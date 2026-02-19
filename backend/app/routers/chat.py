"""
Chat API Router - Web-based chat interface for JARVIS.

This provides the same AI analysis capabilities as the Slack bot,
but accessible through the dashboard web interface.

IMPORTANT: This router must stay in full parity with bot.py's analyze_and_respond()
logic — same ad-lookup detection, same MTD default, same active ad count fetch,
same stale-cache suppression when live data succeeds.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import re
import structlog

from app.config import get_settings
from app.slack.analyst import AnthropicAnalyst
from app.services.live_api import (
    LiveAPIService,
    parse_date_range_from_query,
    get_account_id_from_query,
    DateRange,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Store conversation contexts per session (keyed by session_id)
_session_contexts: Dict[str, List[Dict[str, str]]] = {}

# ── Ad-lookup detection (mirrors bot.py exactly) ──────────────────────────────

_AD_LIMIT_KEYWORDS = [
    "pause", "ad limit", "250", "over limit", "which ads", "ad review",
    "adreview", "too many ads", "cut ads", "reduce ads", "active ads",
]

_AD_LOOKUP_KEYWORDS = [
    "ad ", "ads ", "creative", "batch", "batches", "specific ad",
    "this ad", "these ads", "the ad", "ad name", "ad called",
    "| car |", "| img |", "| bof |", "| mof |", "| tof |",
    "websiteleads", "learn more", "floorplan", "dreamhome",
    "modelhome", "winner +", "variant",
]

_PAUSED_ADS_KEYWORDS = [
    "paused ads", "what was paused", "what did i pause", "what have i paused",
    "which ads were paused", "ads i paused", "show paused", "list paused",
    "recently paused", "just paused", "ads paused", "paused creatives",
    "change history", "what changed", "paused today", "paused this week",
    "paused yesterday",
]


def _is_ad_limit_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _AD_LIMIT_KEYWORDS)


def _is_paused_ads_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _PAUSED_ADS_KEYWORDS)


def _is_ad_lookup_query(query: str) -> bool:
    q = query.lower()
    if q.count("|") >= 2:
        return True
    return any(kw in q for kw in _AD_LOOKUP_KEYWORDS)


def _extract_search_terms(query: str) -> List[str]:
    if "|" in query:
        # Split on pipes
        raw_tokens = [t.strip() for t in query.replace("•", "").split("|")]

        # The first token may contain a sentence prefix before the actual ad name fragment,
        # e.g. "How are these ads performing: DreamHome" or "What is the performance of Winner + floorplans"
        # Extract just the ad-name fragment from the end of the first token.
        cleaned_tokens = []
        for i, tok in enumerate(raw_tokens):
            if i == 0:
                cleaned = tok

                # Step 1: Split on colon or explicit intro words like "ads:", "creatives:"
                stripped = re.split(
                    r"[:]\s*|(?:ads?|these|those|following|creatives?)\s+",
                    cleaned,
                    flags=re.IGNORECASE,
                )
                cleaned = stripped[-1].strip()

                # Step 2: If still a long sentence (>3 words), grab the phrase after
                # prepositions/verbs like "of", "for", "on", "check", "pull", "show"
                if len(cleaned.split()) > 3:
                    match = re.search(
                        r"(?:of|for|on|about|check|pull|get|show|see)\s+(.+)$",
                        cleaned,
                        flags=re.IGNORECASE,
                    )
                    if match:
                        cleaned = match.group(1).strip()

                if cleaned:
                    cleaned_tokens.append(cleaned)
            else:
                if tok:
                    cleaned_tokens.append(tok)

        # Filter to non-trivial tokens (length > 1)
        terms = [t for t in cleaned_tokens if len(t) > 1]

        # Also add joined first-3-segment form as a composite search term
        if len(terms) >= 2:
            terms.append(" | ".join(terms[:3]))

        return list(dict.fromkeys(terms))  # deduplicate, preserve order

    stopwords = {"what", "how", "did", "does", "with", "about", "these", "those",
                 "that", "this", "from", "have", "show", "tell", "look", "give",
                 "their", "they", "them", "then", "than", "when", "where", "which"}
    words = re.findall(r"[A-Za-z0-9+]+", query)
    return [w for w in words if len(w) > 4 and w.lower() not in stopwords]


# ─────────────────────────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    """A chat message from the user."""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Response from JARVIS."""
    response: str
    session_id: str
    data_source: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage):
    """
    Send a message to JARVIS and get a response.

    Full parity with bot.py:
    - Always defaults to MTD if no date range detected
    - Always fetches live API data (never stale static JSON when live succeeds)
    - Always fetches active ad count in parallel
    - Detects ad-lookup queries and fetches ad-level data automatically
    - Detects ad-limit queries and fetches full active-ads inventory
    - Passes per-session conversation history to Claude
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    session_id = chat_message.session_id or "default"
    user_message = chat_message.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info("chat_message_received", session_id=session_id, message_length=len(user_message))

    try:
        settings = get_settings()
        analyst = AnthropicAnalyst(api_key=settings.anthropic_api_key)

        # Resolve date range — always default to MTD so live data is always fetched
        date_range = parse_date_range_from_query(user_message)
        if date_range is None:
            date_range = DateRange.this_month()
            logger.info("no_date_range_defaulting_to_mtd")

        account_id = get_account_id_from_query(user_message)

        # Decide which extra fetch stages we need
        needs_paused_ads = _is_paused_ads_query(user_message)
        needs_ad_limit = (not needs_paused_ads) and _is_ad_limit_query(user_message)
        needs_ad_lookup = (not needs_paused_ads) and (not needs_ad_limit) and _is_ad_lookup_query(user_message)

        logger.info(
            "chat_query_routing",
            date_range=f"{date_range.start_date} to {date_range.end_date}",
            needs_paused_ads=needs_paused_ads,
            needs_ad_limit=needs_ad_limit,
            needs_ad_lookup=needs_ad_lookup,
        )

        live_api_context = None
        live_data_success = False
        additional_context_parts: List[str] = []
        data_source = f"live_api ({date_range.start_date} to {date_range.end_date})"

        if not settings.meta_access_token:
            live_api_context = (
                f"=== DATE RANGE REQUESTED ===\n"
                f"Period: {date_range.start_date} to {date_range.end_date}\n"
                f"Note: Meta API token not configured.\n"
            )
        else:
            live_api = LiveAPIService(meta_access_token=settings.meta_access_token)

            # ── Stage 1: Account summary + campaign breakdown + active ad count ─
            try:
                insights_data, campaign_data, active_count_data = await asyncio.gather(
                    live_api.get_meta_account_insights(
                        account_id=account_id,
                        date_range=date_range,
                        level="account",
                    ),
                    live_api.get_meta_campaigns(
                        account_id=account_id,
                        date_range=date_range,
                    ),
                    live_api.get_meta_active_ads_count(account_id),
                )

                if insights_data.get("success"):
                    live_api_context = live_api.format_insights_for_context(insights_data)
                    live_data_success = True

                    if campaign_data.get("success"):
                        live_api_context += "\n\n" + live_api.format_campaigns_for_context(campaign_data)

                    if active_count_data.get("success"):
                        active_count = active_count_data["active_ads"]
                        headroom = 250 - active_count
                        live_api_context += (
                            f"\n\n=== ACTIVE AD COUNT (real-time, today) ===\n"
                            f"Delivering ads right now: {active_count} / 250 limit\n"
                            f"Headroom before limit: {headroom} ads\n"
                            f"Status: {'⚠️ OVER LIMIT' if headroom < 0 else ('🟡 CLOSE TO LIMIT' if headroom < 20 else '🟢 OK')}"
                        )

                    logger.info(
                        "live_data_fetched",
                        date_range=f"{date_range.start_date} to {date_range.end_date}",
                        campaign_count=len(campaign_data.get("campaigns", [])),
                        active_ads=active_count_data.get("active_ads"),
                        needs_paused_ads=needs_paused_ads,
                        needs_ad_lookup=needs_ad_lookup,
                        needs_ad_limit=needs_ad_limit,
                    )
                else:
                    error_msg = insights_data.get("error", "Unknown error")
                    logger.warning("live_data_fetch_failed", error=error_msg)
                    live_api_context = (
                        f"=== DATE RANGE REQUESTED ===\n"
                        f"Period: {date_range.start_date} to {date_range.end_date}\n"
                        f"Note: Live data fetch failed ({error_msg}).\n"
                    )

            except Exception as e:
                logger.warning("live_data_fetch_error", error=str(e))
                live_api_context = (
                    f"=== DATE RANGE REQUESTED ===\n"
                    f"Period: {date_range.start_date} to {date_range.end_date}\n"
                    f"Note: Could not fetch live data ({str(e)}).\n"
                )

            # ── Stage 2a: Paused ads history (change history queries) ────────
            if needs_paused_ads:
                try:
                    paused_data = await live_api.get_meta_recently_paused_ads(account_id)
                    if paused_data.get("success"):
                        paused_context = live_api.format_paused_ads_for_context(paused_data)
                        additional_context_parts.insert(0, paused_context)
                        logger.info(
                            "paused_ads_context_injected",
                            ad_count=paused_data.get("total_paused_ads"),
                        )
                    else:
                        logger.warning("paused_ads_fetch_failed", error=paused_data.get("error"))
                except Exception as e:
                    logger.warning("paused_ads_fetch_error", error=str(e))

            # ── Stage 2b: Active ads inventory (pause/limit queries) ──────────
            elif needs_ad_limit:
                try:
                    ad_perf_data = await live_api.get_meta_active_ads_with_performance(account_id)
                    if ad_perf_data.get("success"):
                        ad_perf_context = live_api.format_active_ads_for_jarvis(ad_perf_data)
                        additional_context_parts.insert(0, ad_perf_context)
                        logger.info(
                            "ad_performance_context_injected",
                            ad_count=ad_perf_data.get("total_active_ads"),
                        )
                except Exception as e:
                    logger.warning("ad_performance_fetch_failed", error=str(e))

            # ── Stage 2c: Ad-level creative lookup ────────────────────────────
            elif needs_ad_lookup:
                try:
                    search_terms = _extract_search_terms(user_message)
                    logger.info("ad_lookup_triggered", search_terms=search_terms)

                    ad_lookup_data = await live_api.get_meta_ads_by_date_range(
                        account_id=account_id,
                        date_range=date_range,
                        search_terms=search_terms if search_terms else None,
                    )
                    if ad_lookup_data.get("success"):
                        ad_lookup_context = live_api.format_ads_for_context(ad_lookup_data)
                        additional_context_parts.insert(0, ad_lookup_context)
                        logger.info(
                            "ad_lookup_context_injected",
                            ad_count=ad_lookup_data.get("total_ads"),
                            search_terms=search_terms,
                        )
                    else:
                        logger.warning("ad_lookup_failed", error=ad_lookup_data.get("error"))
                except Exception as e:
                    logger.warning("ad_lookup_fetch_failed", error=str(e))

        # Prepend live API context to additional context parts
        if live_api_context:
            additional_context_parts.insert(0, live_api_context)

        additional_context = "\n\n".join(additional_context_parts) if additional_context_parts else None

        # When live data succeeded, do NOT pass stale static JSON — pass empty dict
        # so Claude never sees phantom old campaign names from campaigns.json.
        performance_data = {} if live_data_success else {}

        # Load per-session conversation history
        conversation_history = _session_contexts.get(session_id, [])

        logger.info(
            "requesting_chat_analysis",
            session_id=session_id,
            history_turns=len(conversation_history) // 2,
            has_live_context=bool(live_api_context),
            has_ad_context=needs_paused_ads or needs_ad_lookup or needs_ad_limit,
        )

        # Get analysis from JARVIS
        response = await analyst.analyze_performance(
            performance_data=performance_data,
            user_query=user_message,
            additional_context=additional_context,
            conversation_history=conversation_history,
        )

        # Save this exchange to per-session history (clean Q&A only, not data dumps)
        updated_history = list(conversation_history)
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": response})
        # Cap at 20 messages (10 turns)
        _session_contexts[session_id] = updated_history[-20:]

        logger.info("chat_response_sent", session_id=session_id, response_length=len(response))

        return ChatResponse(
            response=response,
            session_id=session_id,
            data_source=data_source,
        )

    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_session(session_id: str = "default"):
    """Clear the conversation history for a session."""
    if session_id in _session_contexts:
        del _session_contexts[session_id]
    return {"status": "cleared", "session_id": session_id}


@router.get("/status")
async def chat_status():
    """Check if JARVIS chat is available."""
    settings = get_settings()
    return {
        "available": bool(settings.anthropic_api_key),
        "live_data_enabled": bool(settings.meta_access_token),
        "active_sessions": len(_session_contexts),
    }
