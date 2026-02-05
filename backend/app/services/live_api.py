"""
Live API Service for fetching real-time data from ad platforms.

This service makes HTTP requests to fetch live performance data
with custom date ranges from Meta, Google Ads, and LinkedIn.
"""

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


def parse_date_range_from_query(query: str) -> Optional[DateRange]:
    """
    Parse natural language date range from user query.
    """
    import re
    query_lower = query.lower()

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
        Fetch campaign-level performance data.
        """
        if not self.meta_token:
            return {"error": "Meta API token not configured"}

        fields = [
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

        params = {
            "access_token": self.meta_token,
            "fields": ",".join(fields),
            "time_range": f'{{"since":"{date_range.start_date}","until":"{date_range.end_date}"}}',
            "level": "campaign",
            "limit": 100
        }

        url = f"{META_API_BASE}/{account_id}/insights"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "account_id": account_id,
                    "date_range": {
                        "start": date_range.start_date,
                        "end": date_range.end_date
                    },
                    "campaigns": data.get("data", [])
                }

        except Exception as e:
            logger.error("meta_campaigns_error", error=str(e))
            return {"success": False, "error": str(e)}

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
        """
        if not campaign_data.get("success"):
            return f"API Error: {campaign_data.get('error', 'Unknown error')}"

        lines = [
            "=== LIVE CAMPAIGN DATA ===",
            f"Account: {campaign_data.get('account_id')}",
            f"Date Range: {campaign_data['date_range']['start']} to {campaign_data['date_range']['end']}",
            ""
        ]

        campaigns = campaign_data.get("campaigns", [])
        if not campaigns:
            lines.append("No campaign data available for this date range.")
            return "\n".join(lines)

        lines.append(f"### Campaigns ({len(campaigns)} total)")
        lines.append("")

        for camp in campaigns:
            name = camp.get("campaign_name", "Unknown")
            spend = float(camp.get("spend", 0))
            impressions = int(camp.get("impressions", 0))
            clicks = int(camp.get("clicks", 0))
            ctr = float(camp.get("ctr", 0))
            cpc = float(camp.get("cpc", 0))

            # Extract leads
            leads = 0
            for action in camp.get("actions", []):
                if action.get("action_type") == "lead":
                    leads = int(action.get("value", 0))
                    break

            cpl = spend / leads if leads > 0 else 0

            lines.extend([
                f"**{name}**",
                f"  - Spend: ${spend:,.2f}",
                f"  - Impressions: {impressions:,}",
                f"  - Clicks: {clicks:,}",
                f"  - CTR: {ctr:.2f}%",
                f"  - CPC: ${cpc:.2f}",
                f"  - Leads: {leads}",
                f"  - CPL: ${cpl:.2f}",
                ""
            ])

        return "\n".join(lines)
