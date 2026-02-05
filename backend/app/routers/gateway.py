"""
Gateway API Router - Proxy endpoints for fetching live ad platform data.

These endpoints allow the JARVIS bot to fetch real-time data from
Meta, Google Ads, and other platforms via direct API calls or MCP Gateway.
"""

import os
import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.services.live_api import LiveAPIService, DateRange
from app.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])

# MCP Gateway configuration
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "https://gatewayapi-production.up.railway.app")
MCP_GATEWAY_TOKEN = os.getenv("MCP_GATEWAY_TOKEN", "sg_NDhjNzU3NjctMGZhZC00MDQzLTg3MzctMzkzYjZl")


@router.get("/meta/account-insights")
async def get_meta_account_insights(
    account_id: str = Query(default="act_142003632", description="Meta ad account ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Fetch Meta account insights for a specific date range.

    This endpoint uses the LiveAPIService to fetch data directly from Meta Graph API.
    """
    logger.info(
        "meta_account_insights_request",
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        settings = get_settings()

        # Check if Meta access token is configured
        if not settings.meta_access_token:
            logger.warning("meta_token_not_configured")
            return {
                "success": False,
                "error": "Meta access token not configured",
                "message": "Please configure META_ACCESS_TOKEN in your .env file to enable live data fetching.",
            }

        # Use LiveAPIService to fetch data
        service = LiveAPIService(meta_access_token=settings.meta_access_token)
        date_range = DateRange(start_date=start_date, end_date=end_date)

        result = await service.get_meta_account_insights(
            account_id=account_id,
            date_range=date_range,
            level="account"
        )

        if result.get("success"):
            return {
                "success": True,
                "account_id": account_id,
                "date_range": {"start": start_date, "end": end_date},
                "data": result.get("data", []),
            }
        else:
            logger.warning("meta_api_failed", error=result.get("error"))
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "detail": result.get("detail", ""),
            }

    except Exception as e:
        logger.error("meta_insights_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/campaign-report")
async def get_meta_campaign_report(
    account_id: str = Query(default="act_142003632", description="Meta ad account ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Fetch Meta campaign-level performance report for a specific date range.
    """
    logger.info(
        "meta_campaign_report_request",
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        settings = get_settings()

        # Check if Meta access token is configured
        if not settings.meta_access_token:
            logger.warning("meta_token_not_configured")
            return {
                "success": False,
                "error": "Meta access token not configured",
            }

        # Use LiveAPIService to fetch campaign data
        service = LiveAPIService(meta_access_token=settings.meta_access_token)
        date_range = DateRange(start_date=start_date, end_date=end_date)

        result = await service.get_meta_campaigns(
            account_id=account_id,
            date_range=date_range
        )

        if result.get("success"):
            return {
                "success": True,
                "account_id": account_id,
                "date_range": {"start": start_date, "end": end_date},
                "campaigns": result.get("campaigns", []),
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
            }

    except Exception as e:
        logger.error("campaign_report_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def gateway_status():
    """Check MCP Gateway connection status."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MCP_GATEWAY_URL}/health")
            return {
                "gateway_url": MCP_GATEWAY_URL,
                "status": "connected" if response.status_code == 200 else "error",
                "response_code": response.status_code,
            }
    except httpx.ConnectError:
        return {
            "gateway_url": MCP_GATEWAY_URL,
            "status": "disconnected",
            "message": "Cannot connect to MCP Gateway",
        }
    except Exception as e:
        return {
            "gateway_url": MCP_GATEWAY_URL,
            "status": "error",
            "error": str(e),
        }
