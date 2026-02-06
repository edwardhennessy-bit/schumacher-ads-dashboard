from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import structlog

from app.models.schemas import Campaign
from app.services.meta_ads import MetaAdsService
from app.services.mock_data import MockDataService
from app.services.live_api import LiveAPIService, DateRange
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

# Use real Meta Ads service, fallback to mock if no data
meta_service = MetaAdsService()
mock_service = MockDataService()


def get_service():
    """Get the appropriate service based on data availability."""
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


def _build_campaigns_from_live(campaigns_data: list) -> List[Campaign]:
    """Transform raw Meta API campaign data into Campaign schema list."""
    campaigns = []
    for camp in campaigns_data:
        spend = float(camp.get("spend", 0))
        impressions = int(camp.get("impressions", 0))
        clicks = int(camp.get("clicks", 0))
        ctr = float(camp.get("ctr", 0))
        cpc = float(camp.get("cpc", 0))

        actions = camp.get("actions", [])
        leads = _extract_action_value(actions, "lead")
        conversions = _extract_action_value(actions, "offsite_conversion.fb_pixel_lead")
        if conversions == 0:
            conversions = leads

        cost_per_lead = round(spend / leads, 2) if leads > 0 else 0
        cost_per_conversion = round(spend / conversions, 2) if conversions > 0 else 0
        lead_rate = round((leads / clicks) * 100, 2) if clicks > 0 else 0

        campaigns.append(Campaign(
            id=camp.get("campaign_id", ""),
            name=camp.get("campaign_name", "Unknown"),
            status="ACTIVE",
            objective=camp.get("objective", "UNKNOWN"),
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            ctr=round(ctr, 2),
            cpc=round(cpc, 2),
            conversions=conversions,
            cost_per_conversion=cost_per_conversion,
            leads=leads,
            cost_per_lead=cost_per_lead,
            lead_rate=lead_rate,
        ))
    return campaigns


@router.get("", response_model=List[Campaign])
async def list_campaigns(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """List all campaigns with insights."""
    if start_date and end_date:
        settings = get_settings()
        if settings.meta_access_token:
            try:
                live_service = LiveAPIService(meta_access_token=settings.meta_access_token)
                date_range = DateRange(start_date=start_date, end_date=end_date)
                account_id = settings.meta_ad_account_id or "act_142003632"

                result = await live_service.get_meta_campaigns(account_id, date_range)

                if result.get("success") and result.get("campaigns"):
                    return _build_campaigns_from_live(result["campaigns"])

                logger.warning("live_campaigns_no_data", date_range=f"{start_date} to {end_date}")
            except Exception as e:
                logger.error("live_campaigns_error", error=str(e))

    # Fallback: cached data
    service = get_service()
    return service.get_campaigns()


@router.get("/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    """Get a single campaign by ID."""
    service = get_service()
    campaigns = service.get_campaigns()
    for campaign in campaigns:
        if campaign.id == campaign_id:
            return campaign
    raise HTTPException(status_code=404, detail="Campaign not found")


@router.get("/{campaign_id}/adsets")
async def get_campaign_adsets(campaign_id: str):
    """Get ad sets within a campaign."""
    return {
        "campaign_id": campaign_id,
        "adsets": [],
        "message": "Ad sets endpoint - will be implemented with real Meta Ads data",
    }


@router.get("/{campaign_id}/ads")
async def get_campaign_ads(campaign_id: str):
    """Get ads within a campaign."""
    return {
        "campaign_id": campaign_id,
        "ads": [],
        "message": "Ads endpoint - will be implemented with real Meta Ads data",
    }
