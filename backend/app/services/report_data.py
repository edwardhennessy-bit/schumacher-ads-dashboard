"""
Report data collector service.

Gathers performance data from all platforms and computes
cross-platform aggregates for report generation.
"""

import structlog
from typing import Any, Dict, Optional
from datetime import date, timedelta
from calendar import monthrange

from app.services.live_api import DateRange
from app.services.google_ads_api import GoogleAdsService
from app.services.mcp_client import MCPGatewayClient

logger = structlog.get_logger(__name__)


def month_date_range(month: int, year: int) -> DateRange:
    """Get DateRange for a full calendar month."""
    _, last_day = monthrange(year, month)
    return DateRange(
        start_date=f"{year}-{month:02d}-01",
        end_date=f"{year}-{month:02d}-{last_day:02d}",
    )


def prior_month_date_range(month: int, year: int) -> DateRange:
    """Get DateRange for the month prior to the given month."""
    if month == 1:
        return month_date_range(12, year - 1)
    return month_date_range(month - 1, year)


def week_date_range(week_of: str) -> DateRange:
    """Get DateRange for the week starting on the given date (Mon-Sun)."""
    d = date.fromisoformat(week_of)
    # Find the Monday of that week
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return DateRange(
        start_date=monday.isoformat(),
        end_date=sunday.isoformat(),
    )


def prior_week_date_range(week_of: str) -> DateRange:
    """Get DateRange for the week before the given date."""
    d = date.fromisoformat(week_of)
    monday = d - timedelta(days=d.weekday())
    prior_monday = monday - timedelta(days=7)
    prior_sunday = prior_monday + timedelta(days=6)
    return DateRange(
        start_date=prior_monday.isoformat(),
        end_date=prior_sunday.isoformat(),
    )


def _pct_change(current: float, prior: float) -> float:
    """Calculate percentage change."""
    if prior == 0:
        return 0.0
    return round((current - prior) / prior * 100, 1)


