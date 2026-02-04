from fastapi import APIRouter, HTTPException
from typing import List

from app.models.schemas import Campaign
from app.services.meta_ads import MetaAdsService
from app.services.mock_data import MockDataService

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


@router.get("", response_model=List[Campaign])
async def list_campaigns():
    """List all campaigns with insights."""
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
    # Mock response - will be implemented with real data later
    return {
        "campaign_id": campaign_id,
        "adsets": [],
        "message": "Ad sets endpoint - will be implemented with real Meta Ads data",
    }


@router.get("/{campaign_id}/ads")
async def get_campaign_ads(campaign_id: str):
    """Get ads within a campaign."""
    # Mock response - will be implemented with real data later
    return {
        "campaign_id": campaign_id,
        "ads": [],
        "message": "Ads endpoint - will be implemented with real Meta Ads data",
    }
