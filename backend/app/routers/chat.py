"""
Chat API Router - Web-based chat interface for JARVIS.

This provides the same AI analysis capabilities as the Slack bot,
but accessible through the dashboard web interface.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import structlog

from app.config import get_settings
from app.slack.analyst import AnthropicAnalyst
from app.services.meta_ads import MetaAdsService
from app.services.live_api import (
    LiveAPIService,
    parse_date_range_from_query,
    get_account_id_from_query,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Store conversation contexts per session
_session_contexts: Dict[str, List[Dict[str, str]]] = {}


class ChatMessage(BaseModel):
    """A chat message from the user."""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """Response from JARVIS."""
    response: str
    session_id: str
    data_source: Optional[str] = None


def _get_performance_data() -> Dict[str, Any]:
    """Fetch performance data from Meta Ads service."""
    performance_data = {}
    meta_service = MetaAdsService()

    try:
        metrics = meta_service.get_metrics_overview()
        performance_data["summary"] = {
            "total_spend": metrics.spend,
            "total_budget": 0,
            "impressions": metrics.impressions,
            "clicks": metrics.clicks,
            "leads": metrics.leads,
            "conversions": metrics.conversions,
            "cost_per_lead": metrics.cost_per_lead,
            "ctr": metrics.ctr,
            "cpc": metrics.cpc,
            "cpm": metrics.cpm,
            "active_ads": metrics.active_ads,
            "total_ads": metrics.total_ads,
            "spend_change": metrics.spend_change,
            "leads_change": metrics.leads_change,
            "cpl_change": metrics.cost_per_lead_change,
            "remarketing_cpl": metrics.remarketing_cpl,
            "prospecting_cpl": metrics.prospecting_cpl,
        }
    except Exception as e:
        logger.warning("metrics_overview_error", error=str(e))

    try:
        campaigns = meta_service.get_campaigns()
        performance_data["campaigns"] = [
            {
                "id": c.id,
                "name": c.name,
                "platform": "Meta",
                "status": c.status,
                "spend": c.spend,
                "impressions": c.impressions,
                "clicks": c.clicks,
                "leads": c.leads,
                "conversions": c.conversions,
                "cost_per_lead": c.cost_per_lead,
                "ctr": c.ctr,
                "cpc": c.cpc,
            }
            for c in campaigns
        ]
    except Exception as e:
        logger.warning("campaigns_error", error=str(e))

    return performance_data


@router.post("/message", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage):
    """
    Send a message to JARVIS and get a response.

    This endpoint provides the same AI-powered analysis as the Slack bot.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="Anthropic API key not configured"
        )

    session_id = chat_message.session_id or "default"
    user_message = chat_message.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info("chat_message_received", session_id=session_id, message_length=len(user_message))

    try:
        # Initialize analyst
        analyst = AnthropicAnalyst(api_key=settings.anthropic_api_key)

        # Load previous context if exists
        if session_id in _session_contexts:
            analyst._conversation_context = _session_contexts[session_id].copy()

        # Check for date range in query
        date_range = parse_date_range_from_query(user_message)
        live_api_context = None
        data_source = "dashboard"

        if date_range:
            # Fetch live data for the requested date range
            account_id = get_account_id_from_query(user_message)

            if settings.meta_access_token:
                try:
                    live_api = LiveAPIService(meta_access_token=settings.meta_access_token)

                    insights_data = await live_api.get_meta_account_insights(
                        account_id=account_id,
                        date_range=date_range,
                        level="account"
                    )

                    if insights_data.get("success"):
                        live_api_context = live_api.format_insights_for_context(insights_data)

                        campaign_data = await live_api.get_meta_campaigns(
                            account_id=account_id,
                            date_range=date_range
                        )
                        if campaign_data.get("success"):
                            live_api_context += "\n\n" + live_api.format_campaigns_for_context(campaign_data)

                        data_source = f"live_api ({date_range.start_date} to {date_range.end_date})"
                        logger.info("live_data_fetched", date_range=f"{date_range.start_date} to {date_range.end_date}")
                    else:
                        live_api_context = (
                            f"=== DATE RANGE REQUESTED ===\n"
                            f"Period: {date_range.start_date} to {date_range.end_date}\n"
                            f"Note: Live data fetch failed. Using cached dashboard data.\n"
                        )
                except Exception as e:
                    logger.warning("live_data_fetch_error", error=str(e))
                    live_api_context = (
                        f"=== DATE RANGE REQUESTED ===\n"
                        f"Period: {date_range.start_date} to {date_range.end_date}\n"
                        f"Note: Could not fetch live data ({str(e)}). Using dashboard data.\n"
                    )
            else:
                live_api_context = (
                    f"=== DATE RANGE REQUESTED ===\n"
                    f"Period: {date_range.start_date} to {date_range.end_date}\n"
                    f"Note: Meta API token not configured. Using dashboard data.\n"
                )

        # Get dashboard performance data
        performance_data = _get_performance_data()

        # Build additional context
        additional_context = live_api_context if live_api_context else None

        # Get analysis from JARVIS
        response = await analyst.analyze_performance(
            performance_data=performance_data,
            user_query=user_message,
            additional_context=additional_context,
        )

        # Save conversation context
        _session_contexts[session_id] = analyst._conversation_context.copy()

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
