"""
Microsoft Ads Router — live data via MCP Gateway.

Fetches real-time Microsoft Ads performance data for Schumacher Homes
through the SingleGrain MCP Gateway. No scraping required.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import structlog
from datetime import datetime

from app.services.mcp_client import get_mcp_client
from app.services.live_api import DateRange
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/microsoft", tags=["microsoft-ads"])

# Schumacher Homes Microsoft Ads account ID
SCHUMACHER_MICROSOFT_ACCOUNT_ID = "275026"


def _parse_float(val) -> float:
    """Parse a numeric string, stripping currency/percent symbols."""
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace("$", "").replace(",", "").replace("%", "").strip() or 0)


def _parse_int(val) -> int:
    return int(_parse_float(val))


def _calc_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 1)


def _aggregate_campaigns(rows: list) -> dict:
    """Roll up campaign rows into account-level totals."""
    spend = 0.0
    impressions = 0
    clicks = 0
    conversions = 0

    for row in rows:
        spend += _parse_float(row.get("Spend", 0))
        impressions += _parse_int(row.get("Impressions", 0))
        clicks += _parse_int(row.get("Clicks", 0))
        conversions += _parse_int(row.get("Conversions", 0))

    ctr = round(clicks / impressions * 100, 2) if impressions else 0
    cpc = round(spend / clicks, 2) if clicks else 0
    cpl = round(spend / conversions, 2) if conversions else 0

    return {
        "spend": round(spend, 2),
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "leads": conversions,
        "ctr": ctr,
        "cpc": cpc,
        "cost_per_lead": cpl,
        "cost_per_conversion": cpl,
    }


def _format_campaigns(rows: list) -> list:
    """Format campaign rows for the campaigns table."""
    result = []
    for row in rows:
        spend = _parse_float(row.get("Spend", 0))
        clicks = _parse_int(row.get("Clicks", 0))
        impressions = _parse_int(row.get("Impressions", 0))
        conversions = _parse_int(row.get("Conversions", 0))
        if spend == 0 and impressions == 0:
            continue
        result.append({
            "id": str(row.get("CampaignId", "")),
            "name": row.get("CampaignName", ""),
            "status": row.get("CampaignStatus", ""),
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": _parse_float(row.get("Ctr", "0").replace("%", "")),
            "cpc": _parse_float(row.get("AverageCpc", 0)),
            "conversions": conversions,
            "cost_per_conversion": _parse_float(row.get("CostPerConversion", 0)),
        })
    return sorted(result, key=lambda x: x["spend"], reverse=True)


class MicrosoftOverviewResponse(BaseModel):
    connected: bool = False
    live: bool = False
    spend: float = 0
    spend_change: float = 0
    impressions: int = 0
    impressions_change: float = 0
    clicks: int = 0
    clicks_change: float = 0
    ctr: float = 0
    ctr_change: float = 0
    cpc: float = 0
    cpc_change: float = 0
    leads: int = 0
    leads_change: float = 0
    cost_per_lead: float = 0
    cost_per_lead_change: float = 0
    conversions: int = 0
    conversions_change: float = 0
    cost_per_conversion: float = 0
    campaigns: list = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/overview", response_model=MicrosoftOverviewResponse)
async def get_microsoft_overview(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """Fetch live Microsoft Ads performance for Schumacher via MCP Gateway."""
    settings = get_settings()
    mcp = get_mcp_client(
        gateway_url=settings.gateway_url,
        gateway_token=settings.gateway_token,
    )

    if not mcp.is_configured:
        logger.warning("microsoft_gateway_not_configured")
        return MicrosoftOverviewResponse(connected=False)

    account_id = SCHUMACHER_MICROSOFT_ACCOUNT_ID

    if not start_date or not end_date:
        return MicrosoftOverviewResponse(connected=False)

    date_range = DateRange(start_date=start_date, end_date=end_date)
    prior_range = date_range.get_prior_month_equivalent()

    try:
        current_raw, prior_raw = await asyncio.gather(
            mcp.call_tool("microsoft_ads_campaign_performance", {
                "accountId": account_id,
                "startDate": start_date,
                "endDate": end_date,
            }),
            mcp.call_tool("microsoft_ads_campaign_performance", {
                "accountId": account_id,
                "startDate": prior_range.start_date,
                "endDate": prior_range.end_date,
            }),
        )
    except Exception as e:
        logger.error("microsoft_overview_error", error=str(e))
        return MicrosoftOverviewResponse(connected=False)

    # Gateway returns a list of campaign rows directly
    current_rows = current_raw if isinstance(current_raw, list) else current_raw.get("data", [])
    prior_rows = prior_raw if isinstance(prior_raw, list) else prior_raw.get("data", [])

    if not current_rows:
        logger.warning("microsoft_no_data", date_range=f"{start_date} to {end_date}")
        return MicrosoftOverviewResponse(connected=True, live=True)

    cur = _aggregate_campaigns(current_rows)
    prev = _aggregate_campaigns(prior_rows)
    campaigns = _format_campaigns(current_rows)

    return MicrosoftOverviewResponse(
        connected=True,
        live=True,
        spend=cur["spend"],
        spend_change=_calc_change(cur["spend"], prev["spend"]),
        impressions=cur["impressions"],
        impressions_change=_calc_change(cur["impressions"], prev["impressions"]),
        clicks=cur["clicks"],
        clicks_change=_calc_change(cur["clicks"], prev["clicks"]),
        ctr=cur["ctr"],
        ctr_change=_calc_change(cur["ctr"], prev["ctr"]),
        cpc=cur["cpc"],
        cpc_change=_calc_change(cur["cpc"], prev["cpc"]),
        leads=cur["leads"],
        leads_change=_calc_change(cur["leads"], prev["leads"]),
        cost_per_lead=cur["cost_per_lead"],
        cost_per_lead_change=_calc_change(cur["cost_per_lead"], prev["cost_per_lead"]),
        conversions=cur["conversions"],
        conversions_change=_calc_change(cur["conversions"], prev["conversions"]),
        cost_per_conversion=cur["cost_per_conversion"],
        campaigns=campaigns,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/campaigns")
async def get_microsoft_campaigns(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Return campaign-level Microsoft Ads performance via MCP Gateway."""
    settings = get_settings()
    mcp = get_mcp_client(
        gateway_url=settings.gateway_url,
        gateway_token=settings.gateway_token,
    )

    if not mcp.is_configured or not start_date or not end_date:
        return []

    try:
        raw = await mcp.call_tool("microsoft_ads_campaign_performance", {
            "accountId": SCHUMACHER_MICROSOFT_ACCOUNT_ID,
            "startDate": start_date,
            "endDate": end_date,
        })
        rows = raw if isinstance(raw, list) else raw.get("data", [])
        return _format_campaigns(rows)
    except Exception as e:
        logger.error("microsoft_campaigns_error", error=str(e))
        return []


