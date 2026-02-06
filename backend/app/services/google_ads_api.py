"""
Google Ads API Service for fetching live performance data.

Primary data source: MCP Gateway (googleads_* tools)
Fallback: Direct Google Ads REST API v18 (requires OAuth credentials)
"""

import httpx
import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.services.live_api import DateRange
from app.services.mcp_client import MCPGatewayClient

logger = structlog.get_logger(__name__)

# Schumacher Homes Google Ads IDs
SCHUMACHER_GOOGLE_CUSTOMER_ID = "3428920141"
MCC_CUSTOMER_ID = "5405350977"

# Google Ads REST API base (for direct API fallback)
GOOGLE_ADS_API_BASE = "https://googleads.googleapis.com/v18"


class GoogleAdsService:
    """
    Service for fetching Google Ads performance data.

    Uses the MCP Gateway as the primary data source.
    Falls back to direct Google Ads REST API when gateway is unavailable.
    """

    def __init__(
        self,
        mcp_client: Optional[MCPGatewayClient] = None,
        developer_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.mcp_client = mcp_client
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def has_gateway(self) -> bool:
        """Check if MCP Gateway client is available."""
        return self.mcp_client is not None and self.mcp_client.is_configured

    @property
    def has_direct_api(self) -> bool:
        """Check if direct Google Ads API credentials are configured."""
        return bool(
            self.developer_token
            and self.client_id
            and self.client_secret
            and self.refresh_token
        )

    @property
    def is_configured(self) -> bool:
        """Check if any data source is available."""
        return self.has_gateway or self.has_direct_api

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_account_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """Fetch account-level performance metrics for a date range."""
        if self.has_gateway:
            return await self._account_perf_gateway(customer_id, date_range)
        if self.has_direct_api:
            return await self._account_perf_direct(customer_id, date_range)
        return {"success": False, "error": "No data source configured"}

    async def get_campaign_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """Fetch campaign-level performance data."""
        if self.has_gateway:
            return await self._campaign_perf_gateway(customer_id, date_range)
        if self.has_direct_api:
            return await self._campaign_perf_direct(customer_id, date_range)
        return {"success": False, "error": "No data source configured", "campaigns": []}

    async def get_daily_performance(
        self,
        customer_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """Fetch daily performance for trend charts."""
        if self.has_gateway:
            return await self._daily_perf_gateway(customer_id, date_range)
        if self.has_direct_api:
            return await self._daily_perf_direct(customer_id, date_range)
        return {"success": False, "error": "No data source configured", "data": []}

    # ------------------------------------------------------------------
    # Gateway implementations
    # ------------------------------------------------------------------

    async def _account_perf_gateway(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        """Get account performance by aggregating campaign data from gateway."""
        result = await self._campaign_perf_gateway(customer_id, date_range)
        if not result.get("success"):
            return result
        return {"success": True, **result.get("account", {})}

    async def _campaign_perf_gateway(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch campaign performance via MCP gateway."""
        raw = await self.mcp_client.call_tool(
            "googleads_campaign_performance",
            {
                "customerId": customer_id,
                "startDate": date_range.start_date,
                "endDate": date_range.end_date,
                "limit": 100,
            },
        )

        if "error" in raw:
            logger.warning("gateway_campaign_perf_error", error=raw["error"])
            return {"success": False, "error": raw["error"], "campaigns": []}

        # Gateway returns {"data": [...]}
        campaigns_raw = raw.get("data", [])
        if not campaigns_raw:
            return {"success": True, "account": _empty_account(), "campaigns": []}

        return _transform_campaign_rows(campaigns_raw)

    async def _daily_perf_gateway(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        """Fetch daily performance via MCP gateway GAQL query."""
        query = (
            f"SELECT segments.date, metrics.cost_micros, metrics.impressions, "
            f"metrics.clicks, metrics.conversions, metrics.ctr, metrics.average_cpc "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' "
            f"ORDER BY segments.date ASC"
        )

        raw = await self.mcp_client.call_tool(
            "googleads_query",
            {
                "customerId": customer_id,
                "query": query,
            },
        )

        if isinstance(raw, dict) and "error" in raw:
            logger.warning("gateway_daily_perf_error", error=raw["error"])
            return {"success": False, "error": raw["error"], "data": []}

        rows = raw if isinstance(raw, list) else raw.get("data", raw.get("results", []))
        if not rows:
            return {"success": True, "data": []}

        daily = []
        for row in rows:
            seg = row.get("segments", {})
            m = row.get("metrics", {})
            cost_micros = m.get("cost_micros", m.get("costMicros", 0))
            spend = cost_micros / 1_000_000
            clicks = m.get("clicks", 0)
            conversions = m.get("conversions", 0)
            if isinstance(conversions, str):
                conversions = float(conversions)

            daily.append({
                "date": seg.get("date", ""),
                "spend": round(spend, 2),
                "impressions": m.get("impressions", 0),
                "clicks": clicks,
                "conversions": round(conversions),
                "leads": round(conversions),
                "ctr": round(m.get("ctr", 0) * 100, 2),
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "cost_per_lead": round(spend / conversions, 2) if conversions else 0,
            })

        return {"success": True, "data": daily}

    # ------------------------------------------------------------------
    # Direct API implementations (fallback)
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> Optional[str]:
        """Get or refresh OAuth2 access token for direct API access."""
        if not self.has_direct_api:
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

    async def _execute_gaql(self, customer_id: str, query: str) -> Dict[str, Any]:
        """Execute a GAQL query via the Google Ads REST API."""
        access_token = await self._get_access_token()
        if not access_token:
            return {"success": False, "error": "No access token", "data": []}

        url = f"{GOOGLE_ADS_API_BASE}/customers/{customer_id}/googleAds:searchStream"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": self.developer_token,
            "login-customer-id": MCC_CUSTOMER_ID,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json={"query": query})
                resp.raise_for_status()
                data = resp.json()
                results = []
                for batch in data:
                    results.extend(batch.get("results", []))
                return {"success": True, "data": results}
        except Exception as e:
            logger.error("google_ads_query_failed", error=str(e))
            return {"success": False, "error": str(e), "data": []}

    async def _account_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = (
            f"SELECT metrics.cost_micros, metrics.impressions, metrics.clicks, "
            f"metrics.conversions, metrics.ctr, metrics.average_cpc "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}'"
        )
        result = await self._execute_gaql(customer_id, query)
        if not result["success"]:
            return result

        total = dict(spend=0.0, impressions=0, clicks=0, conversions=0.0)
        for row in result["data"]:
            m = row.get("metrics", {})
            total["spend"] += m.get("costMicros", 0) / 1_000_000
            total["impressions"] += m.get("impressions", 0)
            total["clicks"] += m.get("clicks", 0)
            total["conversions"] += m.get("conversions", 0)

        if total["impressions"]:
            total["ctr"] = total["clicks"] / total["impressions"] * 100
        else:
            total["ctr"] = 0
        if total["clicks"]:
            total["cpc"] = total["spend"] / total["clicks"]
        else:
            total["cpc"] = 0

        total["leads"] = round(total["conversions"])
        total["cost_per_lead"] = (
            round(total["spend"] / total["conversions"], 2)
            if total["conversions"]
            else 0
        )
        return {"success": True, **total}

    async def _campaign_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = (
            f"SELECT campaign.id, campaign.name, campaign.status, "
            f"metrics.cost_micros, metrics.impressions, metrics.clicks, "
            f"metrics.conversions, metrics.ctr, metrics.average_cpc "
            f"FROM campaign "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' AND campaign.status != 'REMOVED' "
            f"ORDER BY metrics.cost_micros DESC"
        )
        result = await self._execute_gaql(customer_id, query)
        if not result["success"]:
            return result
        return _transform_campaign_rows(result["data"])

    async def _daily_perf_direct(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        query = (
            f"SELECT segments.date, metrics.cost_micros, metrics.impressions, "
            f"metrics.clicks, metrics.conversions, metrics.ctr, metrics.average_cpc "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' ORDER BY segments.date ASC"
        )
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
            daily.append({
                "date": seg.get("date", ""),
                "spend": round(spend, 2),
                "impressions": m.get("impressions", 0),
                "clicks": clicks,
                "conversions": round(conversions),
                "leads": round(conversions),
                "ctr": round(m.get("ctr", 0) * 100, 2),
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "cost_per_lead": round(spend / conversions, 2) if conversions else 0,
            })
        return {"success": True, "data": daily}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _empty_account() -> Dict[str, Any]:
    return {
        "spend": 0, "impressions": 0, "clicks": 0,
        "conversions": 0, "leads": 0, "ctr": 0, "cpc": 0, "cost_per_lead": 0,
    }


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

        # Handle both camelCase (REST API) and snake_case (gateway) field names
        cost_micros = m.get("cost_micros", m.get("costMicros", 0))
        spend = cost_micros / 1_000_000
        clicks = m.get("clicks", 0)
        conversions = m.get("conversions", 0)
        if isinstance(conversions, str):
            conversions = float(conversions)
        impressions = m.get("impressions", 0)

        if impressions == 0 and clicks == 0:
            continue

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions

        status_raw = c.get("status", "")
        status = "ACTIVE" if status_raw in ("ENABLED", 2) else "PAUSED"

        ctr_raw = m.get("ctr", 0)
        ctr = round(ctr_raw * 100, 2) if ctr_raw and ctr_raw < 1 else (
            round(ctr_raw, 2) if ctr_raw else (
                round(clicks / impressions * 100, 2) if impressions else 0
            )
        )

        campaigns.append({
            "id": str(c.get("id", "")),
            "name": c.get("name", ""),
            "status": status,
            "objective": "",
            "spend": round(spend, 2),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "cpc": round(spend / clicks, 2) if clicks else 0,
            "conversions": round(conversions),
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0,
            "leads": round(conversions),
            "cost_per_lead": round(spend / conversions, 2) if conversions else 0,
            "lead_rate": round(conversions / clicks * 100, 2) if clicks else 0,
        })

    account = {
        "spend": round(total_spend, 2),
        "impressions": total_impressions,
        "clicks": total_clicks,
        "conversions": round(total_conversions),
        "leads": round(total_conversions),
        "ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions else 0,
        "cpc": round(total_spend / total_clicks, 2) if total_clicks else 0,
        "cost_per_lead": round(total_spend / total_conversions, 2) if total_conversions else 0,
    }

    return {
        "success": True,
        "account": account,
        "campaigns": sorted(campaigns, key=lambda x: x["spend"], reverse=True),
    }
