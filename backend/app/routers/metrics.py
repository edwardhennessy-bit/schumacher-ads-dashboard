from fastapi import APIRouter, Query
from typing import List, Optional
import structlog

from app.models.schemas import MetricsOverview, DailyMetric
from app.services.meta_ads import MetaAdsService
from app.services.mock_data import MockDataService
from app.services.live_api import LiveAPIService, DateRange
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Use real Meta Ads service, fallback to mock if no data
meta_service = MetaAdsService()
mock_service = MockDataService()


def get_service():
    """Get the appropriate service based on data availability."""
    # Check if real data exists
    campaigns = meta_service.get_campaigns()
    if campaigns:
        return meta_service
    return mock_service


def _extract_action_value(actions: list, action_type: str) -> int:
    """Extract value for a specific action type from Meta API actions list."""
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == action_type:
            return int(action.get("value", 0))
    return 0


def _calc_change(current: float, previous: float) -> float:
    """Calculate percentage change between two values."""
    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 1)


def _segment_campaign_cpls(campaigns: list) -> dict:
    """Segment campaigns into remarketing and prospecting buckets and compute CPLs.

    Business rules:
      - Remarketing: campaign name contains 'remarketing' (case-insensitive)
      - Prospecting: campaign name does NOT contain 'remarketing' AND does NOT contain 'Visit'
      - Campaigns with 'Visit' in the name (TOF/website visitor) are excluded from both buckets
    """
    remarketing_spend = 0.0
    remarketing_leads = 0
    prospecting_spend = 0.0
    prospecting_leads = 0

    for camp in campaigns:
        name = camp.get("campaign_name", "")
        name_lower = name.lower()
        spend = float(camp.get("spend", 0))

        # Extract leads from actions
        leads = _extract_action_value(camp.get("actions", []), "lead")

        if "remarketing" in name_lower:
            remarketing_spend += spend
            remarketing_leads += leads
        elif "visit" not in name_lower:
            # Prospecting = everything that isn't remarketing and doesn't contain 'Visit'
            prospecting_spend += spend
            prospecting_leads += leads
        # else: "Visit" campaigns are excluded from both buckets

    remarketing_cpl = round(remarketing_spend / remarketing_leads, 2) if remarketing_leads > 0 else 0
    prospecting_cpl = round(prospecting_spend / prospecting_leads, 2) if prospecting_leads > 0 else 0

    return {
        "remarketing_leads": remarketing_leads,
        "remarketing_spend": round(remarketing_spend, 2),
        "remarketing_cpl": remarketing_cpl,
        "prospecting_leads": prospecting_leads,
        "prospecting_spend": round(prospecting_spend, 2),
        "prospecting_cpl": prospecting_cpl,
    }


def _build_overview_from_live(current_data: dict, previous_data: dict = None, campaign_data: list = None) -> MetricsOverview:
    """Transform raw Meta API response into MetricsOverview schema."""
    spend = float(current_data.get("spend", 0))
    impressions = int(current_data.get("impressions", 0))
    clicks = int(current_data.get("clicks", 0))
    ctr = float(current_data.get("ctr", 0))
    cpc = float(current_data.get("cpc", 0))
    cpm = float(current_data.get("cpm", 0))

    actions = current_data.get("actions", [])
    leads = _extract_action_value(actions, "lead")
    conversions = _extract_action_value(actions, "offsite_conversion.fb_pixel_lead")
    if conversions == 0:
        conversions = leads

    cost_per_lead = round(spend / leads, 2) if leads > 0 else 0
    lead_rate = round((leads / clicks) * 100, 2) if clicks > 0 else 0

    # Calculate changes from comparison period
    if previous_data:
        prev_spend = float(previous_data.get("spend", 0))
        prev_impressions = int(previous_data.get("impressions", 0))
        prev_clicks = int(previous_data.get("clicks", 0))
        prev_ctr = float(previous_data.get("ctr", 0))
        prev_cpc = float(previous_data.get("cpc", 0))
        prev_cpm = float(previous_data.get("cpm", 0))
        prev_actions = previous_data.get("actions", [])
        prev_leads = _extract_action_value(prev_actions, "lead")
        prev_conversions = _extract_action_value(prev_actions, "offsite_conversion.fb_pixel_lead")
        if prev_conversions == 0:
            prev_conversions = prev_leads
        prev_cpl = round(prev_spend / prev_leads, 2) if prev_leads > 0 else 0
        prev_lead_rate = round((prev_leads / prev_clicks) * 100, 2) if prev_clicks > 0 else 0

        spend_change = _calc_change(spend, prev_spend)
        impressions_change = _calc_change(impressions, prev_impressions)
        clicks_change = _calc_change(clicks, prev_clicks)
        ctr_change = _calc_change(ctr, prev_ctr)
        cpc_change = _calc_change(cpc, prev_cpc)
        cpm_change = _calc_change(cpm, prev_cpm)
        leads_change = _calc_change(leads, prev_leads)
        conversions_change = _calc_change(conversions, prev_conversions)
        cpl_change = _calc_change(cost_per_lead, prev_cpl)
        lead_rate_change = _calc_change(lead_rate, prev_lead_rate)
    else:
        spend_change = impressions_change = clicks_change = 0
        ctr_change = cpc_change = cpm_change = 0
        leads_change = conversions_change = cpl_change = lead_rate_change = 0

    # Segment campaign data for remarketing/prospecting CPLs
    segmented = _segment_campaign_cpls(campaign_data or [])

    # Ad inventory comes from cached data (always current snapshot)
    ad_inventory = meta_service._load_json("ad_inventory.json")
    if ad_inventory:
        active_ads = ad_inventory.get("active_ads", 0)
        total_ads = ad_inventory.get("total_ads", 0)
        active_ads_threshold = ad_inventory.get("threshold", 250)
    else:
        active_ads = 204
        total_ads = 2500
        active_ads_threshold = 250

    return MetricsOverview(
        spend=spend,
        spend_change=spend_change,
        impressions=impressions,
        impressions_change=impressions_change,
        clicks=clicks,
        clicks_change=clicks_change,
        ctr=round(ctr, 2),
        ctr_change=ctr_change,
        cpc=round(cpc, 2),
        cpc_change=cpc_change,
        cpm=round(cpm, 2),
        cpm_change=cpm_change,
        conversions=conversions,
        conversions_change=conversions_change,
        leads=leads,
        leads_change=leads_change,
        cost_per_lead=cost_per_lead,
        cost_per_lead_change=cpl_change,
        lead_rate=lead_rate,
        lead_rate_change=lead_rate_change,
        remarketing_leads=segmented["remarketing_leads"],
        remarketing_spend=segmented["remarketing_spend"],
        remarketing_cpl=segmented["remarketing_cpl"],
        prospecting_leads=segmented["prospecting_leads"],
        prospecting_spend=segmented["prospecting_spend"],
        prospecting_cpl=segmented["prospecting_cpl"],
        active_ads=active_ads,
        total_ads=total_ads,
        active_ads_threshold=active_ads_threshold,
    )