def _build_microsoft_active_ads_tree(
    campaign_rows: list,
    ad_group_rows: list,
    mode: str,
) -> dict:
    """
    Build a campaign -> ad group tree from Microsoft Ads performance rows.

    campaign_rows: from microsoft_ads_campaign_performance
    ad_group_rows: from microsoft_ads_ad_group_performance
    mode: "active" or "with_spend"
    """
    # Index ad groups by CampaignId
    groups_by_campaign: dict = {}
    for ag in ad_group_rows:
        cid = str(ag.get("CampaignId", ""))
        if cid not in groups_by_campaign:
            groups_by_campaign[cid] = []
        groups_by_campaign[cid].append(ag)

    campaigns_out = []
    total_leaf_items = 0

    for row in campaign_rows:
        c_spend = _parse_float(row.get("Spend", 0))
        c_clicks = _parse_int(row.get("Clicks", 0))
        c_impressions = _parse_int(row.get("Impressions", 0))
        c_conversions = _parse_int(row.get("Conversions", 0))
        c_status = row.get("CampaignStatus", "")
        cid = str(row.get("CampaignId", ""))

        # mode=active: skip paused/removed campaigns
        if mode == "active" and c_status.lower() not in ("active", "enabled"):
            continue
        # mode=with_spend: skip zero-spend campaigns
        if mode == "with_spend" and c_spend <= 0:
            continue

        c_name = row.get("CampaignName", "")
        is_pmax = "performance max" in c_name.lower()

        # Build ad groups for this campaign
        adsets = []
        for ag in groups_by_campaign.get(cid, []):
            ag_spend = _parse_float(ag.get("Spend", 0))
            ag_clicks = _parse_int(ag.get("Clicks", 0))
            ag_impressions = _parse_int(ag.get("Impressions", 0))
            ag_conversions = _parse_int(ag.get("Conversions", 0))
            ag_status = ag.get("AdGroupStatus", "")

            if mode == "active" and ag_status.lower() not in ("active", "enabled"):
                continue
            if mode == "with_spend" and ag_spend <= 0:
                continue

            adsets.append({
                "id": str(ag.get("AdGroupId", "")),
                "name": ag.get("AdGroupName", ""),
                "status": ag_status,
                "ad_count": 0,
                "spend": round(ag_spend, 2),
                "impressions": ag_impressions,
                "clicks": ag_clicks,
                "ctr": round(ag_clicks / ag_impressions * 100, 2) if ag_impressions else 0,
                "cpc": round(ag_spend / ag_clicks, 2) if ag_clicks else 0,
                "leads": ag_conversions,
                "cost_per_lead": round(ag_spend / ag_conversions, 2) if ag_conversions else 0,
                "ads": [],
            })

        adsets.sort(key=lambda x: x["spend"], reverse=True)
        adset_count = len(adsets)
        total_leaf_items += adset_count

        leads = c_conversions
        cpl = round(c_spend / leads, 2) if leads else 0

        campaigns_out.append({
            "id": cid,
            "name": c_name,
            "status": c_status,
            "is_pmax": is_pmax,
            "adset_count": adset_count,
            "ad_count": 0,
            "spend": round(c_spend, 2),
            "impressions": c_impressions,
            "clicks": c_clicks,
            "ctr": round(c_clicks / c_impressions * 100, 2) if c_impressions else 0,
            "cpc": round(c_spend / c_clicks, 2) if c_clicks else 0,
            "leads": leads,
            "cost_per_lead": cpl,
            "adsets": adsets,
        })

    campaigns_out.sort(key=lambda x: x["spend"], reverse=True)
    return {
        "success": True,
        "total_active_ads": total_leaf_items,
        "mode": mode,
        "campaigns": campaigns_out,
    }


