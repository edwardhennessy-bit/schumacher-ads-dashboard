"""
Google Ads API Service for fetching live performance data.

Uses the Google Ads REST API (v18) via httpx to fetch campaign
and account-level performance data.

When Google Ads credentials are not configured, uses the MCP Gateway
endpoint as a fallback (requires the gateway URL and token in config).
"""

import httpx
import json as _json
import structlog
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.services.live_api import DateRange

logger = structlog.get_logger(__name__)

# Google Ads REST API base
GOOGLE_ADS_API_BASE = "https://googleads.googleapis.com/v18"

# Schumacher Homes Google Ads IDs
SCHUMACHER_GOOGLE_CUSTOMER_ID = "3428920141"
MCC_CUSTOMER_ID = "5405350977"


class GoogleAdsService:
    """
    Service for fetching Google Ads performance data.

    Connects to the Google Ads REST API v18 via httpx.
    Falls back to the MCP Gateway HTTP endpoint when direct
    API credentials are not available.
    """

    def __init__(
        self,
        developer_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        gateway_url: Optional[str] = None,
        gateway_token: Optional[str] = None,
    ):
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.gateway_url = gateway_url
        self.gateway_token = gateway_token
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        """Check if direct Google Ads API credentials are configured."""
        return bool(
            self.developer_token
            and self.client_id
            and self.client_secret
            and self.refresh_token
        )

    @property
    def has_gateway(self) -> bool:
        """Check if MCP Gateway is configured for fallback."""
        return bool(self.gateway_url and self.gateway_token)

    async def _get_access_token(self) -> Optional[str]:
        """Get or refresh OAuth2 access token for direct API access."""
        if not self.is_configured:
            return None

        if (
            self._access_token
            and self._token_expiry
            and datetime.now() < self._token_expiry
        ):
            return self._access_token

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self._access_token = data["access_token"]
                from datetime import timedelta
                self._token_expiry = datetime.now() + timedelta(seconds=3000)
                return self._access_token
        except Exception as e:
            logger.error("google_ads_token_refresh_failed", error=str(e))
            return None

    async def _execute_gaql(
        self, customer_id: str, query: str
    ) -> Dict[str, Any]:
        """Execute a GAQL query via the Google Ads REST API."""
        access_token = await self._get_access_token()
        if not access_token:
            return {"success": False, "error": "No access token", "data": []}

        url = (
            f"{GOOGLE_ADS_API_BASE}/customers/{customer_id}"
            f"/googleAds:searchStream"
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": self.developer_token,
            "login-customer-id": MCC_CUSTOMER_ID,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    url, headers=headers, json={"query": query}
                )
                resp.raise_for_status()
                data = resp.json()
                results = []
                for batch in data:
                    results.extend(batch.get("results", []))
                return {"success": True, "data": results}
        except Exception as e:
            logger.error("google_ads_query_failed", error=str(e))
            return {"success": False, "error": str(e), "data": []}

    # ------------------------------------------------------------------
    # Gateway fallback helpers
    # ------------------------------------------------------------------

    async def _call_gateway(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP Gateway tool via its HTTP REST interface."""
        if not self.has_gateway:
            return {"success": False, "error": "Gateway not configured"}

        url = f"{self.gateway_url}/api/tools/{tool_name}"
        headers = {
            "Authorization": f"Bearer {self.gateway_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    url, headers=headers, json=arguments
                )
                resp.raise_for_status()
                return {"success": True, "data": resp.json()}
        except Exception as e:
            logger.error(
                "google_ads_gateway_call_failed",
                tool=tool_name,
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_account_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """
        Fetch account-level performance metrics for a date range.
        Returns spend, impressions, clicks, leads (conversions), ctr, cpc.
        """
        if self.is_configured:
            return await self._account_perf_direct(customer_id, date_range)

        # Fallback: derive from campaign data
        campaign_result = await self.get_campaign_performance(
            customer_id, date_range
        )
        if not campaign_result.get("success"):
            return campaign_result
        return {"success": True, **campaign_result.get("account", {})}

    async def _account_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = f"""
            SELECT
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM customer
            WHERE segments.date BETWEEN '{date_range.start_date}'
                AND '{date_range.end_date}'
        """
        result = await self._execute_gaql(customer_id, query)
        if not result["success"]:
            return result

        total = dict(
            spend=0.0, impressions=0, clicks=0, conversions=0.0, ctr=0.0, cpc=0.0
        )
        for row in result["data"]:
            m = row.get("metrics", {})
            total["spend"] += m.get("costMicros", 0) / 1_000_000
            total["impressions"] += m.get("impressions", 0)
            total["clicks"] += m.get("clicks", 0)
            total["conversions"] += m.get("conversions", 0)

        if total["impressions"]:
            total["ctr"] = total["clicks"] / total["impressions"] * 100
        if total["clicks"]:
            total["cpc"] = total["spend"] / total["clicks"]

        total["leads"] = round(total["conversions"])
        total["cost_per_lead"] = (
            round(total["spend"] / total["conversions"], 2)
            if total["conversions"]
            else 0
        )
        return {"success": True, **total}

    async def get_campaign_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """
        Fetch campaign-level performance data.
        Returns account totals + list of campaigns.
        """
        if self.is_configured:
            return await self._campaign_perf_direct(customer_id, date_range)

        # No direct API — return empty
        return {
            "success": False,
            "error": "Google Ads credentials not configured. Add GOOGLE_ADS_* variables to .env",
            "account": {},
            "campaigns": [],
        }

    async def _campaign_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE segments.date BETWEEN '{date_range.start_date}'
                AND '{date_range.end_date}'
                AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
        """
        result = await self._execute_gaql(customer_id, query)
        if not result["success"]:
            return result

        return _transform_campaign_rows(result["data"])

    async def get_daily_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """
        Fetch daily performance for trend charts.
        """
        if self.is_configured:
            return await self._daily_perf_direct(customer_id, date_range)

        return {
            "success": False,
            "error": "Google Ads credentials not configured",
            "data": [],
        }

    async def _daily_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = f"""
            SELECT
                segments.date,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM customer
            WHERE segments.date BETWEEN '{date_range.start_date}'
                AND '{date_range.end_date}'
            ORDER BY segments.date ASC
        """
        result = await self._execute_gaql(customer_id, query)
        if not result["success"]:
            return result

        daily = []
        for row in result["data"]:
            seg = row.get("segments", {})
            m = row.get("metrics", {})
            spend = m.get("costMicros", 0) / 1_000_000
            clicks = m.get("clicks", 0)
            conversions = m.get("conversions", 0)
            daily.append(
                {
                    "date": seg.get("date", ""),
                    "spend": round(spend, 2),
                    "impressions": m.get("impressions", 0),
                    "clicks": clicks,
                    "conversions": round(conversions),
                    "leads": round(conversions),
                    "ctr": round(m.get("ctr", 0) * 100, 2),
                    "cpc": round(spend / clicks, 2) if clicks else 0,
                    "cost_per_lead": (
                        round(spend / conversions, 2) if conversions else 0
                    ),
                }
            )
        return {"success": True, "data": daily}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _transform_campaign_rows(rows: List[Dict]) -> Dict[str, Any]:
    """Transform Google Ads campaign rows into our standard format."""
    campaigns = []
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0.0

    for row in rows:
        c = row.get("campaign", {})
        m = row.get("metrics", {})

        spend = m.get("costMicros", 0) / 1_000_000
        clicks = m.get("clicks", 0)
        conversions = m.get("conversions", 0)
        impressions = m.get("impressions", 0)

        if impressions == 0 and clicks == 0:
            continue  # skip removed campaigns with no data

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions

        status_raw = c.get("status", "")
        status = "ACTIVE" if status_raw in ("ENABLED", 2) else "PAUSED"

        campaigns.append(
            {
                "id": str(c.get("id", "")),
                "name": c.get("name", ""),
                "status": status,
                "objective": "",
                "spend": round(spend, 2),
                "impressions": impressions,
                "clicks": clicks,
                "ctr": round(m.get("ctr", 0) * 100, 2) if m.get("ctr") else (
                    round(clicks / impressions * 100, 2) if impressions else 0
                ),
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "conversions": round(conversions),
                "cost_per_conversion": (
                    round(spend / conversions, 2) if conversions else 0
                ),
                "leads": round(conversions),
                "cost_per_lead": (
                    round(spend / conversions, 2) if conversions else 0
                ),
                "lead_rate": (
                    round(conversions / clicks * 100, 2) if clicks else 0
                ),
            }
        )

    account = {
        "spend": round(total_spend, 2),
        "impressions": total_impressions,
        "clicks": total_clicks,
        "conversions": round(total_conversions),
        "leads": round(total_conversions),
        "ctr": (
            round(total_clicks / total_impressions * 100, 2)
            if total_impressions
            else 0
        ),
        "cpc": round(total_spend / total_clicks, 2) if total_clicks else 0,
        "cost_per_lead": (
            round(total_spend / total_conversions, 2)
            if total_conversions
            else 0
        ),
    }

    return {
        "success": True,
        "account": account,
        "campaigns": sorted(campaigns, key=lambda x: x["spend"], reverse=True),
    }


def transform_gateway_campaign_data(raw_data: List[Dict]) -> Dict[str, Any]:
    """
    Transform campaign data coming from the MCP gateway
    (googleads_campaign_performance tool) into our standard format.

    The gateway returns objects like:
    {
      "campaign": {"id": 123, "name": "...", "status": 2},
      "metrics": {"clicks": 100, "cost_micros": 3087355836, ...}
    }
    """
    return _transform_campaign_rows(raw_data)
