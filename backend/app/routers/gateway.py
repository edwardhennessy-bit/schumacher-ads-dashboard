"""
Gateway API Router - Proxy endpoints for fetching live ad platform data.

These endpoints allow the JARVIS bot to fetch real-time data from
Meta, Google Ads, and other platforms via the MCP Gateway.
"""

import os
import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])

# MCP Gateway configuration
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://localhost:3001")


@router.get("/meta/account-insights")
async def get_meta_account_insights(
    account_id: str = Query(default="act_142003632", description="Meta ad account ID"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """
    Fetch Meta account insights for a specific date range.

    This endpoint proxies requests to the MCP Gateway to get live Meta Ads data.
    """
    logger.info(
        "meta_account_insights_request",
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        # Call MCP Gateway to get Meta account insights
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MCP_GATEWAY_URL}/tools/meta_account_insights",
                json={
                    "adAccountId": account_id,
                    "startDate": start_date,
                    "endDate": end_date,
                }
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {"start": start_date, "end": end_date},
                    "data": data,
                }
            else:
                logger.warning("mcp_gateway_error", status=response.status_code)
                return {
                    "success": False,
                    "error": f"Gateway returned status {response.status_code}",
                }

    except httpx.ConnectError:
        logger.warning("mcp_gateway_unavailable")
        # Return mock data or indicate gateway unavailable
        return {
            "success": False,
            "error": "MCP Gateway not available",
            "message": "Live data fetch unavailable. Using cached data.",
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{MCP_GATEWAY_URL}/tools/meta_campaign_report",
                json={
                    "adAccountId": account_id,
                    "startDate": start_date,
                    "endDate": end_date,
                }
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {"start": start_date, "end": end_date},
                    "campaigns": data,
                }
            else:
                return {
                    "success": False,
                    "error": f"Gateway returned status {response.status_code}",
                }

    except httpx.ConnectError:
        return {
            "success": False,
            "error": "MCP Gateway not available",
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