@router.get("/active-ads-tree")
async def get_microsoft_active_ads_tree(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    mode: str = Query("active"),
):
    """Get Microsoft Ads campaign → ad group hierarchy with performance metrics."""
    if not start_date or not end_date:
        return {"success": False, "total_active_ads": 0, "campaigns": [], "error": "Date range required"}

    settings = get_settings()
    mcp = get_mcp_client(
        gateway_url=settings.gateway_url,
        gateway_token=settings.gateway_token,
    )

    if not mcp.is_configured:
        return {"success": False, "total_active_ads": 0, "campaigns": [], "error": "Microsoft Ads gateway not configured"}

    account_id = SCHUMACHER_MICROSOFT_ACCOUNT_ID

    try:
        campaign_raw, ad_group_raw = await asyncio.gather(
            mcp.call_tool("microsoft_ads_campaign_performance", {
                "accountId": account_id,
                "startDate": start_date,
                "endDate": end_date,
            }),
            mcp.call_tool("microsoft_ads_ad_group_performance", {
                "accountId": account_id,
                "startDate": start_date,
                "endDate": end_date,
            }),
        )
    except Exception as e:
        logger.error("microsoft_active_ads_tree_error", error=str(e))
        return {"success": False, "total_active_ads": 0, "campaigns": [], "error": str(e)}

    campaign_rows = campaign_raw if isinstance(campaign_raw, list) else campaign_raw.get("data", [])
    ad_group_rows = ad_group_raw if isinstance(ad_group_raw, list) else ad_group_raw.get("data", [])

    return _build_microsoft_active_ads_tree(campaign_rows, ad_group_rows, mode)


@router.get("/status")
async def get_microsoft_status():
    """Check if Microsoft Ads gateway is configured."""
    settings = get_settings()
    mcp = get_mcp_client(
        gateway_url=settings.gateway_url,
        gateway_token=settings.gateway_token,
    )
    return {
        "live": mcp.is_configured,
        "source": "gateway" if mcp.is_configured else "none",
        "account_id": SCHUMACHER_MICROSOFT_ACCOUNT_ID,
    }
