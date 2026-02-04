from fastapi import APIRouter, Query
from typing import List

from app.models.schemas import MetricsOverview, DailyMetric
from app.services.meta_ads import MetaAdsService
from app.services.mock_data import MockDataService

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


@router.get("/overview", response_model=MetricsOverview)
async def get_metrics_overview():
    """Get high-level metrics overview for the dashboard."""
    service = get_service()
    return service.get_metrics_overview()


@router.get("/trends", response_model=List[DailyMetric])
async def get_trend_data(days: int = Query(default=30, ge=1, le=90)):
    """Get daily trend data for charts."""
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
