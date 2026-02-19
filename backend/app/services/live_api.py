"""
Live API Service for fetching real-time data from ad platforms.

This service makes HTTP requests to fetch live performance data
with custom date ranges from Meta, Google Ads, and LinkedIn.
"""

import asyncio
import os
import httpx
import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Meta Graph API base URL
META_API_BASE = "https://graph.facebook.com/v21.0"

# Known account IDs
ACCOUNT_IDS = {
    "schumacher": "act_142003632",
    "schumacher_homes": "act_142003632",
    "cheddar_up": "act_29125558",
    "upkeep": "act_143371293",
    "bierman": "act_104107839747101",
    "nextiva": "act_286048099",
    "helium10": "act_105487233155545",
    "learning_az": "act_109596339489054",
    "smartling": "act_2419341138098567",
}


@dataclass
class DateRange:
    """Represents a date range for API queries."""
    start_date: str  # YYYY-MM-DD format
    end_date: str    # YYYY-MM-DD format

    def to_meta_time_range(self) -> Dict[str, str]:
        """Convert to Meta API time_range format."""
        return {
            "since": self.start_date,
            "until": self.end_date
        }

    @classmethod
    def last_n_days(cls, n: int) -> "DateRange":
        """Create a date range for the last N days."""
        end = datetime.now()
        start = end - timedelta(days=n)
        return cls(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d")
        )

    @classmethod
    def this_month(cls) -> "DateRange":
        """Create a date range for this month to date."""
        now = datetime.now()
        start = now.replace(day=1)
        return cls(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=now.strftime("%Y-%m-%d")
        )

    @classmethod
    def last_month(cls) -> "DateRange":
        """Create a date range for last month."""
        now = datetime.now()
        first_of_this_month = now.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_of_prev_month.replace(day=1)
        return cls(
            start_date=first_of_prev_month.strftime("%Y-%m-%d"),
            end_date=last_of_prev_month.strftime("%Y-%m-%d")
        )

    @classmethod
    def year_to_date(cls) -> "DateRange":
        """Create a date range for year to date."""
        now = datetime.now()
        start = now.replace(month=1, day=1)
        return cls(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=now.strftime("%Y-%m-%d")
        )

    def get_comparison_period(self) -> "DateRange":
        """Get the comparison period of same duration, immediately before this range."""
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        duration = (end - start).days
        comp_end = start - timedelta(days=1)
        comp_start = comp_end - timedelta(days=duration)
        return DateRange(
            start_date=comp_start.strftime("%Y-%m-%d"),
            end_date=comp_end.strftime("%Y-%m-%d")
        )

    def get_prior_month_equivalent(self) -> "DateRange":
        """Shift this date range back by one calendar month for apples-to-apples comparison.

        Examples:
          Feb 1-5   → Jan 1-5
          Jan 15-31 → Dec 15-31
          Mar 1-31  → Feb 1-28 (clamped to month length)
        """
        from calendar import monthrange

        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")

        # Shift start back one month
        if start.month == 1:
            prev_start = start.replace(year=start.year - 1, month=12)
        else:
            # Clamp day to max days in prior month
            _, max_day = monthrange(start.year, start.month - 1)
            prev_start = start.replace(month=start.month - 1, day=min(start.day, max_day))

        # Shift end back one month
        if end.month == 1:
            prev_end = end.replace(year=end.year - 1, month=12)
        else:
            _, max_day = monthrange(end.year, end.month - 1)
            prev_end = end.replace(month=end.month - 1, day=min(end.day, max_day))

        return DateRange(
            start_date=prev_start.strftime("%Y-%m-%d"),
            end_date=prev_end.strftime("%Y-%m-%d")
        )

    @staticmethod
    def get_last_month_range() -> "DateRange":
        """Get the full previous calendar month as a DateRange."""
        from calendar import monthrange
        now = datetime.now()
        first_of_this_month = now.replace(day=1)
        last_of_prev = first_of_this_month - timedelta(days=1)
        first_of_prev = last_of_prev.replace(day=1)
        return DateRange(
            start_date=first_of_prev.strftime("%Y-%m-%d"),
            end_date=last_of_prev.strftime("%Y-%m-%d")
        )

    @property
    def duration_days(self) -> int:
        """Number of days in this range."""
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        return (end - start).days + 1


def parse_date_range_from_query(query: str) -> Optional[DateRange]:
    """
    Parse natural language date range from user query.
    Returns None only if absolutely no date intent is detected — callers should
    default to MTD in that case so Jarvis always uses live data, never stale cache.
    """
    import re
    query_lower = query.lower()

    # "today" / "right now" / "live"
    if any(w in query_lower for w in ["today", "right now", "live right now"]):
        from datetime import date
        today = date.today().isoformat()
        return DateRange(start_date=today, end_date=today)

    # Check for specific patterns
    if "last 7 days" in query_lower or "past 7 days" in query_lower or "past week" in query_lower:
        return DateRange.last_n_days(7)

    if "last 14 days" in query_lower or "past 14 days" in query_lower or "past two weeks" in query_lower:
        return DateRange.last_n_days(14)

    if "last 30 days" in query_lower or "past 30 days" in query_lower:
        return DateRange.last_n_days(30)

    if "last 60 days" in query_lower or "past 60 days" in query_lower:
        return DateRange.last_n_days(60)

    if "last 90 days" in query_lower or "past 90 days" in query_lower or "last quarter" in query_lower:
        return DateRange.last_n_days(90)

    if "mtd" in query_lower or "month to date" in query_lower or "this month" in query_lower:
        return DateRange.this_month()

    if "last month" in query_lower or "previous month" in query_lower:
        return DateRange.last_month()

    if "ytd" in query_lower or "year to date" in query_lower:
        return DateRange.year_to_date()

    # Check for "february" specifically (current month context)
    if "february" in query_lower and "2026" not in query_lower:
        return DateRange.this_month()

    # Check for specific month names with year
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }

    for month_name, month_num in months.items():
        if month_name in query_lower:
            # Try to find year
            year_match = re.search(r'20\d{2}', query)
            year = int(year_match.group()) if year_match else datetime.now().year

            # Create date range for that month
            from calendar import monthrange
            _, last_day = monthrange(year, month_num)

            # If it's the current month, only go to today
            now = datetime.now()
            if year == now.year and month_num == now.month:
                end_day = now.day
            else:
                end_day = last_day

            start = f"{year}-{month_num:02d}-01"
            end = f"{year}-{month_num:02d}-{end_day:02d}"
            return DateRange(start_date=start, end_date=end)

    # Default: return None (will use default date range)
    return None


def get_account_id_from_query(query: str) -> str:
    """
    Extract or identify account ID from query.
    Defaults to Schumacher if not specified.
    """
    query_lower = query.lower()

    for name, account_id in ACCOUNT_IDS.items():
        if name.replace("_", " ") in query_lower or name in query_lower:
            return account_id

    # Default to Schumacher
    return ACCOUNT_IDS["schumacher"]