@router.get("/overview", response_model=MetricsOverview)
async def get_metrics_overview(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """Get high-level metrics overview for the dashboard."""
    if start_date and end_date:
        settings = get_settings()
        if settings.meta_access_token:
            try:
                live_service = LiveAPIService(meta_access_token=settings.meta_access_token)
                date_range = DateRange(start_date=start_date, end_date=end_date)
                account_id = settings.meta_ad_account_id or "act_142003632"

                # Compare against same date range shifted back one month (apples-to-apples)
                prior_month_range = date_range.get_prior_month_equivalent()

                import asyncio
                current_result, prior_month_result, campaign_result = await asyncio.gather(
                    live_service.get_meta_account_insights(account_id, date_range),
                    live_service.get_meta_account_insights(account_id, prior_month_range),
                    live_service.get_meta_campaigns(account_id, date_range),
                )

                if current_result.get("success") and current_result.get("data"):
                    current_data = current_result["data"][0]
                    previous_data = prior_month_result["data"][0] if prior_month_result.get("success") and prior_month_result.get("data") else None
                    campaign_data = campaign_result.get("campaigns", []) if campaign_result.get("success") else []
                    return _build_overview_from_live(current_data, previous_data, campaign_data)

                logger.warning("live_overview_no_data", date_range=f"{start_date} to {end_date}")
            except Exception as e:
                logger.error("live_overview_error", error=str(e))

    # Fallback: cached data
    service = get_service()
    return service.get_metrics_overview()


@router.get("/trends", response_model=List[DailyMetric])
async def get_trend_data(
    days: int = Query(default=30, ge=1, le=365),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """Get daily trend data for charts."""
    if start_date and end_date:
        settings = get_settings()
        if settings.meta_access_token:
            try:
                live_service = LiveAPIService(meta_access_token=settings.meta_access_token)
                date_range = DateRange(start_date=start_date, end_date=end_date)
                account_id = settings.meta_ad_account_id or "act_142003632"

                result = await live_service.get_meta_daily_insights(account_id, date_range)

                if result.get("success") and result.get("data"):
                    daily_metrics = []
                    for day_data in result["data"]:
                        spend = float(day_data.get("spend", 0))
                        impressions = int(day_data.get("impressions", 0))
                        clicks = int(day_data.get("clicks", 0))
                        actions = day_data.get("actions", [])
                        leads = _extract_action_value(actions, "lead")
                        conversions = _extract_action_value(actions, "offsite_conversion.fb_pixel_lead")
                        if conversions == 0:
                            conversions = leads

                        daily_metrics.append(DailyMetric(
                            date=day_data.get("date_start", ""),
                            spend=spend,
                            impressions=impressions,
                            clicks=clicks,
                            conversions=conversions,
                            leads=leads,
                            ctr=round(float(day_data.get("ctr", 0)), 2),
                            cpc=round(float(day_data.get("cpc", 0)), 2),
                            cpm=round(float(day_data.get("cpm", 0)), 2),
                            cost_per_lead=round(spend / leads, 2) if leads > 0 else 0,
                        ))
                    return daily_metrics

                logger.warning("live_trends_no_data", date_range=f"{start_date} to {end_date}")
            except Exception as e:
                logger.error("live_trends_error", error=str(e))

    # Fallback: cached data
    service = get_service()
    return service.get_trend_data(days=days)


@router.get("/inventory")
async def get_ad_inventory():
    """Get active vs paused ad counts."""
    service = get_service()
    overview = service.get_metrics_overview()
    return {
        "active": overview.active_ads,
        "total": overview.total_ads,
        "paused": overview.total_ads - overview.active_ads,
    }
