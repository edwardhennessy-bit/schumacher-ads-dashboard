"""
Google Ads Metrics Router — dashboard endpoints for Google Ads data.

Mirrors the structure of the Meta metrics router so the frontend
can use the same component patterns for both platforms.
"""

from fastapi import APIRouter, Query
from typing import List, Optional
import asyncio
import structlog

from app.models.schemas import MetricsOverview, DailyMetric, Campaign
from app.services.google_ads_api import (
    GoogleAdsService,
    SCHUMACHER_GOOGLE_CUSTOMER_ID,
    transform_gateway_campaign_data,
)
from app.services.live_api import DateRange
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/google", tags=["google-ads"])


def _get_google_service() -> GoogleAdsService:
    """Create a GoogleAdsService with credentials from settings."""
    settings = get_settings()
    return GoogleAdsService(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
        refresh_token=settings.google_ads_refresh_token,
    )


def _calc_change(current: float, previous: float) -> float:
    """Calculate percentage change."""
    if previous == 0:
        return 0
    return round(((current - previous) / previous) * 100, 1)


@router.get("/overview", response_model=MetricsOverview)
async def get_google_overview(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """Get Google Ads account-level metrics overview."""
    if not start_date or not end_date:
        return MetricsOverview()  # empty defaults

    settings = get_settings()
    customer_id = settings.google_ads_customer_id or SCHUMACHER_GOOGLE_CUSTOMER_ID
    service = _get_google_service()

    if not service.is_configured:
        logger.warning("google_ads_not_configured")
        return MetricsOverview()

    date_range = DateRange(start_date=start_date, end_date=end_date)
    prior_range = date_range.get_prior_month_equivalent()

    try:
        current_result, prior_result = await asyncio.gather(
            service.get_account_performance(customer_id, date_range),
            service.get_account_performance(customer_id, prior_range),
        )

        if not current_result.get("success"):
            logger.warning("google_overview_failed", error=current_result.get("error"))
            return MetricsOverview()

        cur = current_result
        prev = prior_result if prior_result.get("success") else {}

        spend = cur.get("spend", 0)
        impressions = cur.get("impressions", 0)
        clicks = cur.get("clicks", 0)
        leads = cur.get("leads", 0)
        ctr = cur.get("ctr", 0)
        cpc = cur.get("cpc", 0)
        cpl = cur.get("cost_per_lead", 0)

        return MetricsOverview(
            spend=spend,
            spend_change=_calc_change(spend, prev.get("spend", 0)),
            impressions=impressions,
            impressions_change=_calc_change(impressions, prev.get("impressions", 0)),
            clicks=clicks,
            clicks_change=_calc_change(clicks, prev.get("clicks", 0)),
            ctr=round(ctr, 2),
            ctr_change=_calc_change(ctr, prev.get("ctr", 0)),
            cpc=round(cpc, 2),
            cpc_change=_calc_change(cpc, prev.get("cpc", 0)),
            leads=leads,
            leads_change=_calc_change(leads, prev.get("leads", 0)),
            cost_per_lead=cpl,
            cost_per_lead_change=_calc_change(cpl, prev.get("cost_per_lead", 0)),
        )

    except Exception as e:
        logger.error("google_overview_error", error=str(e))
        return MetricsOverview()


@router.get("/campaigns")
async def get_google_campaigns(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """Get Google Ads campaign-level performance data."""
    if not start_date or not end_date:
        return []

    settings = get_settings()
    customer_id = settings.google_ads_customer_id or SCHUMACHER_GOOGLE_CUSTOMER_ID
    service = _get_google_service()

    if not service.is_configured:
        return []

    date_range = DateRange(start_date=start_date, end_date=end_date)

    try:
        result = await service.get_campaign_performance(customer_id, date_range)
        if result.get("success"):
            return result.get("campaigns", [])
        return []
    except Exception as e:
        logger.error("google_campaigns_error", error=str(e))
        return []


@router.get("/trends")
async def get_google_trends(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get daily Google Ads trend data for charts."""
    if not start_date or not end_date:
        return []

    settings = get_settings()
    customer_id = settings.google_ads_customer_id or SCHUMACHER_GOOGLE_CUSTOMER_ID
    service = _get_google_service()

    if not service.is_configured:
        return []

    date_range = DateRange(start_date=start_date, end_date=end_date)

    try:
        result = await service.get_daily_performance(customer_id, date_range)
        if result.get("success"):
            return result.get("data", [])
        return []
    except Exception as e:
        logger.error("google_trends_error", error=str(e))
        return []


@router.get("/status")
async def get_google_status():
    """Check if Google Ads is configured and connected."""
    service = _get_google_service()
    settings = get_settings()
    return {
        "configured": service.is_configured,
        "customer_id": settings.google_ads_customer_id or SCHUMACHER_GOOGLE_CUSTOMER_ID,
    }
