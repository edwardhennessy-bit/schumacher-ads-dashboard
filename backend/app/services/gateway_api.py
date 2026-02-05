"""
Gateway API Service for fetching real-time data from ad platforms.

This service connects to the SingleGrain MCP Gateway to fetch live
performance data with custom date ranges from Meta, Google Ads, etc.
"""

import os
import httpx
import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Gateway MCP server endpoint (if running locally)
GATEWAY_BASE_URL = os.getenv("GATEWAY_API_URL", "http://localhost:3000")

# Known account IDs for quick access
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
    "low_cost_interlock": "act_3009576865739732",
}


@dataclass
class DateRange:
    """Represents a date range for API queries."""
    start_date: str  # YYYY-MM-DD format
    end_date: str    # YYYY-MM-DD format

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
    if "february" in query_lower:
        return DateRange.this_month()

    # Check for "january" (last month in Feb context)
    if "january" in query_lower:
        # January 2026
        return DateRange(start_date="2026-01-01", end_date="2026-01-31")

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


def get_date_preset(date_range: DateRange) -> Optional[str]:
    """Convert DateRange to Meta API date preset if applicable."""
    today = datetime.now().strftime("%Y-%m-%d")

    if date_range.end_date == today:
        start = datetime.strptime(date_range.start_date, "%Y-%m-%d")
        end = datetime.strptime(date_range.end_date, "%Y-%m-%d")
        days_diff = (end - start).days

        if days_diff == 6:
            return "last_7d"
        elif days_diff == 29 or days_diff == 30:
            return "last_30d"

    return None


class GatewayAPIService:
    """
    Service for fetching live data from ad platform APIs via the Gateway.

    This class provides methods to query Meta, Google Ads, and LinkedIn
    with custom date ranges.
    """

    def __init__(self):
        """Initialize the Gateway API service."""
        self.base_url = GATEWAY_BASE_URL
        logger.info("gateway_api_service_initialized", base_url=self.base_url)

    async def get_meta_account_insights(
        self,
        account_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """
        Fetch Meta account insights for a specific date range.

        This method would normally call the MCP Gateway endpoint.
        For now, it returns a structured request that can be processed.
        """
        date_preset = get_date_preset(date_range)

        request_info = {
            "platform": "meta",
            "account_id": account_id,
            "date_range": {
                "start": date_range.start_date,
                "end": date_range.end_date,
            },
            "date_preset": date_preset,
            "metrics_requested": [
                "spend", "impressions", "clicks", "reach",
                "ctr", "cpc", "cpm", "leads", "cost_per_lead"
            ]
        }

        logger.info(
            "meta_insights_request",
            account_id=account_id,
            date_range=f"{date_range.start_date} to {date_range.end_date}"
        )

        return request_info

    async def get_meta_campaign_report(
        self,
        account_id: str,
        date_range: DateRange,
    ) -> Dict[str, Any]:
        """
        Fetch Meta campaign-level performance report.
        """
        request_info = {
            "platform": "meta",
            "account_id": account_id,
            "level": "campaign",
            "date_range": {
                "start": date_range.start_date,
                "end": date_range.end_date,
            },
        }

        logger.info(
            "meta_campaign_report_request",
            account_id=account_id,
            date_range=f"{date_range.start_date} to {date_range.end_date}"
        )

        return request_info

    def format_api_request_for_context(self, request_info: Dict[str, Any]) -> str:
        """
        Format API request info as context for the AI to understand
        what data is being requested.
        """
        lines = [
            "=== DATA REQUEST INFO ===",
            f"Platform: {request_info.get('platform', 'unknown').upper()}",
            f"Account: {request_info.get('account_id')}",
            f"Date Range: {request_info['date_range']['start']} to {request_info['date_range']['end']}",
        ]

        if request_info.get('level'):
            lines.append(f"Level: {request_info['level']}")

        if request_info.get('date_preset'):
            lines.append(f"Preset: {request_info['date_preset']}")

        return "\n".join(lines)
