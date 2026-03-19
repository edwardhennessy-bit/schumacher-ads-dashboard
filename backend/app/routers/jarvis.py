"""
JARVIS API Router — AI insights and custom Slack report endpoints.
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from app.config import get_settings
from app.services.live_api import LiveAPIService, DateRange

router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])

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


@router.post("/send-report")
async def send_report(body: dict):
    """
    Generate a custom AI report from user prompt and post to Slack.
    """
    settings = get_settings()

    if not settings.slack_bot_token:
        return {"success": False, "error": "Slack bot not configured"}

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