class LiveAPIService:
    """Service for fetching live data from ad platform APIs."""

    def __init__(self, meta_access_token: Optional[str] = None):
        """Initialize with API credentials."""
        self.meta_token = meta_access_token or os.getenv("META_ACCESS_TOKEN")

    async def get_meta_account_insights(
        self,
        account_id: str,
        date_range: DateRange,
        level: str = "account"
    ) -> Dict[str, Any]:
        """
        Fetch insights from Meta Ads API for a specific date range.

        Args:
            account_id: Meta ad account ID (e.g., "act_142003632")
            date_range: DateRange object with start and end dates
            level: Breakdown level - "account", "campaign", "adset", or "ad"

        Returns:
            Dictionary with insights data
        """
        if not self.meta_token:
            logger.warning("no_meta_token", message="Meta access token not configured")
            return {"error": "Meta API token not configured"}

        # Build the API request
        fields = [
            "spend",
            "impressions",
            "clicks",
            "reach",
            "ctr",
            "cpc",
            "cpm",
            "actions",
            "cost_per_action_type",
        ]

        params = {
            "access_token": self.meta_token,
            "fields": ",".join(fields),
            "time_range": f'{{"since":"{date_range.start_date}","until":"{date_range.end_date}"}}',
        }

        if level == "campaign":
            params["level"] = "campaign"

        url = f"{META_API_BASE}/{account_id}/insights"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                logger.info(
                    "meta_api_success",
                    account_id=account_id,
                    date_range=f"{date_range.start_date} to {date_range.end_date}",
                    records=len(data.get("data", []))
                )

                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {
                        "start": date_range.start_date,
                        "end": date_range.end_date
                    },
                    "data": data.get("data", []),
                    "level": level
                }

        except httpx.HTTPStatusError as e:
            logger.error("meta_api_error", status=e.response.status_code, detail=str(e))
            return {
                "success": False,
                "error": f"API error: {e.response.status_code}",
                "detail": e.response.text
            }
        except Exception as e:
            logger.error("meta_api_exception", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def get_meta_campaigns(
        self,
        account_id: str,
        date_range: DateRange
    ) -> Dict[str, Any]:
        """
        Fetch campaign-level performance data for a specific date range.

        Only returns campaigns that had spend or impressions in the requested
        window — campaigns with zero activity are excluded so Jarvis never
        sees stale campaign names from prior periods.
        """
        if not self.meta_token:
            return {"error": "Meta API token not configured"}

        # Insights fields — actual performance for the date window
        insight_fields = [
            "campaign_id",
            "campaign_name",
            "spend",
            "impressions",
            "clicks",
            "reach",
            "ctr",
            "cpc",
            "cpm",
            "actions",
        ]

        # Also pull campaign-level metadata (status, budget) separately
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                # 1. Insights for the requested date range
                insights_resp = await client.get(
                    f"{META_API_BASE}/{account_id}/insights",
                    params={
                        "access_token": self.meta_token,
                        "fields": ",".join(insight_fields),
                        "time_range": f'{{"since":"{date_range.start_date}","until":"{date_range.end_date}"}}',
                        "level": "campaign",
                        "limit": 200,
                    }
                )
                insights_resp.raise_for_status()
                insights_data = insights_resp.json()
                campaigns_with_spend = insights_data.get("data", [])

                # 2. Campaign metadata (name, status, daily budget) — scoped to ACTIVE campaigns
                import json as _json
                meta_resp = await client.get(
                    f"{META_API_BASE}/{account_id}/campaigns",
                    params={
                        "access_token": self.meta_token,
                        "fields": "id,name,status,effective_status,daily_budget,lifetime_budget,objective",
                        "filtering": _json.dumps([{
                            "field": "effective_status",
                            "operator": "IN",
                            "value": ["ACTIVE", "PAUSED"],
                        }]),
                        "limit": 200,
                    }
                )
                meta_resp.raise_for_status()
                campaign_meta = {
                    c["id"]: c for c in meta_resp.json().get("data", [])
                }

                # Merge metadata into insights rows; filter out zero-spend rows
                enriched = []
                for row in campaigns_with_spend:
                    spend = float(row.get("spend", 0))
                    impressions = int(row.get("impressions", 0))
                    # Skip campaigns with zero activity in this window
                    if spend == 0 and impressions == 0:
                        continue

                    cid = row.get("campaign_id", "")
                    meta = campaign_meta.get(cid, {})
                    daily_budget = meta.get("daily_budget")
                    lifetime_budget = meta.get("lifetime_budget")
                    row["status"] = meta.get("effective_status", "UNKNOWN")
                    row["objective"] = meta.get("objective", "")
                    row["daily_budget"] = (
                        f"${float(daily_budget)/100:,.2f}" if daily_budget else None
                    )
                    row["lifetime_budget"] = (
                        f"${float(lifetime_budget)/100:,.2f}" if lifetime_budget else None
                    )
                    enriched.append(row)

                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {
                        "start": date_range.start_date,
                        "end": date_range.end_date
                    },
                    "campaigns": enriched,
                }

            except Exception as e:
                logger.error("meta_campaigns_error", error=str(e))
                return {"success": False, "error": str(e)}

    async def get_meta_active_ads_count(
        self,
        account_id: str,
    ) -> Dict[str, Any]:
        """
        Count ads that are ACTIVE and delivered at least one impression today.

        Uses today-only insights (since=today, until=today) so the count always
        reflects what is live right now — not a rolling window that could include
        ads that stopped delivering days ago.
        """
        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        import json as _json
        from datetime import date

        today = date.today().isoformat()

        active_filter = _json.dumps([{
            "field": "effective_status",
            "operator": "IN",
            "value": ["ACTIVE"],
        }])

        url = f"{META_API_BASE}/{account_id}/ads"
        params = {
            "access_token": self.meta_token,
            "fields": (
                "id,"
                f"insights.time_range({{'since':'{today}','until':'{today}'}})"
                "{impressions}"
            ),
            "filtering": active_filter,
            "limit": 500,
        }

        try:
            delivering_count = 0
            async with httpx.AsyncClient(timeout=60.0) as client:
                while url:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    for ad in data.get("data", []):
                        rows = ad.get("insights", {}).get("data", [])
                        impressions = int(rows[0].get("impressions", 0)) if rows else 0
                        if impressions > 0:
                            delivering_count += 1

                    next_url = data.get("paging", {}).get("next")
                    if next_url:
                        url = next_url
                        params = {}
                    else:
                        url = None

            logger.info("meta_active_ads_count", account_id=account_id, count=delivering_count)
            return {
                "success": True,
                "active_ads": delivering_count,
            }

        except Exception as e:
            logger.error("meta_active_ads_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def get_meta_active_ads_tree(
        self,
        account_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch the hierarchy of actively-delivering campaigns → ad sets → ads.

        Two-stage filter:
          1. effective_status=ACTIVE — Meta's guarantee that ad + adset + campaign are all on.
          2. Delivery check — fetch 7-day impressions per ad and exclude any ad with 0 impressions.
             This removes phantom-active ads (past-event open houses, exhausted budgets, etc.)
             that Meta leaves in ACTIVE status indefinitely even when they stopped delivering.

        Tree is built bottom-up: adsets/campaigns only appear if they have ≥1 delivering ad.
        """
        import json as _json
        from datetime import date

        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        active_filter = _json.dumps([{
            "field": "effective_status",
            "operator": "IN",
            "value": ["ACTIVE"],
        }])

        # Today-only delivery window — shows exactly what is live right now
        today = date.today().isoformat()

        async def paginate(client: httpx.AsyncClient, url: str, params: dict) -> List[dict]:
            results = []
            while url:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
                params = {}  # next URL already contains all params
            return results

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 1. Fetch active campaigns
                campaigns_raw = await paginate(client, f"{META_API_BASE}/{account_id}/campaigns", {
                    "access_token": self.meta_token,
                    "fields": "id,name,status,effective_status",
                    "filtering": active_filter,
                    "limit": 100,
                })

                # 2. Fetch all active ad sets
                adsets_raw = await paginate(client, f"{META_API_BASE}/{account_id}/adsets", {
                    "access_token": self.meta_token,
                    "fields": "id,name,status,effective_status,campaign_id",
                    "filtering": active_filter,
                    "limit": 200,
                })

                # 3. Fetch all active ads WITH today's impressions inline for delivery check
                ads_raw = await paginate(client, f"{META_API_BASE}/{account_id}/ads", {
                    "access_token": self.meta_token,
                    "fields": (
                        "id,name,status,effective_status,adset_id,campaign_id,"
                        f"insights.time_range({{'since':'{today}','until':'{today}'}})"
                        "{impressions}"
                    ),
                    "filtering": active_filter,
                    "limit": 500,
                })

            # Build a set of ad IDs that had ≥1 impression in the last 7 days
            delivering_ad_ids: set = set()
            for ad in ads_raw:
                rows = ad.get("insights", {}).get("data", [])
                impressions = int(rows[0].get("impressions", 0)) if rows else 0
                if impressions > 0:
                    delivering_ad_ids.add(ad["id"])

            logger.info(
                "meta_active_ads_delivery_filter",
                total_active=len(ads_raw),
                delivering_today=len(delivering_ad_ids),
                phantom=len(ads_raw) - len(delivering_ad_ids),
            )

            # Index adsets by campaign
            adsets_by_campaign: Dict[str, List[dict]] = {}
            for adset in adsets_raw:
                cid = adset.get("campaign_id", "")
                adsets_by_campaign.setdefault(cid, []).append(adset)

            # Index delivering ads by adset (exclude phantom-active ads)
            ads_by_adset: Dict[str, List[dict]] = {}
            for ad in ads_raw:
                if ad["id"] not in delivering_ad_ids:
                    continue  # skip phantom-active / non-delivering ads
                asid = ad.get("adset_id", "")
                ads_by_adset.setdefault(asid, []).append(ad)

            # Build tree bottom-up: only include adsets/campaigns with ≥1 delivering ad
            tree = []
            for campaign in campaigns_raw:
                cid = campaign["id"]
                adsets = adsets_by_campaign.get(cid, [])
                adset_nodes = []
                for adset in adsets:
                    asid = adset["id"]
                    ads = ads_by_adset.get(asid, [])
                    if not ads:
                        continue
                    adset_nodes.append({
                        "id": asid,
                        "name": adset.get("name", ""),
                        "status": adset.get("effective_status", adset.get("status", "")),
                        "ad_count": len(ads),
                        "ads": [
                            {
                                "id": ad["id"],
                                "name": ad.get("name", ""),
                                "status": ad.get("effective_status", ad.get("status", "")),
                            }
                            for ad in ads
                        ],
                    })
                total_ads = sum(n["ad_count"] for n in adset_nodes)
                if total_ads == 0:
                    continue
                tree.append({
                    "id": cid,
                    "name": campaign.get("name", ""),
                    "status": campaign.get("effective_status", campaign.get("status", "")),
                    "adset_count": len(adset_nodes),
                    "ad_count": total_ads,
                    "adsets": adset_nodes,
                })

            total_active_ads = sum(c["ad_count"] for c in tree)
            logger.info("meta_active_ads_tree", account_id=account_id, campaigns=len(tree), total_ads=total_active_ads)
            return {
                "success": True,
                "total_active_ads": total_active_ads,
                "campaigns": tree,
            }

        except Exception as e:
            logger.error("meta_active_ads_tree_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def get_meta_daily_insights(
        self,
        account_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """Fetch daily-level insights for trend chart data."""
        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        fields = [
            "spend",
            "impressions",
            "clicks",
            "ctr",
            "cpc",
            "cpm",
            "actions",
        ]

        params = {
            "access_token": self.meta_token,
            "fields": ",".join(fields),
            "time_range": f'{{"since":"{date_range.start_date}","until":"{date_range.end_date}"}}',
            "time_increment": "1",
            "limit": 400,
        }

        url = f"{META_API_BASE}/{account_id}/insights"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "data": data.get("data", []),
                }

        except Exception as e:
            logger.error("meta_daily_insights_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def get_insights_with_comparison(
        self,
        account_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """Fetch insights for current and comparison periods in parallel."""
        comparison_range = date_range.get_comparison_period()

        current, previous = await asyncio.gather(
            self.get_meta_account_insights(account_id, date_range),
            self.get_meta_account_insights(account_id, comparison_range),
        )

        return {
            "current": current,
            "previous": previous,
            "date_range": {
                "start": date_range.start_date,
                "end": date_range.end_date,
            },
            "comparison_range": {
                "start": comparison_range.start_date,
                "end": comparison_range.end_date,
            },
        }

    def format_insights_for_context(self, insights: Dict[str, Any]) -> str:
        """
        Format API insights data as readable context for the AI.
        """
        if not insights.get("success"):
            return f"API Error: {insights.get('error', 'Unknown error')}"

        lines = [
            "=== LIVE API DATA ===",
            f"Account: {insights.get('account_id')}",
            f"Date Range: {insights['date_range']['start']} to {insights['date_range']['end']}",
            ""
        ]

        data = insights.get("data", [])
        if not data:
            lines.append("No data available for this date range.")
            return "\n".join(lines)

        for record in data:
            spend = float(record.get("spend", 0))
            impressions = int(record.get("impressions", 0))
            clicks = int(record.get("clicks", 0))
            reach = int(record.get("reach", 0))
            ctr = float(record.get("ctr", 0))
            cpc = float(record.get("cpc", 0))
            cpm = float(record.get("cpm", 0))

            # Extract leads from actions
            leads = 0
            actions = record.get("actions", [])
            for action in actions:
                if action.get("action_type") == "lead":
                    leads = int(action.get("value", 0))
                    break

            cpl = spend / leads if leads > 0 else 0

            lines.extend([
                "### Account Performance Summary",
                f"- **Spend**: ${spend:,.2f}",
                f"- **Impressions**: {impressions:,}",
                f"- **Clicks**: {clicks:,}",
                f"- **Reach**: {reach:,}",
                f"- **CTR**: {ctr:.2f}%",
                f"- **CPC**: ${cpc:.2f}",
                f"- **CPM**: ${cpm:.2f}",
                f"- **Leads**: {leads:,}",
                f"- **Cost Per Lead**: ${cpl:.2f}",
            ])

        return "\n".join(lines)

    def format_campaigns_for_context(self, campaign_data: Dict[str, Any]) -> str:
        """
        Format campaign data as readable context for the AI.

        IMPORTANT: Only campaigns that had spend or impressions in the requested
        date window are included. Zero-activity campaigns are filtered out at the
        API layer so Jarvis never sees stale campaign names from past periods.
        """
        if not campaign_data.get("success"):
            return f"API Error: {campaign_data.get('error', 'Unknown error')}"

        date_start = campaign_data["date_range"]["start"]
        date_end = campaign_data["date_range"]["end"]

        lines = [
            "=== LIVE CAMPAIGN DATA ===",
            f"Account: {campaign_data.get('account_id')}",
            f"Date Range: {date_start} to {date_end}",
            "⚠️  Only campaigns with spend or impressions in this exact window are shown.",
            "    Campaigns not listed had zero activity in this period.",
            ""
        ]

        campaigns = campaign_data.get("campaigns", [])
        if not campaigns:
            lines.append("No campaigns had spend or impressions in this date range.")
            return "\n".join(lines)

        # Sort by spend descending
        campaigns_sorted = sorted(
            campaigns, key=lambda c: float(c.get("spend", 0)), reverse=True
        )

        lines.append(f"### Campaigns with activity in window ({len(campaigns_sorted)} total)")
        lines.append("")

        for camp in campaigns_sorted:
            name = camp.get("campaign_name", "Unknown")
            spend = float(camp.get("spend", 0))
            impressions = int(camp.get("impressions", 0))
            clicks = int(camp.get("clicks", 0))
            ctr = float(camp.get("ctr", 0))
            cpc = float(camp.get("cpc", 0))
            status = camp.get("status", "")
            daily_budget = camp.get("daily_budget")
            lifetime_budget = camp.get("lifetime_budget")
            objective = camp.get("objective", "")

            # Extract leads
            leads = 0
            for action in camp.get("actions", []):
                if action.get("action_type") == "lead":
                    leads = int(action.get("value", 0))
                    break

            cpl = spend / leads if leads > 0 else 0

            budget_str = ""
            if daily_budget:
                budget_str = f" | Daily budget: {daily_budget}"
            elif lifetime_budget:
                budget_str = f" | Lifetime budget: {lifetime_budget}"

            lines.extend([
                f"**{name}**",
                f"  - Status: {status}{' | Objective: ' + objective if objective else ''}",
                f"  - Spend ({date_start}–{date_end}): ${spend:,.2f}{budget_str}",
                f"  - Impressions: {impressions:,} | Clicks: {clicks:,} | CTR: {ctr:.2f}% | CPC: ${cpc:.2f}",
                f"  - Leads: {leads}" + (f" | CPL: ${cpl:.2f}" if leads > 0 else " | CPL: N/A"),
                ""
            ])

        return "\n".join(lines)

    async def get_meta_ads_by_date_range(
        self,
        account_id: str,
        date_range: DateRange,
        search_terms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch ad-level performance data for a specific date range.

        Pulls every ad that had spend or impressions in the window, enriched
        with campaign name and ad set name. Optionally filters to ads whose
        name contains any of the search_terms (case-insensitive) so Jarvis
        can look up specific creatives by name fragment.

        Args:
            account_id: Meta ad account ID.
            date_range: Date window to pull metrics for.
            search_terms: Optional list of name fragments to filter ads by.
                          If None/empty, returns ALL ads with activity.
        """
        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        import json as _json

        since = date_range.start_date
        until = date_range.end_date

        async def paginate(client: httpx.AsyncClient, url: str, params: dict) -> List[dict]:
            results = []
            while url:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
                params = {}
            return results

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                # Fetch ad-level insights for the date window
                ads_insights = await paginate(client, f"{META_API_BASE}/{account_id}/insights", {
                    "access_token": self.meta_token,
                    "level": "ad",
                    "fields": (
                        "ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,"
                        "spend,impressions,clicks,reach,ctr,cpc,cpm,actions"
                    ),
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "limit": 500,
                })

                # Filter out zero-activity rows
                active_ads = [
                    a for a in ads_insights
                    if float(a.get("spend", 0)) > 0 or int(a.get("impressions", 0)) > 0
                ]

                # If search terms provided, filter to matching ad names
                if search_terms:
                    terms_lower = [t.lower() for t in search_terms]
                    active_ads = [
                        a for a in active_ads
                        if any(term in a.get("ad_name", "").lower() for term in terms_lower)
                    ]

                # Build enriched ad records
                enriched = []
                for a in active_ads:
                    spend = float(a.get("spend", 0))
                    impressions = int(a.get("impressions", 0))
                    clicks = int(a.get("clicks", 0))
                    ctr = float(a.get("ctr", 0))
                    cpc = float(a.get("cpc", 0))
                    cpm = float(a.get("cpm", 0))

                    leads = 0
                    for action in a.get("actions", []):
                        if action.get("action_type") == "lead":
                            leads = int(action.get("value", 0))
                            break

                    cpl = round(spend / leads, 2) if leads > 0 else None

                    campaign_name = a.get("campaign_name", "Unknown Campaign")
                    traffic_keywords = ["open house", "visit", "visits"]
                    is_traffic = any(kw in campaign_name.lower() for kw in traffic_keywords)

                    enriched.append({
                        "ad_id": a.get("ad_id", ""),
                        "ad_name": a.get("ad_name", ""),
                        "adset_id": a.get("adset_id", ""),
                        "adset_name": a.get("adset_name", ""),
                        "campaign_id": a.get("campaign_id", ""),
                        "campaign_name": campaign_name,
                        "is_traffic_campaign": is_traffic,
                        "spend": round(spend, 2),
                        "impressions": impressions,
                        "clicks": clicks,
                        "ctr": round(ctr, 2),
                        "cpc": round(cpc, 2),
                        "cpm": round(cpm, 2),
                        "leads": leads,
                        "cpl": cpl,
                    })

                # Sort by spend descending
                enriched.sort(key=lambda x: x["spend"], reverse=True)

                logger.info(
                    "meta_ads_by_date_range",
                    account_id=account_id,
                    date_range=f"{since} to {until}",
                    total_ads=len(enriched),
                    search_terms=search_terms,
                )

                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {"start": since, "end": until},
                    "search_terms": search_terms or [],
                    "total_ads": len(enriched),
                    "ads": enriched,
                }

        except Exception as e:
            logger.error("meta_ads_by_date_range_error", error=str(e))
            return {"success": False, "error": str(e)}

    def format_ads_for_context(self, data: Dict[str, Any]) -> str:
        """
        Format ad-level data as readable context for Jarvis.

        Structure:
          1. CREATIVE ROLLUP — one row per unique ad name showing totals across
             ALL campaigns/adsets it lives in, plus how many instances exist.
             This lets Jarvis immediately see if a creative is duplicated and
             compare its aggregate performance.
          2. FULL BREAKDOWN — Campaign → Ad Set → individual ad instances with
             full metrics, so Jarvis can see exactly where each copy lives and
             compare performance across placements.
        """
        if not data.get("success"):
            return f"Ad-level data unavailable: {data.get('error', 'Unknown error')}"

        ads = data.get("ads", [])
        date_start = data["date_range"]["start"]
        date_end = data["date_range"]["end"]
        search_terms = data.get("search_terms", [])

        header = "=== AD-LEVEL PERFORMANCE DATA ==="
        if search_terms:
            header += f"\nFiltered to ads matching: {', '.join(search_terms)}"
        lines = [
            header,
            f"Date Range: {date_start} to {date_end}",
            f"Total ad instances with activity: {len(ads)}",
            "⚠️  Same ad name appearing in multiple campaigns = separate instances (duplicates).",
            "    Each instance has independent spend/leads. Totals below aggregate all instances.",
            "",
        ]

        if not ads:
            lines.append("No ads matched the search criteria in this date range.")
            return "\n".join(lines)

        # ── SECTION 1: Creative rollup (aggregate by ad name across all placements) ──
        by_ad_name: Dict[str, List[dict]] = {}
        for ad in ads:
            by_ad_name.setdefault(ad["ad_name"], []).append(ad)

        lines.append("─" * 60)
        lines.append("SECTION 1 — CREATIVE ROLLUP (all instances combined)")
        lines.append("─" * 60)
        lines.append(
            f"{'Ad Name':<45} {'Instances':>9} {'Spend':>10} {'Leads':>6} {'CPL':>8} {'Impr':>10}"
        )
        lines.append("-" * 95)

        # Sort rollup by total spend desc
        rollup_sorted = sorted(
            by_ad_name.items(),
            key=lambda kv: sum(a["spend"] for a in kv[1]),
            reverse=True,
        )
        for ad_name, instances in rollup_sorted:
            total_spend = sum(a["spend"] for a in instances)
            total_leads = sum(a["leads"] for a in instances)
            total_impr = sum(a["impressions"] for a in instances)
            total_cpl = round(total_spend / total_leads, 2) if total_leads > 0 else None
            cpl_str = f"${total_cpl:.2f}" if total_cpl else "N/A"
            instance_count = len(instances)
            duplicate_flag = " ⚠️ DUPE" if instance_count > 1 else ""

            # Truncate long ad names for table alignment
            name_display = (ad_name[:42] + "...") if len(ad_name) > 45 else ad_name
            lines.append(
                f"{name_display:<45} {instance_count:>9}{duplicate_flag}"
                f"  ${total_spend:>8,.2f}  {total_leads:>5}  {cpl_str:>8}  {total_impr:>9,}"
            )

            # Show which campaigns each instance lives in (indented)
            for inst in sorted(instances, key=lambda x: x["spend"], reverse=True):
                inst_cpl = f"${inst['cpl']:.2f}" if inst["cpl"] else "N/A"
                lines.append(
                    f"    ↳ [{inst['campaign_name']}] › [{inst['adset_name']}]"
                    f"  spend=${inst['spend']:,.2f}  leads={inst['leads']}  cpl={inst_cpl}"
                )
        lines.append("")

        # ── SECTION 2: Full breakdown Campaign → Ad Set → Ads ──
        lines.append("─" * 60)
        lines.append("SECTION 2 — FULL BREAKDOWN BY CAMPAIGN & AD SET")
        lines.append("─" * 60)

        # Group by campaign → adset, sort campaigns by total spend desc
        by_campaign: Dict[str, Dict[str, List[dict]]] = {}
        for ad in ads:
            cname = ad["campaign_name"]
            aname = ad["adset_name"]
            by_campaign.setdefault(cname, {}).setdefault(aname, []).append(ad)

        campaigns_by_spend = sorted(
            by_campaign.items(),
            key=lambda kv: sum(
                ad["spend"] for adsets in kv[1].values() for ad in adsets
            ),
            reverse=True,
        )

        for campaign_name, adsets in campaigns_by_spend:
            is_traffic = list(adsets.values())[0][0].get("is_traffic_campaign", False)
            camp_label = "🚗 TRAFFIC" if is_traffic else "📣 LEAD-GEN"
            camp_spend = sum(ad["spend"] for ads_list in adsets.values() for ad in ads_list)
            camp_leads = sum(ad["leads"] for ads_list in adsets.values() for ad in ads_list)
            camp_cpl = round(camp_spend / camp_leads, 2) if camp_leads > 0 else None
            cpl_str = f"${camp_cpl:.2f}" if camp_cpl else "N/A"

            lines.append(
                f"\n{camp_label} Campaign: {campaign_name}"
                f"\n  Campaign totals — Spend: ${camp_spend:,.2f} | Leads: {camp_leads} | CPL: {cpl_str}"
            )

            # Sort adsets by spend desc
            adsets_by_spend = sorted(
                adsets.items(),
                key=lambda kv: sum(a["spend"] for a in kv[1]),
                reverse=True,
            )
            for adset_name, adset_ads in adsets_by_spend:
                adset_spend = sum(a["spend"] for a in adset_ads)
                adset_leads = sum(a["leads"] for a in adset_ads)
                adset_cpl = round(adset_spend / adset_leads, 2) if adset_leads > 0 else None
                adset_cpl_str = f"${adset_cpl:.2f}" if adset_cpl else "N/A"

                lines.append(
                    f"  📂 Ad Set: {adset_name}"
                    f"  |  Spend: ${adset_spend:,.2f} | Leads: {adset_leads} | CPL: {adset_cpl_str}"
                )

                for ad in sorted(adset_ads, key=lambda x: x["spend"], reverse=True):
                    # Flag if this ad name appears in other campaigns too
                    instance_count = len(by_ad_name.get(ad["ad_name"], []))
                    dupe_note = f"  ← also in {instance_count - 1} other campaign(s)" if instance_count > 1 else ""

                    if is_traffic:
                        metric_str = (
                            f"Impr: {ad['impressions']:,} | CTR: {ad['ctr']:.2f}% "
                            f"| CPC: ${ad['cpc']:.2f} | CPM: ${ad['cpm']:.2f}"
                        )
                    else:
                        leads_str = (
                            f"Leads: {ad['leads']} | CPL: ${ad['cpl']:.2f}"
                            if ad["leads"] > 0 else "Leads: 0 | CPL: N/A"
                        )
                        metric_str = (
                            f"Impr: {ad['impressions']:,} | Clicks: {ad['clicks']:,} | {leads_str}"
                        )

                    lines.append(
                        f"    🎯 {ad['ad_name']}{dupe_note}\n"
                        f"       Spend: ${ad['spend']:,.2f} | {metric_str}"
                    )
                lines.append("")

        return "\n".join(lines)

    async def get_meta_recently_paused_ads(
        self,
        account_id: str,
        days_back: int = 1,
        max_ads: int = 150,
    ) -> Dict[str, Any]:
        """
        Fetch RECENTLY paused ads with their performance metrics.

        Fetches ads with effective_status=PAUSED, then filters client-side to
        only those whose updated_time (pause-date proxy) falls within the last
        `days_back` days. Default is 1 day (last 24 hours) so we only surface
        ads paused in the most recent session — not the entire account history.

        Capped at `max_ads` total (sorted by 30d spend desc) to stay within
        the 200k token limit for Claude.

        Args:
            account_id: Meta ad account ID.
            days_back: How far back to look for paused ads (default 1 day).
            max_ads: Hard cap on ads passed to the formatter (default 150).
        """
        import json as _json
        from datetime import date, timedelta, timezone

        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        today = date.today()
        since = (today - timedelta(days=days_back)).isoformat()
        until = today.isoformat()
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)

        paused_filter = _json.dumps([{
            "field": "effective_status",
            "operator": "IN",
            "value": ["PAUSED"],
        }])

        async def paginate(client: httpx.AsyncClient, url: str, params: dict) -> List[dict]:
            results = []
            while url:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
                params = {}
            return results

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                # Only fetch one page (500 ads max) sorted by updated_time desc
                # so the most recently paused ads come first — no need to paginate
                # through thousands of old paused ads.
                resp = await client.get(f"{META_API_BASE}/{account_id}/ads", params={
                    "access_token": self.meta_token,
                    "fields": (
                        "id,name,effective_status,adset_id,campaign_id,"
                        "created_time,updated_time,"
                        f"insights.time_range({{'since':'{since}','until':'{until}'}})"
                        "{spend,impressions,clicks,actions,ctr,cpc,cpm}"
                    ),
                    "filtering": paused_filter,
                    "sort": "updated_time_descending",
                    "limit": 500,
                })
                resp.raise_for_status()
                ads_raw = resp.json().get("data", [])

                # Fetch campaign and adset names (no status filter — include all)
                campaigns_raw, adsets_raw = await asyncio.gather(
                    paginate(client, f"{META_API_BASE}/{account_id}/campaigns", {
                        "access_token": self.meta_token,
                        "fields": "id,name",
                        "limit": 200,
                    }),
                    paginate(client, f"{META_API_BASE}/{account_id}/adsets", {
                        "access_token": self.meta_token,
                        "fields": "id,name,campaign_id",
                        "limit": 500,
                    }),
                )

            campaign_names = {c["id"]: c["name"] for c in campaigns_raw}
            adset_names = {a["id"]: a["name"] for a in adsets_raw}

            import re as _re

            def _parse_meta_datetime(raw: str) -> Optional[datetime]:
                """Parse Meta's datetime strings which may use ±HHMM or ±HH:MM offsets."""
                if not raw:
                    return None
                try:
                    # Normalise ±HHMM → ±HH:MM so fromisoformat() accepts it
                    normalised = _re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', raw)
                    return datetime.fromisoformat(normalised)
                except Exception:
                    return None

            enriched_ads = []
            skipped_old = 0
            for ad in ads_raw:
                # Parse updated_time and skip ads not updated in the window
                updated_raw = ad.get("updated_time", "")
                updated_dt = _parse_meta_datetime(updated_raw)
                paused_date = updated_dt.strftime("%Y-%m-%d") if updated_dt else None

                # Filter: only include ads updated within the window
                if updated_dt and updated_dt.astimezone(timezone.utc) < cutoff_dt:
                    skipped_old += 1
                    continue

                insights_rows = ad.get("insights", {}).get("data", [])
                row = insights_rows[0] if insights_rows else {}

                spend = float(row.get("spend", 0))
                impressions = int(row.get("impressions", 0))
                clicks = int(row.get("clicks", 0))
                ctr = float(row.get("ctr", 0))
                cpc = float(row.get("cpc", 0))
                cpm = float(row.get("cpm", 0))
                leads = 0
                for action in row.get("actions", []):
                    if action.get("action_type") == "lead":
                        leads = int(action.get("value", 0))
                        break
                cpl = round(spend / leads, 2) if leads > 0 else None

                # Days running (created → today)
                created_dt = _parse_meta_datetime(ad.get("created_time", ""))
                days_running = None
                if created_dt:
                    days_running = (datetime.now(created_dt.tzinfo) - created_dt).days

                campaign_id = ad.get("campaign_id", "")
                adset_id = ad.get("adset_id", "")
                campaign_name = campaign_names.get(campaign_id, "Unknown Campaign")

                traffic_keywords = ["open house", "visit", "visits"]
                is_traffic_campaign = any(kw in campaign_name.lower() for kw in traffic_keywords)

                enriched_ads.append({
                    "id": ad["id"],
                    "name": ad.get("name", ""),
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "adset_id": adset_id,
                    "adset_name": adset_names.get(adset_id, "Unknown Ad Set"),
                    "is_traffic_campaign": is_traffic_campaign,
                    "days_running": days_running,
                    "paused_date": paused_date,
                    "spend_30d": round(spend, 2),
                    "impressions_30d": impressions,
                    "clicks_30d": clicks,
                    "leads_30d": leads,
                    "ctr_30d": round(ctr, 2),
                    "cpc_30d": round(cpc, 2),
                    "cpm_30d": round(cpm, 2),
                    "cpl_30d": cpl,
                })

            # Sort by 30d spend desc, then hard-cap to max_ads
            enriched_ads.sort(key=lambda x: x["spend_30d"], reverse=True)
            total_recent = len(enriched_ads)
            truncated = total_recent > max_ads
            enriched_ads = enriched_ads[:max_ads]

            logger.info(
                "meta_recently_paused_ads",
                account_id=account_id,
                recent_ad_count=total_recent,
                skipped_old=skipped_old,
                returned=len(enriched_ads),
                truncated=truncated,
                date_range=f"{since} to {until}",
            )

            return {
                "success": True,
                "total_paused_ads": total_recent,
                "truncated": truncated,
                "max_ads": max_ads,
                "date_range": {"since": since, "until": until},
                "ads": enriched_ads,
            }

        except Exception as e:
            logger.error("meta_recently_paused_ads_error", error=str(e))
            return {"success": False, "error": str(e)}

    def format_paused_ads_for_context(self, data: Dict[str, Any]) -> str:
        """
        Format paused ads with performance context for Jarvis.

        Groups by campaign so Jarvis can reason about what was paused where
        and explain the performance rationale behind each pause.
        """
        if not data.get("success"):
            return f"Paused ads data unavailable: {data.get('error', 'Unknown error')}"

        ads = data.get("ads", [])
        total = data.get("total_paused_ads", len(ads))
        truncated = data.get("truncated", False)
        max_ads = data.get("max_ads", 150)
        since = data.get("date_range", {}).get("since", "")
        until = data.get("date_range", {}).get("until", "")

        # Count unique creative names vs total instances
        unique_names = len({a["name"] for a in ads})

        lines = [
            "=== RECENTLY PAUSED ADS (paused in the last 24 hours) ===",
            f"Ad instances paused: {total}" + (f" (showing top {max_ads} by 30d spend)" if truncated else "") +
            (f" | Unique creatives: {unique_names}" if unique_names != total else ""),
            f"Performance window: {since} to {until} (30 days)",
            "Note: Same creative name in multiple ad sets = separate instances counted individually.",
            "",
        ]

        if not ads:
            lines.append("No ads appear to have been paused in the last 24 hours.")
            lines.append("If you paused ads more than 24 hours ago, ask Jarvis to 'show paused ads from the last 7 days'.")
            return "\n".join(lines)

        # ── SECTION 1: Creative rollup — one row per unique ad name ─────────
        by_ad_name: Dict[str, List[dict]] = {}
        for ad in ads:
            by_ad_name.setdefault(ad["name"], []).append(ad)

        lines.append("─" * 60)
        lines.append("SECTION 1 — CREATIVE ROLLUP (unique ad names, all instances combined)")
        lines.append("─" * 60)
        lines.append(f"{'Ad Name':<45} {'Copies':>6} {'30d Spend':>10} {'Leads':>6} {'CPL':>8}")
        lines.append("-" * 80)

        rollup_sorted = sorted(
            by_ad_name.items(),
            key=lambda kv: sum(a["spend_30d"] for a in kv[1]),
            reverse=True,
        )
        for ad_name, instances in rollup_sorted:
            total_spend = sum(a["spend_30d"] for a in instances)
            total_leads = sum(a["leads_30d"] for a in instances)
            total_cpl = round(total_spend / total_leads, 2) if total_leads > 0 else None
            cpl_str = f"${total_cpl:.2f}" if total_cpl else "no leads"
            count = len(instances)
            dupe_flag = " ⚠️ x" + str(count) if count > 1 else ""

            name_display = (ad_name[:42] + "...") if len(ad_name) > 45 else ad_name
            lines.append(
                f"{name_display:<45} {str(count) + dupe_flag:>6}  ${total_spend:>8,.2f}  {total_leads:>5}  {cpl_str:>8}"
            )
        lines.append("")

        # ── SECTION 2: Full breakdown by campaign ────────────────────────────
        lines.append("─" * 60)
        lines.append("SECTION 2 — FULL BREAKDOWN BY CAMPAIGN")
        lines.append("─" * 60)

        by_campaign: Dict[str, List[dict]] = {}
        for ad in ads:
            by_campaign.setdefault(ad["campaign_name"], []).append(ad)

        campaigns_by_spend = sorted(
            by_campaign.items(),
            key=lambda kv: sum(a["spend_30d"] for a in kv[1]),
            reverse=True,
        )

        for campaign_name, camp_ads in campaigns_by_spend:
            is_traffic = camp_ads[0].get("is_traffic_campaign", False)
            camp_spend = sum(a["spend_30d"] for a in camp_ads)
            camp_leads = sum(a["leads_30d"] for a in camp_ads)
            camp_cpl = round(camp_spend / camp_leads, 2) if camp_leads > 0 else None
            cpl_str = f"${camp_cpl:.2f}" if camp_cpl else "no leads"

            camp_label = "🚗 TRAFFIC" if is_traffic else "📣 LEAD-GEN"
            summary = f"   {len(camp_ads)} paused | 30d spend: ${camp_spend:,.2f}"
            if not is_traffic:
                summary += f" | leads: {camp_leads} | CPL: {cpl_str}"

            lines.append(f"\n{camp_label}: {campaign_name}")
            lines.append(summary)

            for ad in sorted(camp_ads, key=lambda x: x["spend_30d"], reverse=True):
                dr = f"{ad['days_running']}d old" if ad["days_running"] is not None else "age unknown"
                paused_str = f" | paused ~{ad['paused_date']}" if ad["paused_date"] else ""
                spend_str = f"${ad['spend_30d']:,.2f}"
                # Flag if this same creative exists in other campaigns too
                instance_count = len(by_ad_name.get(ad["name"], []))
                dupe_note = f"  [also in {instance_count - 1} other ad set(s)]" if instance_count > 1 else ""

                lines.append(f"   • {ad['name'][:80]}{dupe_note}")
                lines.append(f"     Ad Set: {ad['adset_name'][:65]} | {dr}{paused_str}")

                if is_traffic:
                    impr = ad["impressions_30d"]
                    ctr = ad["ctr_30d"]
                    cpc_str = f"${ad['cpc_30d']:.2f}" if ad["cpc_30d"] > 0 else "$0.00"
                    lines.append(
                        f"     30d: spend={spend_str} | impr={impr:,} | CTR={ctr:.2f}% | CPC={cpc_str}"
                    )
                else:
                    cpl_ad_str = f"${ad['cpl_30d']:.2f}" if ad["cpl_30d"] is not None else "no leads"
                    lines.append(
                        f"     30d: spend={spend_str} | leads={ad['leads_30d']} | CPL={cpl_ad_str} | "
                        f"impr={ad['impressions_30d']:,} | CTR={ad['ctr_30d']:.2f}%"
                    )
            lines.append("")

        return "\n".join(lines)

    async def get_meta_active_ads_with_performance(
        self,
        account_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch all active ads with 30-day performance data and days-running context.

        Returns each active ad enriched with:
          - Campaign name and ad set name
          - 30-day spend, impressions, clicks, leads, CPL
          - Created date and days running (for learning phase awareness)
          - effective_status (always ACTIVE)

        Used by Jarvis to recommend which ads to pause to get below the 250 limit.
        """
        import json as _json
        from datetime import date, timedelta

        if not self.meta_token:
            return {"success": False, "error": "Meta API token not configured"}

        today = date.today()
        since = (today - timedelta(days=30)).isoformat()
        until = today.isoformat()

        active_filter = _json.dumps([{
            "field": "effective_status",
            "operator": "IN",
            "value": ["ACTIVE"],
        }])

        async def paginate(client: httpx.AsyncClient, url: str, params: dict) -> List[dict]:
            results = []
            while url:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
                params = {}
            return results

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                ads_raw = await paginate(client, f"{META_API_BASE}/{account_id}/ads", {
                    "access_token": self.meta_token,
                    "fields": (
                        "id,name,effective_status,adset_id,campaign_id,"
                        "created_time,"
                        f"insights.time_range({{'since':'{since}','until':'{until}'}})"
                        "{spend,impressions,clicks,actions,ctr,cpc}"
                    ),
                    "filtering": active_filter,
                    "limit": 500,
                })

                # Fetch campaign and adset names in parallel
                campaigns_raw = await paginate(client, f"{META_API_BASE}/{account_id}/campaigns", {
                    "access_token": self.meta_token,
                    "fields": "id,name",
                    "filtering": active_filter,
                    "limit": 100,
                })
                adsets_raw = await paginate(client, f"{META_API_BASE}/{account_id}/adsets", {
                    "access_token": self.meta_token,
                    "fields": "id,name,campaign_id",
                    "filtering": active_filter,
                    "limit": 200,
                })

            campaign_names = {c["id"]: c["name"] for c in campaigns_raw}
            adset_names = {a["id"]: a["name"] for a in adsets_raw}

            enriched_ads = []
            for ad in ads_raw:
                insights_rows = ad.get("insights", {}).get("data", [])
                row = insights_rows[0] if insights_rows else {}

                spend = float(row.get("spend", 0))
                impressions = int(row.get("impressions", 0))
                clicks = int(row.get("clicks", 0))
                ctr = float(row.get("ctr", 0))
                cpc = float(row.get("cpc", 0))
                leads = 0
                for action in row.get("actions", []):
                    if action.get("action_type") == "lead":
                        leads = int(action.get("value", 0))
                        break
                cpl = round(spend / leads, 2) if leads > 0 else None

                # Days running
                created_raw = ad.get("created_time", "")
                days_running = None
                if created_raw:
                    try:
                        created_dt = datetime.fromisoformat(created_raw.replace("+0000", "+00:00"))
                        days_running = (datetime.now(created_dt.tzinfo) - created_dt).days
                    except Exception:
                        pass

                campaign_id = ad.get("campaign_id", "")
                adset_id = ad.get("adset_id", "")
                campaign_name = campaign_names.get(campaign_id, "Unknown Campaign")

                # Traffic/engagement campaigns are judged on reach/CTR, not leads
                traffic_keywords = ["open house", "visit", "visits"]
                is_traffic_campaign = any(kw in campaign_name.lower() for kw in traffic_keywords)

                enriched_ads.append({
                    "id": ad["id"],
                    "name": ad.get("name", ""),
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "adset_id": adset_id,
                    "adset_name": adset_names.get(adset_id, "Unknown Ad Set"),
                    "is_traffic_campaign": is_traffic_campaign,
                    "days_running": days_running,
                    "spend_30d": round(spend, 2),
                    "impressions_30d": impressions,
                    "clicks_30d": clicks,
                    "leads_30d": leads,
                    "ctr_30d": round(ctr, 2),
                    "cpc_30d": round(cpc, 2),
                    "cpl_30d": cpl,
                })

            logger.info(
                "meta_active_ads_with_performance",
                account_id=account_id,
                ad_count=len(enriched_ads),
                date_range=f"{since} to {until}",
            )
            return {
                "success": True,
                "total_active_ads": len(enriched_ads),
                "threshold": 250,
                "over_by": max(0, len(enriched_ads) - 250),
                "date_range": {"since": since, "until": until},
                "ads": enriched_ads,
            }

        except Exception as e:
            logger.error("meta_active_ads_performance_error", error=str(e))
            return {"success": False, "error": str(e)}

    def format_active_ads_for_jarvis(self, data: Dict[str, Any]) -> str:
        """
        Format active ads performance data as concise Jarvis context.
        Groups by campaign so Jarvis can reason about pausing at the right level.
        """
        if not data.get("success"):
            return f"Active ads data unavailable: {data.get('error', 'Unknown error')}"

        ads = data.get("ads", [])
        total = data.get("total_active_ads", len(ads))
        threshold = data.get("threshold", 250)
        over_by = data.get("over_by", 0)
        since = data.get("date_range", {}).get("since", "")
        until = data.get("date_range", {}).get("until", "")

        lines = [
            "=== ACTIVE ADS PERFORMANCE (for pause recommendations) ===",
            f"Total active ads: {total} / {threshold} limit",
        ]
        if over_by > 0:
            lines.append(f"⚠️  Over limit by {over_by} ads — need to pause at least {over_by} to get back under {threshold}")
        lines += [f"Performance window: {since} to {until} (30 days)", ""]

        # Group by campaign
        by_campaign: Dict[str, List[dict]] = {}
        for ad in ads:
            cname = ad["campaign_name"]
            by_campaign.setdefault(cname, []).append(ad)

        for campaign_name, camp_ads in sorted(by_campaign.items()):
            is_traffic = camp_ads[0].get("is_traffic_campaign", False)
            camp_spend = sum(a["spend_30d"] for a in camp_ads)

            if is_traffic:
                # Traffic/engagement campaigns: evaluate on reach metrics, NOT leads/CPL
                camp_impressions = sum(a["impressions_30d"] for a in camp_ads)
                camp_clicks = sum(a["clicks_30d"] for a in camp_ads)
                camp_ctr = round((camp_clicks / camp_impressions) * 100, 2) if camp_impressions > 0 else 0
                camp_cpc = round(camp_spend / camp_clicks, 2) if camp_clicks > 0 else 0

                lines.append(f"🚗 TRAFFIC/ENGAGEMENT CAMPAIGN: {campaign_name}")
                lines.append(
                    f"   {len(camp_ads)} active ads | 30d spend: ${camp_spend:,.2f} | "
                    f"30d impressions: {camp_impressions:,} | 30d CTR: {camp_ctr:.2f}% | 30d CPC: ${camp_cpc:.2f}"
                )
                lines.append("   ⚠️  Judge these ads on impressions/CTR/CPC — NOT leads or CPL (traffic objective)")
            else:
                # Lead-gen campaigns: evaluate on leads and CPL
                camp_leads = sum(a["leads_30d"] for a in camp_ads)
                camp_cpl = round(camp_spend / camp_leads, 2) if camp_leads > 0 else None
                cpl_str = f"${camp_cpl:.2f}" if camp_cpl is not None else "no leads"

                lines.append(f"📣 Campaign: {campaign_name}")
                lines.append(
                    f"   {len(camp_ads)} active ads | 30d spend: ${camp_spend:,.2f} | "
                    f"30d leads: {camp_leads} | 30d CPL: {cpl_str}"
                )

            for ad in camp_ads:
                dr = f"{ad['days_running']}d running" if ad["days_running"] is not None else "unknown age"
                spend_str = f"${ad['spend_30d']:,.2f}"
                in_learning = ad["days_running"] is not None and ad["days_running"] < 14

                learning_flag = " 🎓 IN LEARNING (<14d)" if in_learning else ""
                lines.append(
                    f"   • [{dr}]{learning_flag} {ad['name'][:80]}"
                )

                if is_traffic:
                    # Show engagement metrics for traffic ads
                    impr = ad["impressions_30d"]
                    ctr = ad["ctr_30d"]
                    cpc_str = f"${ad['cpc_30d']:.2f}" if ad["cpc_30d"] > 0 else "$0.00"
                    lines.append(
                        f"     Ad Set: {ad['adset_name'][:60]} | spend: {spend_str} | "
                        f"impressions: {impr:,} | CTR: {ctr:.2f}% | CPC: {cpc_str}"
                    )
                else:
                    # Show lead-gen metrics
                    leads_str = str(ad["leads_30d"])
                    cpl_str_ad = f"${ad['cpl_30d']:.2f}" if ad["cpl_30d"] is not None else "no leads"
                    lines.append(
                        f"     Ad Set: {ad['adset_name'][:60]} | spend: {spend_str} | "
                        f"leads: {leads_str} | CPL: {cpl_str_ad}"
                    )
            lines.append("")

        return "\n".join(lines)
