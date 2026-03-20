"""
JARVIS API Router — AI insights and custom Slack report endpoints.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.services.live_api import LiveAPIService, DateRange

router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])
logger = logging.getLogger(__name__)

# Path to schedule config file
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SCHEDULE_FILE = DATA_DIR / "jarvis_schedule.json"

DEFAULT_SCHEDULE = {"channel": "jarvis-schumacher", "day": "monday", "hour": 9, "timezone": "America/New_York"}

DEFAULT_CHANNELS = ["jarvis-schumacher", "paid-media", "paid-media-team", "general"]
CHANNELS_FILE = DATA_DIR / "jarvis_channels.json"


def _load_channels() -> list[str]:
    """Load channels from disk, merged with defaults (deduped, defaults first)."""
    saved: list[str] = []
    if CHANNELS_FILE.exists():
        try:
            saved = json.loads(CHANNELS_FILE.read_text())
        except Exception:
            pass
    merged = list(DEFAULT_CHANNELS)
    for ch in saved:
        if ch not in merged:
            merged.append(ch)
    return merged


def _save_channels(channels: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Persist only the non-default channels so defaults stay in code
    extra = [ch for ch in channels if ch not in DEFAULT_CHANNELS]
    CHANNELS_FILE.write_text(json.dumps(extra, indent=2))


@router.get("/channels")
async def get_channels():
    """Return list of available Slack channels."""
    return {"channels": _load_channels()}


@router.post("/channels")
async def add_channel(body: dict):
    """Add a custom Slack channel to the persistent list."""
    channel = (body.get("channel") or "").strip().lstrip("#")
    if not channel:
        return {"success": False, "error": "Channel name is required"}
    channels = _load_channels()
    if channel not in channels:
        channels.append(channel)
        _save_channels(channels)
    return {"success": True, "channels": channels}


@router.post("/schedule")
async def update_schedule(body: dict):
    """Write schedule config to disk."""
    channel = body.get("channel", DEFAULT_SCHEDULE["channel"])
    day = body.get("day", DEFAULT_SCHEDULE["day"])
    hour = body.get("hour", DEFAULT_SCHEDULE["hour"])
    timezone = body.get("timezone", DEFAULT_SCHEDULE["timezone"])

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = {"channel": channel, "day": day, "hour": hour, "timezone": timezone}
    SCHEDULE_FILE.write_text(json.dumps(config, indent=2))

    return {"success": True, "channel": channel, "day": day, "hour": hour, "timezone": timezone}


@router.get("/schedule")
async def get_schedule():
    """Read schedule config from disk, or return default."""
    if SCHEDULE_FILE.exists():
        try:
            config = json.loads(SCHEDULE_FILE.read_text())
            # Back-fill timezone for configs saved before this field was added
            if "timezone" not in config:
                config["timezone"] = DEFAULT_SCHEDULE["timezone"]
            return config
        except Exception:
            pass
    return DEFAULT_SCHEDULE


@router.post("/ai-insights")
async def get_ai_insights(body: dict):
    """
    Auto-generate AI insights for the active ads tree.
    Calls Claude to summarize performance with optional comparison period.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        return {"success": False, "error": "AI insights not configured"}

    start_date: str = body.get("start_date", "")
    end_date: str = body.get("end_date", "")
    compare_start: Optional[str] = body.get("compare_start")
    compare_end: Optional[str] = body.get("compare_end")

    try:
        import anthropic as _anthropic

        # Fetch ads tree for main period
        if settings.meta_access_token:
            live_service = LiveAPIService(meta_access_token=settings.meta_access_token)
            account_id = settings.meta_ad_account_id or "act_142003632"
            tree_result = await live_service.get_meta_active_ads_tree(
                account_id,
                start_date=start_date or None,
                end_date=end_date or None,
            )
        else:
            tree_result = {"success": False, "campaigns": [], "total_active_ads": 0}

        # Optionally fetch comparison period
        compare_tree = None
        if compare_start and compare_end and settings.meta_access_token:
            compare_tree = await live_service.get_meta_active_ads_tree(
                account_id,
                start_date=compare_start,
                end_date=compare_end,
            )

        # Build period labels
        period_label = f"{start_date} to {end_date}" if start_date and end_date else "last 30 days"
        compare_label = (
            f"{compare_start} to {compare_end}" if compare_start and compare_end else None
        )

        # Compose the data summary for Claude
        data_summary = json.dumps(tree_result, indent=2)
        compare_summary = json.dumps(compare_tree, indent=2) if compare_tree else None

        prompt_parts = [
            f"You are analyzing Meta Ads performance data for Schumacher Homes for the period {period_label}.",
            "",
            "Here is the active ads tree data (campaigns → ad sets → ads with KPIs):",
            "```json",
            data_summary,
            "```",
        ]

        if compare_summary:
            prompt_parts += [
                "",
                f"Here is the comparison period data ({compare_label}):",
                "```json",
                compare_summary,
                "```",
            ]

        prompt_parts += [
            "",
            "Important context:",
            "- 'Visit' or 'TOF' campaigns are engagement/awareness-focused (clicks, CTR) — not lead-focused. Do NOT flag high CPL for these.",
            "- Remarketing campaigns target warm audiences and typically have lower CPL than prospecting.",
            "- CPL above $70 for lead-gen campaigns is a flag worth noting.",
            "- Ad limit proximity: if total active ads is near or above 200, flag it.",
            "",
            "Please analyze:",
            "1. Top performers by leads and CPL efficiency",
            "2. Biggest movers (if comparison data provided)",
            "3. CPL alerts — any lead-gen campaigns/ads with CPL > $70",
            "4. Ad limit proximity — if active ads count is high",
            "5. Budget efficiency observations",
            "6. Any other notable insights",
            "",
            "Return ONLY valid JSON in this exact format (no markdown, no extra text):",
            '{',
            '  "headline": "One-sentence overall summary",',
            '  "bullets": ["Key insight 1", "Key insight 2", "Key insight 3"],',
            '  "flags": ["Warning or alert 1", "Warning or alert 2"]',
            '}',
            "",
            "Keep bullets concise (1-2 sentences each). Include 3-6 bullets. Flags array can be empty if nothing to flag.",
        ]

        full_prompt = "\n".join(prompt_parts)

        client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": full_prompt}],
        )

        raw_text = message.content[0].text.strip()

        # Parse JSON from the response
        try:
            insights = json.loads(raw_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text if Claude wrapped it
            import re
            match = re.search(r"\{[\s\S]*\}", raw_text)
            if match:
                insights = json.loads(match.group())
            else:
                insights = {
                    "headline": "AI analysis complete",
                    "bullets": [raw_text],
                    "flags": [],
                }

        return {
            "success": True,
            "insights": insights,
            "period": period_label,
            "compare_period": compare_label,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _md_to_slack(text: str) -> str:
    """
    Convert markdown to Slack mrkdwn format.
    - **bold** → *bold*
    - ## Header → *HEADER*
    - ### Header → *Header*
    - # Header → *HEADER*
    - - item / * item → • item
    - --- → blank line
    - Strip code fences for special blocks; keep content readable
    """
    import re
    lines = text.split("\n")
    out: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip special code block fences — keep their inner text as-is
        if stripped.startswith("```"):
            block_lines: list[str] = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                block_lines.append(lines[j])
                j += 1
            # Include inner content as plain text (skip JSON blocks which are data)
            block_type = stripped.replace("```", "").strip().lower()
            if block_type not in ("pause_list", "budget_table", "email_report"):
                out.extend(block_lines)
            i = j + 1
            continue

        # Headers
        if stripped.startswith("### "):
            heading = stripped[4:].replace("**", "")
            out.append(f"*{heading}*")
            i += 1
            continue
        if stripped.startswith("## "):
            heading = stripped[3:].replace("**", "").upper()
            out.append(f"*{heading}*")
            i += 1
            continue
        if stripped.startswith("# "):
            heading = stripped[2:].replace("**", "").upper()
            out.append(f"*{heading}*")
            i += 1
            continue

        # Horizontal rules → blank line
        if re.match(r"^[-*_]{3,}$", stripped):
            out.append("")
            i += 1
            continue

        # List items
        ul_match = re.match(r"^[-*•]\s+(.+)", stripped)
        if ul_match:
            item = _inline_md_to_slack(ul_match.group(1))
            out.append(f"• {item}")
            i += 1
            continue

        ol_match = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if ol_match:
            item = _inline_md_to_slack(ol_match.group(2))
            out.append(f"{ol_match.group(1)}. {item}")
            i += 1
            continue

        # Regular line
        if stripped:
            out.append(_inline_md_to_slack(stripped))
        else:
            out.append("")
        i += 1

    # Collapse 3+ blank lines to 2
    result = "\n".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _inline_md_to_slack(text: str) -> str:
    """Convert inline markdown to Slack mrkdwn."""
    import re
    # **bold** → *bold*  (do bold first before italic to avoid double-processing)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # _italic_ → _italic_  (already Slack format, leave as-is)
    # `code` → `code` (already fine in Slack)
    # Strip links — keep display text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


@router.post("/send-report")
async def send_report(body: dict):
    """
    Post a JARVIS response directly to Slack (or optionally re-generate from prompt).
    If 'message' is provided, it is posted directly without calling Claude again.
    """
    settings = get_settings()

    if not settings.slack_bot_token:
        return {"success": False, "error": "Slack bot not configured"}

    channel: str = body.get("channel", "jarvis-schumacher")
    message: Optional[str] = body.get("message")  # Pre-generated content to post directly

    # ── Fast path: post existing JARVIS response directly ─────────────────────
    if message:
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            clean_channel = channel.lstrip("#")
            slack_text = _md_to_slack(message)
            slack_client = AsyncWebClient(token=settings.slack_bot_token)
            await slack_client.chat_postMessage(
                channel=f"#{clean_channel}",
                text=f"*📊 JARVIS Report*\n\n{slack_text}",
            )
            return {"success": True, "message": f"Report sent to #{clean_channel}", "channel": clean_channel}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Slow path: re-generate from prompt via Claude (legacy) ────────────────
    if not settings.anthropic_api_key:
        return {"success": False, "error": "AI insights not configured"}

    prompt: str = body.get("prompt", "Give me a full health report of active ads.")
    channel: str = body.get("channel", "jarvis-schumacher")
    start_date: Optional[str] = body.get("start_date")
    end_date: Optional[str] = body.get("end_date")
    compare_start: Optional[str] = body.get("compare_start")
    compare_end: Optional[str] = body.get("compare_end")

    # Normalize channel (strip leading # if present)
    clean_channel = channel.lstrip("#")

    try:
        import anthropic as _anthropic
        from slack_sdk.web.async_client import AsyncWebClient

        # Fetch ads tree
        if settings.meta_access_token:
            live_service = LiveAPIService(meta_access_token=settings.meta_access_token)
            account_id = settings.meta_ad_account_id or "act_142003632"
            tree_result = await live_service.get_meta_active_ads_tree(
                account_id,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            tree_result = {"success": False, "campaigns": [], "total_active_ads": 0}

        # Optionally fetch comparison period
        compare_tree = None
        if compare_start and compare_end and settings.meta_access_token:
            compare_tree = await live_service.get_meta_active_ads_tree(
                account_id,
                start_date=compare_start,
                end_date=compare_end,
            )

        period_label = (
            f"{start_date} to {end_date}" if start_date and end_date else "last 30 days"
        )

        data_summary = json.dumps(tree_result, indent=2)
        compare_summary = json.dumps(compare_tree, indent=2) if compare_tree else None

        system_prompt = (
            "You are JARVIS, a paid media analyst assistant for Schumacher Homes. "
            "You analyze Meta Ads data and produce concise, actionable Slack reports. "
            "Keep reports clear and formatted for Slack (use *bold*, bullet points with •, no markdown headers). "
            "Important: 'Visit'/'TOF' campaigns are engagement-focused — do not flag high CPL for these."
        )

        user_message_parts = [
            f"User request: {prompt}",
            "",
            f"Period: {period_label}",
            "",
            "Active Ads Tree Data:",
            "```",
            data_summary,
            "```",
        ]

        if compare_summary:
            compare_label = f"{compare_start} to {compare_end}"
            user_message_parts += [
                "",
                f"Comparison Period Data ({compare_label}):",
                "```",
                compare_summary,
                "```",
            ]

        user_message = "\n".join(user_message_parts)

        client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        report_text = message.content[0].text.strip()

        # Post to Slack
        slack_client = AsyncWebClient(token=settings.slack_bot_token)
        await slack_client.chat_postMessage(
            channel=f"#{clean_channel}",
            text=f"*JARVIS Report — {period_label}*\n\n{report_text}",
        )

        return {
            "success": True,
            "message": f"Report sent to #{clean_channel}",
            "channel": clean_channel,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Multi-turn chat endpoint ──────────────────────────────────────────────────

class ChatMessageModel(BaseModel):
    role: str
    content: str

class JarvisChatRequest(BaseModel):
    section: str
    messages: List[ChatMessageModel]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    section_data: Optional[dict] = None

SECTION_SYSTEM_PROMPTS = {
    "kpi_cards": """You are JARVIS, an expert paid media analyst AI for Schumacher Homes (a custom homebuilder). You are embedded in their paid media dashboard and have direct access to live Meta Ads data provided below.

IMPORTANT: Live dashboard data will be injected into this prompt. Always use those exact numbers — never say you don't have access to data.

Key metrics available: Total Leads, Blended CPL (Cost Per Lead), Remarketing CPL & leads, Prospecting CPL & leads, Total Spend, Impressions, Clicks, CTR, CPC, and Active Ads count.

Campaign context:
- Remarketing campaigns: CPL target ~$50-70. Flag anything above $70.
- Prospecting campaigns: CPL target ~$100-150. Higher CPL is expected.
- Visit/TOF campaigns: Engagement-focused — use CTR and CPC as primary KPIs, NOT leads/CPL.

You can: summarize KPI performance, flag anomalies, analyze CPL by segment, assess spend pacing, write Slack-ready summaries. Be concise, specific, and always reference actual numbers from the data.""",

    "active_ads": """You are JARVIS, an expert paid media analyst AI for Schumacher Homes. You are embedded in their paid media dashboard and have direct access to live Meta Ads active ads data provided below.

IMPORTANT: Live active ads tree data (campaigns → ad sets → ads) will be injected into this prompt. Always use those exact numbers — never say you don't have access to data.

Campaign segments:
- Remarketing (BOF/MOF): CPL target ~$50-70. Flag anything above $70.
- Prospecting: Higher CPL expected (~$100-150).
- Visit/TOF campaigns: Engagement-focused — judge by CTR and CPC only, NOT leads/CPL.

You can: generate top/bottom performers, flag high CPL ads, analyze remarketing vs prospecting, review Visit/TOF click efficiency, write Slack-ready health reports. Be specific with campaign and ad names from the data.""",

    "trend_chart": """You are JARVIS, an expert paid media analyst AI for Schumacher Homes. You are embedded in their paid media dashboard and have direct access to live Meta Ads trend data provided below.

IMPORTANT: Live daily performance trend data will be injected into this prompt. Always use those exact numbers and dates — never say you don't have access to data.

You can: summarize trend patterns, identify anomalies/spikes/drops, compare periods, identify best/worst days, write Slack-ready trend summaries. Always cite specific dates and figures from the data.""",

    "campaign_table": """You are JARVIS, an expert paid media analyst AI for Schumacher Homes. You are embedded in their paid media dashboard and have direct access to live Meta Ads campaign data provided below.

IMPORTANT: Live campaign table data will be injected into this prompt. Always use those exact numbers — never say you don't have access to data.

Campaign data includes: spend, leads, CPL, clicks, CTR, CPC per campaign. Campaigns span remarketing, prospecting, and Visit/TOF types.

CPL benchmarks: Remarketing ~$50-70 (flag above $70), Prospecting ~$100-150. Visit/TOF: judge by CTR/CPC only.

You can: rank campaigns by any metric, identify top/bottom performers, analyze spend allocation, flag underperformers, write Slack summaries. Always use actual campaign names and numbers from the data.""",

    "alerts": """You are JARVIS, an expert paid media analyst AI for Schumacher Homes. You are embedded in their paid media dashboard and have direct access to live alert data provided below.

IMPORTANT: Live alert data will be injected into this prompt. Always use those exact alert details — never say you don't have access to data.

Alert types include: budget pacing issues, CPL threshold exceeded, frequency fatigue, ad rejection, spend anomalies.

You can: explain each alert, prioritize by urgency, recommend specific actions, write Slack-ready alert summaries. Be direct and give specific next steps for each alert.""",
}

async def _fetch_section_data(section: str, start_date: Optional[str], end_date: Optional[str], settings) -> Optional[dict]:
    """Auto-fetch live dashboard data for the given section so JARVIS always has real numbers."""
    import json as _json
    try:
        from datetime import date
        sd = start_date or date.today().replace(day=1).isoformat()
        ed = end_date or date.today().isoformat()

        if section in ("kpi_cards", "trend_chart"):
            if settings.meta_access_token:
                svc = LiveAPIService(meta_access_token=settings.meta_access_token)
                acct = settings.meta_ad_account_id or "act_142003632"
                result = await svc.get_meta_account_insights(acct, start_date=sd, end_date=ed)
                return {"platform": "Meta Ads", "period": f"{sd} to {ed}", "metrics": result}

        elif section == "active_ads":
            if settings.meta_access_token:
                svc = LiveAPIService(meta_access_token=settings.meta_access_token)
                acct = settings.meta_ad_account_id or "act_142003632"
                result = await svc.get_meta_active_ads_tree(acct, start_date=sd, end_date=ed)
                return {"platform": "Meta Ads", "period": f"{sd} to {ed}", "active_ads_tree": result}

        elif section == "campaign_table":
            if settings.meta_access_token:
                svc = LiveAPIService(meta_access_token=settings.meta_access_token)
                acct = settings.meta_ad_account_id or "act_142003632"
                result = await svc.get_meta_campaigns(acct, start_date=sd, end_date=ed)
                return {"platform": "Meta Ads", "period": f"{sd} to {ed}", "campaigns": result}

    except Exception as e:
        logger.warning("jarvis_auto_fetch_failed: section=%s error=%s", section, str(e))
    return None


@router.post("/chat")
async def jarvis_chat(request: JarvisChatRequest):
    """Multi-turn conversational chat with JARVIS, context-aware per section."""
    import anthropic as _anthropic
    import json as _json

    settings = get_settings()
    anthropic_key = settings.anthropic_api_key if hasattr(settings, "anthropic_api_key") else os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return {"success": False, "error": "Anthropic API key not configured"}

    system_prompt = SECTION_SYSTEM_PROMPTS.get(request.section, SECTION_SYSTEM_PROMPTS["kpi_cards"])

    # Use provided section_data, or auto-fetch live data from the dashboard
    section_data = request.section_data
    if not section_data:
        section_data = await _fetch_section_data(request.section, request.start_date, request.end_date, settings)

    if section_data:
        system_prompt += f"\n\n=== LIVE DASHBOARD DATA ===\nThe following is the actual current data from the dashboard. Use these exact numbers in your responses — do NOT say you lack access to data.\n\n{_json.dumps(section_data, indent=2)[:10000]}\n=== END DATA ==="

    if request.start_date and request.end_date:
        system_prompt += f"\n\nDate range being analyzed: {request.start_date} to {request.end_date}"

    try:
        client = _anthropic.Anthropic(api_key=anthropic_key)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        reply = response.content[0].text if response.content else "No response generated."
        return {"success": True, "reply": reply}
    except Exception as e:
        logger.error("jarvis_chat_error: error=%s section=%s", str(e), request.section)
        return {"success": False, "error": str(e)}
