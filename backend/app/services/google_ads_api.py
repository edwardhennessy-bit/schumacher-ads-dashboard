"""
Google Ads API Service for fetching live performance data.

Primary data source: MCP Gateway (googleads_* tools)
Fallback: Direct Google Ads REST API v18 (requires OAuth credentials)
"""

import asyncio
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

# Conversion action names from HubSpot integration
MQL_CONVERSION_ACTION = "HubSpot - Marketing Qualified Lead"
OPPORTUNITY_CONVERSION_ACTION = "HubSpot - Opportunity"

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
    # Conversion action query helpers (MQLs + Opportunities)
    # ------------------------------------------------------------------

    async def _get_conversions_by_campaign(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Dict[str, float]]:
        """
        Fetch MQL and Opportunity conversion counts per campaign.
        Returns {campaign_id: {"leads": X, "opportunities": Y}}.
        """
        query = (
            f"SELECT campaign.id, segments.conversion_action_name, metrics.all_conversions "
            f"FROM campaign "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' "
            f"AND campaign.status != 'REMOVED' "
            f"AND segments.conversion_action_name IN "
            f"('{MQL_CONVERSION_ACTION}', '{OPPORTUNITY_CONVERSION_ACTION}')"
        )
        if self.has_gateway:
            raw = await self.mcp_client.call_tool(
                "googleads_query",
                {"customerId": customer_id, "query": query},
            )
        elif self.has_direct_api:
            result = await self._execute_gaql(customer_id, query)
            if not result.get("success"):
                return {}
            raw = result.get("data", [])
        else:
            return {}
        return _parse_conversion_rows(raw)

    async def _get_daily_conversions(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Dict[str, float]]:
        """
        Fetch daily MQL and Opportunity conversion counts.
        Returns {date: {"leads": X, "opportunities": Y}}.
        """
        query = (
            f"SELECT segments.date, segments.conversion_action_name, metrics.all_conversions "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' "
            f"AND segments.conversion_action_name IN "
            f"('{MQL_CONVERSION_ACTION}', '{OPPORTUNITY_CONVERSION_ACTION}') "
            f"ORDER BY segments.date ASC"
        )
        if self.has_gateway:
            raw = await self.mcp_client.call_tool(
                "googleads_query",
                {"customerId": customer_id, "query": query},
            )
        elif self.has_direct_api:
            result = await self._execute_gaql(customer_id, query)
            if not result.get("success"):
                return {}
            raw = result.get("data", [])
        else:
            return {}
        return _parse_daily_conversion_rows(raw)

    # ------------------------------------------------------------------
    # Gateway implementations
    # ------------------------------------------------------------------

    async def _account_perf_gateway(
        self, customer_id: str, date_range: DateRange
    ) -> Dict[str, Any]:
        """Get account performance via direct GAQL account-level query."""
        # Account-level totals query
        account_query = (
            f"SELECT metrics.cost_micros, metrics.impressions, metrics.clicks, "
            f"metrics.conversions "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}'"
        )

        # Conversion action query for MQLs + Opportunities (use all_conversions
        # because these HubSpot actions are not included in primary "conversions")
        conv_query = (
            f"SELECT segments.conversion_action_name, metrics.all_conversions "
            f"FROM customer "
            f"WHERE segments.date BETWEEN '{date_range.start_date}' "
            f"AND '{date_range.end_date}' "
            f"AND segments.conversion_action_name IN "
            f"('{MQL_CONVERSION_ACTION}', '{OPPORTUNITY_CONVERSION_ACTION}')"
        )

        try:
            account_raw, conv_raw = await asyncio.gather(
                self.mcp_client.call_tool(
                    "googleads_query",
                    {"customerId": customer_id, "query": account_query},
                ),
                self.mcp_client.call_tool(
                    "googleads_query",
                    {"customerId": customer_id, "query": conv_query},
                ),
            )
        except Exception as e:
            logger.error("gateway_account_perf_error", error=str(e))
            return {"success": False, "error": str(e)}

        # Parse account totals
        rows = _normalize_rows(account_raw)
        if not rows:
            return {"success": True, **_empty_account()}

        row = rows[0]
        m = row.get("metrics", {})
        cost_micros = m.get("cost_micros", m.get("costMicros", 0))
        spend = cost_micros / 1_000_000
        impressions = m.get("impressions", 0)
        clicks = m.get("clicks", 0)

        # Parse conversion actions (using all_conversions)
        conv_rows = _normalize_rows(conv_raw)
        leads = 0.0
        opportunities = 0.0
        for cr in conv_rows:
            seg = cr.get("segments", {})
            cm = cr.get("metrics", {})
            action_name = seg.get("conversion_action_name", seg.get("conversionActionName", ""))
            convs = cm.get("all_conversions", cm.get("allConversions", 0))
            if isinstance(convs, str):
                convs = float(convs)
            if action_name == MQL_CONVERSION_ACTION:
                leads += convs
            elif action_name == OPPORTUNITY_CONVERSION_ACTION:
                opportunities += convs

        return {
            "success": True,
            "spend": round(spend, 2),
            "impressions": impressions,
            "clicks": clicks,
            "conversions": round(leads + opportunities),
            "leads": round(leads),
            "opportunities": round(opportunities),
            "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
            "cpc": round(spend / clicks, 2) if clicks else 0,
            "cost_per_lead": round(spend / leads, 2) if leads else 0,
            "cost_per_opportunity": round(spend / opportunities, 2) if opportunities else 0,
        }

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

        # Fetch MQL + Opportunity conversions per campaign
        try:
            conv_data = await self._get_conversions_by_campaign(customer_id, date_range)
        except Exception as e:
            logger.warning("gateway_conversions_error", error=str(e))
            conv_data = {}

        return _transform_campaign_rows(campaigns_raw, conv_data)

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

        # Fetch daily MQL + Opportunity counts
        try:
            daily_convs = await self._get_daily_conversions(customer_id, date_range)
        except Exception as e:
            logger.warning("gateway_daily_convs_error", error=str(e))
            daily_convs = {}

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

            date_str = seg.get("date", "")
            day_convs = daily_convs.get(date_str, {})
            leads = day_convs.get("leads", 0)
            opportunities = day_convs.get("opportunities", 0)

            daily.append({
                "date": date_str,
                "spend": round(spend, 2),
                "impressions": m.get("impressions", 0),
                "clicks": clicks,
                "conversions": round(conversions),
                "leads": round(leads),
                "opportunities": round(opportunities),
                "ctr": round(m.get("ctr", 0) * 100, 2),
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "cost_per_lead": round(spend / leads, 2) if leads else 0,
                "cost_per_opportunity": round(spend / opportunities, 2) if opportunities else 0,
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

        # Fetch MQL + Opportunity conversions
        try:
            conv_data = await self._get_conversions_by_campaign(customer_id, date_range)
            total_leads = sum(c.get("leads", 0) for c in conv_data.values())
            total_opps = sum(c.get("opportunities", 0) for c in conv_data.values())
        except Exception:
            total_leads = 0
            total_opps = 0

        total["leads"] = round(total_leads)
        total["opportunities"] = round(total_opps)
        total["cost_per_lead"] = (
            round(total["spend"] / total_leads, 2) if total_leads else 0
        )
        total["cost_per_opportunity"] = (
            round(total["spend"] / total_opps, 2) if total_opps else 0
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

        # Fetch MQL + Opportunity conversions per campaign
        try:
            conv_data = await self._get_conversions_by_campaign(customer_id, date_range)
        except Exception as e:
            logger.warning("direct_conversions_error", error=str(e))
            conv_data = {}

        return _transform_campaign_rows(result["data"], conv_data)

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

        # Fetch daily MQL + Opportunity counts
        try:
            daily_convs = await self._get_daily_conversions(customer_id, date_range)
        except Exception:
            daily_convs = {}

        daily = []
        for row in result["data"]:
            seg = row.get("segments", {})
            m = row.get("metrics", {})
            spend = m.get("costMicros", 0) / 1_000_000
            clicks = m.get("clicks", 0)
            conversions = m.get("conversions", 0)
            date_str = seg.get("date", "")
            day_convs = daily_convs.get(date_str, {})
            leads = day_convs.get("leads", 0)
            opportunities = day_convs.get("opportunities", 0)

            daily.append({
                "date": date_str,
                "spend": round(spend, 2),
                "impressions": m.get("impressions", 0),
                "clicks": clicks,
                "conversions": round(conversions),
                "leads": round(leads),
                "opportunities": round(opportunities),
                "ctr": round(m.get("ctr", 0) * 100, 2),
                "cpc": round(spend / clicks, 2) if clicks else 0,
                "cost_per_lead": round(spend / leads, 2) if leads else 0,
                "cost_per_opportunity": round(spend / opportunities, 2) if opportunities else 0,
            })
        return {"success": True, "data": daily}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _empty_account() -> Dict[str, Any]:
    return {
        "spend": 0, "impressions": 0, "clicks": 0,
        "conversions": 0, "leads": 0, "opportunities": 0,
        "ctr": 0, "cpc": 0, "cost_per_lead": 0, "cost_per_opportunity": 0,
    }


def _normalize_rows(raw: Any) -> List[Dict]:
    """Normalize raw GAQL response into a list of row dicts."""
    if isinstance(raw, dict) and "error" in raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("data", raw.get("results", []))
    return []


def _parse_conversion_rows(raw: Any) -> Dict[str, Dict[str, float]]:
    """
    Parse GAQL conversion rows into {campaign_id: {"leads": X, "opportunities": Y}}.
    Uses all_conversions to capture HubSpot actions not in primary conversions.
    """
    rows = _normalize_rows(raw)
    result: Dict[str, Dict[str, float]] = {}
    for row in rows:
        c = row.get("campaign", {})
        seg = row.get("segments", {})
        m = row.get("metrics", {})
        cid = str(c.get("id", ""))
        action_name = seg.get("conversion_action_name", seg.get("conversionActionName", ""))
        convs = m.get("all_conversions", m.get("allConversions", m.get("conversions", 0)))
        if isinstance(convs, str):
            convs = float(convs)

        if cid not in result:
            result[cid] = {"leads": 0, "opportunities": 0}

        if action_name == MQL_CONVERSION_ACTION:
            result[cid]["leads"] += convs
        elif action_name == OPPORTUNITY_CONVERSION_ACTION:
            result[cid]["opportunities"] += convs
    return result


def _parse_daily_conversion_rows(raw: Any) -> Dict[str, Dict[str, float]]:
    """
    Parse GAQL daily conversion rows into {date: {"leads": X, "opportunities": Y}}.
    Uses all_conversions to capture HubSpot actions not in primary conversions.
    """
    rows = _normalize_rows(raw)
    result: Dict[str, Dict[str, float]] = {}
    for row in rows:
        seg = row.get("segments", {})
        m = row.get("metrics", {})
        date_str = seg.get("date", "")
        action_name = seg.get("conversion_action_name", seg.get("conversionActionName", ""))
        convs = m.get("all_conversions", m.get("allConversions", m.get("conversions", 0)))
        if isinstance(convs, str):
            convs = float(convs)

        if date_str not in result:
            result[date_str] = {"leads": 0, "opportunities": 0}

        if action_name == MQL_CONVERSION_ACTION:
            result[date_str]["leads"] += convs
        elif action_name == OPPORTUNITY_CONVERSION_ACTION:
            result[date_str]["opportunities"] += convs
    return result


def _transform_campaign_rows(
    rows: List[Dict],
    conversion_data: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Transform Google Ads campaign rows into our standard format.

    Args:
        rows: Raw campaign rows from Google Ads API.
        conversion_data: Optional dict of {campaign_id: {"leads": X, "opportunities": Y}}
            from GAQL conversion action queries. If None, falls back to total conversions.
    """
    campaigns = []
    total_spend = 0.0
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0.0
    total_leads = 0.0
    total_opportunities = 0.0

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

        campaign_id = str(c.get("id", ""))

        total_spend += spend
        total_impressions += impressions
        total_clicks += clicks
        total_conversions += conversions

        # Get MQL (leads) and Opportunity counts from conversion data
        if conversion_data is not None:
            camp_convs = conversion_data.get(campaign_id, {})
            leads = camp_convs.get("leads", 0)
            opportunities = camp_convs.get("opportunities", 0)
        else:
            leads = conversions
            opportunities = 0
        total_leads += leads
        total_opportunities += opportunities

        status_raw = c.get("status", "")
        status = "ACTIVE" if status_raw in ("ENABLED", 2) else "PAUSED"

        ctr_raw = m.get("ctr", 0)
        ctr = round(ctr_raw * 100, 2) if ctr_raw and ctr_raw < 1 else (
            round(ctr_raw, 2) if ctr_raw else (
                round(clicks / impressions * 100, 2) if impressions else 0
            )
        )

        campaigns.append({
            "id": campaign_id,
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
            "leads": round(leads),
            "cost_per_lead": round(spend / leads, 2) if leads else 0,
            "opportunities": round(opportunities),
            "cost_per_opportunity": round(spend / opportunities, 2) if opportunities else 0,
            "lead_rate": round(leads / clicks * 100, 2) if clicks else 0,
        })

    account = {
        "spend": round(total_spend, 2),
        "impressions": total_impressions,
        "clicks": total_clicks,
        "conversions": round(total_conversions),
        "leads": round(total_leads),
        "opportunities": round(total_opportunities),
        "ctr": round(total_clicks / total_impressions * 100, 2) if total_impressions else 0,
        "cpc": round(total_spend / total_clicks, 2) if total_clicks else 0,
        "cost_per_lead": round(total_spend / total_leads, 2) if total_leads else 0,
        "cost_per_opportunity": round(total_spend / total_opportunities, 2) if total_opportunities else 0,
    }

    return {
        "success": True,
        "account": account,
        "campaigns": sorted(campaigns, key=lambda x: x["spend"], reverse=True),
    }