class ReportDataCollector:
    """Collects and aggregates performance data across platforms for reports."""

    def __init__(
        self,
        google_ads_service: Optional[GoogleAdsService] = None,
        mcp_client: Optional[MCPGatewayClient] = None,
    ):
        self.google_ads = google_ads_service
        self.mcp_client = mcp_client

    async def collect_monthly_data(
        self, month: int, year: int
    ) -> Dict[str, Any]:
        """Collect all data needed for a monthly performance review."""
        current_range = month_date_range(month, year)
        prior_range = prior_month_date_range(month, year)

        data: Dict[str, Any] = {
            "month": month,
            "year": year,
            "date_range": {"start": current_range.start_date, "end": current_range.end_date},
            "meta": None,
            "google": None,
            "aggregated": None,
        }

        # Fetch Meta data
        meta_current = await self._fetch_meta_overview(current_range)
        meta_prior = await self._fetch_meta_overview(prior_range)
        if meta_current:
            data["meta"] = self._build_platform_data(meta_current, meta_prior, "Meta")

        # Fetch Google data
        google_current = await self._fetch_google_overview(current_range)
        google_prior = await self._fetch_google_overview(prior_range)
        if google_current:
            data["google"] = self._build_platform_data(google_current, google_prior, "Google")

        # Fetch Google campaigns
        google_campaigns = await self._fetch_google_campaigns(current_range)
        if google_campaigns and data["google"]:
            data["google"]["campaigns"] = google_campaigns

        # Fetch Meta campaigns
        meta_campaigns = await self._fetch_meta_campaigns(current_range)
        if meta_campaigns and data["meta"]:
            data["meta"]["campaigns"] = meta_campaigns

        # Aggregate across platforms
        data["aggregated"] = self._aggregate_platforms(data)

        return data

    async def collect_weekly_data(self, week_of: str) -> Dict[str, Any]:
        """Collect all data needed for a weekly agenda/email."""
        current_range = week_date_range(week_of)
        prior_range = prior_week_date_range(week_of)

        data: Dict[str, Any] = {
            "week_of": week_of,
            "date_range": {"start": current_range.start_date, "end": current_range.end_date},
            "meta": None,
            "google": None,
            "aggregated": None,
        }

        meta_current = await self._fetch_meta_overview(current_range)
        meta_prior = await self._fetch_meta_overview(prior_range)
        if meta_current:
            data["meta"] = self._build_platform_data(meta_current, meta_prior, "Meta")

        google_current = await self._fetch_google_overview(current_range)
        google_prior = await self._fetch_google_overview(prior_range)
        if google_current:
            data["google"] = self._build_platform_data(google_current, google_prior, "Google")

        data["aggregated"] = self._aggregate_platforms(data)
        return data

    def _build_platform_data(
        self,
        current: Dict[str, Any],
        prior: Optional[Dict[str, Any]],
        platform: str,
    ) -> Dict[str, Any]:
        """Build structured platform data with period-over-period changes."""
        p = prior or {}
        return {
            "platform": platform,
            "spend": current.get("spend", 0),
            "spend_change": _pct_change(current.get("spend", 0), p.get("spend", 0)),
            "impressions": current.get("impressions", 0),
            "clicks": current.get("clicks", 0),
            "ctr": current.get("ctr", 0),
            "cpc": current.get("cpc", 0),
            "leads": current.get("leads", 0),
            "leads_change": _pct_change(current.get("leads", 0), p.get("leads", 0)),
            "cost_per_lead": current.get("cost_per_lead", 0),
            "cpl_change": _pct_change(current.get("cost_per_lead", 0), p.get("cost_per_lead", 0)),
            "opportunities": current.get("opportunities", 0),
            "opportunities_change": _pct_change(
                current.get("opportunities", 0), p.get("opportunities", 0)
            ),
            "cost_per_opportunity": current.get("cost_per_opportunity", 0),
            "cpo_change": _pct_change(
                current.get("cost_per_opportunity", 0), p.get("cost_per_opportunity", 0)
            ),
            # Meta-specific segmented CPL
            "remarketing_cpl": current.get("remarketing_cpl", 0),
            "remarketing_leads": current.get("remarketing_leads", 0),
            "prospecting_cpl": current.get("prospecting_cpl", 0),
            "prospecting_leads": current.get("prospecting_leads", 0),
            "campaigns": [],
        }

    def _aggregate_platforms(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate metrics across all platforms."""
        total_spend = 0.0
        total_leads = 0
        total_opps = 0

        for key in ("meta", "google"):
            plat = data.get(key)
            if plat:
                total_spend += plat.get("spend", 0)
                total_leads += plat.get("leads", 0)
                total_opps += plat.get("opportunities", 0)

        return {
            "total_spend": round(total_spend, 2),
            "total_leads": total_leads,
            "blended_cpl": round(total_spend / total_leads, 2) if total_leads else 0,
            "total_opportunities": total_opps,
            "blended_cpo": round(total_spend / total_opps, 2) if total_opps else 0,
        }

    # ── Data fetching helpers ─────────────────────────────────────

    async def _fetch_meta_overview(self, date_range: DateRange) -> Optional[Dict[str, Any]]:
        """Fetch Meta overview via MCP gateway."""
        if not self.mcp_client or not self.mcp_client.is_configured:
            return None
        try:
            raw = await self.mcp_client.call_tool(
                "meta_account_insights",
                {
                    "startDate": date_range.start_date,
                    "endDate": date_range.end_date,
                },
            )
            if isinstance(raw, dict) and raw.get("data"):
                row = raw["data"][0] if isinstance(raw["data"], list) else raw["data"]
                spend = float(row.get("spend", 0))
                clicks = int(row.get("clicks", 0))
                impressions = int(row.get("impressions", 0))
                actions = row.get("actions", [])
                leads = 0
                for a in (actions or []):
                    if a.get("action_type") == "lead":
                        leads = int(float(a.get("value", 0)))
                return {
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
                    "cpc": round(spend / clicks, 2) if clicks else 0,
                    "leads": leads,
                    "cost_per_lead": round(spend / leads, 2) if leads else 0,
                    "opportunities": 0,
                    "cost_per_opportunity": 0,
                }
            return None
        except Exception as e:
            logger.warning("meta_overview_fetch_error", error=str(e))
            return None

    async def _fetch_google_overview(self, date_range: DateRange) -> Optional[Dict[str, Any]]:
        """Fetch Google overview."""
        if not self.google_ads:
            return None
        try:
            from app.services.google_ads_api import SCHUMACHER_GOOGLE_CUSTOMER_ID
            result = await self.google_ads.get_account_performance(
                SCHUMACHER_GOOGLE_CUSTOMER_ID, date_range
            )
            if result.get("success"):
                return result
            return None
        except Exception as e:
            logger.warning("google_overview_fetch_error", error=str(e))
            return None

    async def _fetch_google_campaigns(self, date_range: DateRange) -> list:
        """Fetch Google campaign data."""
        if not self.google_ads:
            return []
        try:
            from app.services.google_ads_api import SCHUMACHER_GOOGLE_CUSTOMER_ID
            result = await self.google_ads.get_campaign_performance(
                SCHUMACHER_GOOGLE_CUSTOMER_ID, date_range
            )
            if result.get("success"):
                return result.get("campaigns", [])
            return []
        except Exception as e:
            logger.warning("google_campaigns_fetch_error", error=str(e))
            return []

    async def _fetch_meta_campaigns(self, date_range: DateRange) -> list:
        """Fetch Meta campaign data via MCP gateway."""
        if not self.mcp_client or not self.mcp_client.is_configured:
            return []
        try:
            raw = await self.mcp_client.call_tool(
                "meta_campaign_report",
                {
                    "startDate": date_range.start_date,
                    "endDate": date_range.end_date,
                    "limit": 20,
                },
            )
            if isinstance(raw, dict) and raw.get("data"):
                campaigns = []
                for row in raw["data"]:
                    spend = float(row.get("spend", 0))
                    clicks = int(row.get("clicks", 0))
                    impressions = int(row.get("impressions", 0))
                    campaigns.append({
                        "name": row.get("campaign_name", ""),
                        "status": row.get("status", ""),
                        "spend": spend,
                        "impressions": impressions,
                        "clicks": clicks,
                        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
                        "cpc": round(spend / clicks, 2) if clicks else 0,
                    })
                return sorted(campaigns, key=lambda x: x["spend"], reverse=True)
            return []
        except Exception as e:
            logger.warning("meta_campaigns_fetch_error", error=str(e))
            return []
