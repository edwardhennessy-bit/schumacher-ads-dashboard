"""
Gateway API Client for direct API queries with custom date ranges.

This service enables JARVIS to query platform APIs (Meta, Google, LinkedIn)
with custom date ranges instead of relying on cached data.
"""

import httpx
import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

# Known account IDs for quick access
ACCOUNT_IDS = {
    "schumacher": "act_142003632",
    "schumacher_homes": "act_142003632",
    "cheddar_up": "act_29125558",
    "upkeep": "act_143371293",
    "bierman": "act_104107839747101",
    "netquest": "act_104038476438296",
    "nextiva": "act_286048099",
    "helium10": "act_105487233155545",
    "learning_az": "act_109596339489054",
    "spark_hire": "act_1899357427042682",
    "smartling": "act_2419341138098567",
    "low_cost_interlock": "act_3009576865739732",
    "tax_lien_code": "act_765733914282283",
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

    @classmethod
    def custom(cls, start: str, end: str) -> "DateRange":
        """Create a custom date range."""
        return cls(start_date=start, end_date=end)


def parse_date_range_from_query(query: str) -> Optional[DateRange]:
    """
    Parse natural language date range from user query.

    Examples:
    - "last 7 days" -> DateRange.last_n_days(7)
    - "last 30 days" -> DateRange.last_n_days(30)
    - "this month" -> DateRange.this_month()
    - "last month" -> DateRange.last_month()
    - "MTD" -> DateRange.this_month()
    - "YTD" -> DateRange.year_to_date()
    - "January 2024" -> Custom range for that month
    """
    query_lower = query.lower()

    # Check for specific patterns
    if "last 7 days" in query_lower or "past 7 days" in query_lower or "past week" in query_lower:
        return DateRange.last_n_days(7)

    if "last 14 days" in query_lower or "past 14 days" in query_lower or "past two weeks" in query_lower:
        return DateRange.last_n_days(14)

    if "last 30 days" in query_lower or "past 30 days" in query_lower or "past month" in query_lower:
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

    # Check for specific month names
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }

    for month_name, month_num in months.items():
        if month_name in query_lower:
            # Try to find year
            import re
            year_match = re.search(r'20\d{2}', query)
            year = int(year_match.group()) if year_match else datetime.now().year

            # Create date range for that month
            from calendar import monthrange
            _, last_day = monthrange(year, month_num)
            start = f"{year}-{month_num:02d}-01"
            end = f"{year}-{month_num:02d}-{last_day:02d}"
            return DateRange.custom(start, end)

    # Default: return None (will use default date range)
    return None


def get_account_id(query: str) -> str:
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


def format_date_preset(date_range: DateRange) -> Optional[str]:
    """Convert DateRange to Meta API date preset if applicable."""
    today = datetime.now().strftime("%Y-%m-%d")

    if date_range.end_date == today:
        days_diff = (datetime.now() - datetime.strptime(date_range.start_date, "%Y-%m-%d")).days

        if days_diff == 7:
            return "last_7d"
        elif days_diff == 30:
            return "last_30d"

    return None  # Use explicit dates
