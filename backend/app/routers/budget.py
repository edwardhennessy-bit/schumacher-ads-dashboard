"""
Budget Tracker Router — track monthly budget vs. actual spend with TOF/MOF/BOF funnel breakdown.

Budget config is persisted to backend/app/data/budget_config.json.
Actual spend is fetched live from Google Ads, Microsoft Ads, and Meta for the requested date range.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import asyncio
import calendar
import json
import os
import structlog
from datetime import date

from app.services.live_api import LiveAPIService, DateRange
from app.services.google_ads_api import GoogleAdsService, SCHUMACHER_GOOGLE_CUSTOMER_ID
from app.services.mcp_client import get_mcp_client
from app.routers.microsoft import SCHUMACHER_MICROSOFT_ACCOUNT_ID, _parse_float
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/budget", tags=["budget"])

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "budget_config.json")


# ── Pydantic models ───────────────────────────────────────────────────────────

class PlatformBudget(BaseModel):
    total: float = 0.0
    testing: float = 0.0

class BudgetConfig(BaseModel):
    google: PlatformBudget = PlatformBudget()
    microsoft: PlatformBudget = PlatformBudget()
    meta: PlatformBudget = PlatformBudget()


# ── Config persistence ────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "google": {"total": 0.0, "testing": 0.0},
        "microsoft": {"total": 0.0, "testing": 0.0},
        "meta": {"total": 0.0, "testing": 0.0},
    }

def _save_config(data: dict):
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Campaign classification ───────────────────────────────────────────────────

def _classify(name: str) -> str:
    """Classify a campaign name into a funnel stage or testing bucket."""
    u = name.upper()
    # Testing takes priority — test campaigns are often mixed into any funnel stage
    if "TEST" in u:
        return "testing"
    if "TOF" in u or "TOP OF FUNNEL" in u or "TOP-OF-FUNNEL" in u:
        return "tof"
    if "MOF" in u or "MID FUNNEL" in u or "MIDDLE FUNNEL" in u or "MID-FUNNEL" in u:
        return "mof"
    if (
        "BOF" in u
        or "BOTTOM OF FUNNEL" in u
        or "BOTTOM-OF-FUNNEL" in u
        or "REMARKETING" in u
        or "RETARGETING" in u
    ):
        return "bof"
    return "untagged"

def _build_funnel(campaigns: list) -> dict:
    """Aggregate campaign spend into funnel stage buckets."""
    buckets: dict = {k: {"spend": 0.0, "campaign_count": 0} for k in ("tof", "mof", "bof", "testing", "untagged")}
    for c in campaigns:
        tag = _classify(c.get("name", ""))
        buckets[tag]["spend"] = round(buckets[tag]["spend"] + float(c.get("spend", 0)), 2)
        buckets[tag]["campaign_count"] += 1
    return buckets


# ── Pacing helpers ────────────────────────────────────────────────────────────

def _pacing_status(actual: float, budget: float, factor: float) -> str:
    if budget <= 0:
        return "no_budget"
    expected = budget * factor
    if expected == 0:
        return "no_budget"
    if actual > expected * 1.10:
        return "ahead"
    if actual < expected * 0.90:
        return "behind"
    return "on_track"

def _platform_summary(budget_cfg: dict, campaigns: list, pacing_factor: float) -> dict:
    total_budget = float(budget_cfg.get("total", 0))
    testing_budget = float(budget_cfg.get("testing", 0))
    main_budget = round(total_budget - testing_budget, 2)

    funnel = _build_funnel(campaigns)
    total_spend = round(sum(c.get("spend", 0) for c in campaigns), 2)
    testing_spend = funnel["testing"]["spend"]
    main_spend = round(total_spend - testing_spend, 2)

    return {
        "budget": total_budget,
        "testing_budget": testing_budget,
        "main_budget": main_budget,
        "total_spend": total_spend,
        "testing_spend": testing_spend,
        "main_spend": main_spend,
        "remaining": round(total_budget - total_spend, 2),
        "expected_spend": round(total_budget * pacing_factor, 2),
        "pacing_factor": round(pacing_factor, 4),
        "pacing_status": _pacing_status(total_spend, total_budget, pacing_factor),
        "testing_pacing_status": _pacing_status(testing_spend, testing_budget, pacing_factor),
        "funnel": funnel,
        "campaign_count": len(campaigns),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/config")
async def get_budget_config():
    """Return the current monthly budget configuration."""
    return _load_config()


@router.post("/config")
async def save_budget_config(config: BudgetConfig):
    """Persist monthly budget configuration."""
    data = config.model_dump()
    _save_config(data)
    return {"success": True, "config": data}


@router.get("/status")
async def get_budget_status(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD (defaults to current month start)"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD (defaults to today)"),
):
    """
    Fetch live campaign spend from all platforms and return budget vs. actual status
    with TOF/MOF/BOF funnel breakdown and pacing indicators.
    """
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1).isoformat()
        end_date = today.isoformat()

    config = _load_config()
    settings = get_settings()

    # Pacing factor: how far through the month are we?
    start_d = date.fromisoformat(start_date)
    end_d = date.fromisoformat(end_date)
    _, days_in_month = calendar.monthrange(start_d.year, start_d.month)
    days_elapsed = (end_d - start_d).days + 1
    pacing_factor = min(days_elapsed / days_in_month, 1.0)

    date_range = DateRange(start_date=start_date, end_date=end_date)

    google_campaigns: list = []
    microsoft_campaigns: list = []
    meta_campaigns: list = []

    # ── Google Ads ────────────────────────────────────────────────────────────
    async def _fetch_google():
        try:
            mcp_client = get_mcp_client(
                gateway_url=settings.gateway_url,
                gateway_token=settings.gateway_token,
            )
            service = GoogleAdsService(
                mcp_client=mcp_client if mcp_client.is_configured else None,
                developer_token=settings.google_ads_developer_token,
                client_id=settings.google_ads_client_id,
                client_secret=settings.google_ads_client_secret,
                refresh_token=settings.google_ads_refresh_token,
            )
            if not service.is_configured:
                return []
            customer_id = settings.google_ads_customer_id or SCHUMACHER_GOOGLE_CUSTOMER_ID
            result = await service.get_campaign_performance(customer_id, date_range)
            if result.get("success"):
                return [
                    {"name": c.get("name", ""), "spend": float(c.get("spend", 0))}
                    for c in result.get("campaigns", [])
                ]
        except Exception as e:
            logger.error("budget_google_fetch_error", error=str(e))
        return []

    # ── Microsoft Ads ─────────────────────────────────────────────────────────
    async def _fetch_microsoft():
        try:
            mcp = get_mcp_client(
                gateway_url=settings.gateway_url,
                gateway_token=settings.gateway_token,
            )
            if not mcp.is_configured:
                return []
            raw = await mcp.call_tool("microsoft_ads_campaign_performance", {
                "accountId": SCHUMACHER_MICROSOFT_ACCOUNT_ID,
                "startDate": start_date,
                "endDate": end_date,
            })
            rows = raw if isinstance(raw, list) else raw.get("data", [])
            # Aggregate by campaign name (gateway returns per-day rows)
            agg: dict = {}
            for row in rows:
                name = row.get("CampaignName", "")
                spend = _parse_float(row.get("Spend", 0))
                if name and spend > 0:
                    agg[name] = round(agg.get(name, 0.0) + spend, 2)
            return [{"name": n, "spend": s} for n, s in agg.items()]
        except Exception as e:
            logger.error("budget_microsoft_fetch_error", error=str(e))
        return []

    # ── Meta ──────────────────────────────────────────────────────────────────
    async def _fetch_meta():
        try:
            if not settings.meta_ad_account_id or not settings.meta_access_token:
                return []
            live_api = LiveAPIService(meta_access_token=settings.meta_access_token)
            result = await live_api.get_meta_campaigns(settings.meta_ad_account_id, date_range)
            if result.get("success"):
                return [
                    {
                        "name": c.get("campaign_name", c.get("name", "")),
                        "spend": float(c.get("spend", 0)),
                    }
                    for c in result.get("campaigns", [])
                ]
        except Exception as e:
            logger.error("budget_meta_fetch_error", error=str(e))
        return []

    google_campaigns, microsoft_campaigns, meta_campaigns = await asyncio.gather(
        _fetch_google(),
        _fetch_microsoft(),
        _fetch_meta(),
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "pacing_factor": round(pacing_factor, 4),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "platforms": {
            "google": _platform_summary(config.get("google", {}), google_campaigns, pacing_factor),
            "microsoft": _platform_summary(config.get("microsoft", {}), microsoft_campaigns, pacing_factor),
            "meta": _platform_summary(config.get("meta", {}), meta_campaigns, pacing_factor),
        },
    }
