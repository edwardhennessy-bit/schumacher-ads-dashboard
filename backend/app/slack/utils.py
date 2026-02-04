"""Utility functions for the Slack bot."""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, List, Dict, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


def parse_budget_table_from_response(response_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Extract the budget allocation table from an analysis response.

    The AI is instructed to format budget tables as JSON in a code block
    labeled ```budget_table```.

    Args:
        response_text: The full response text from the AI analyst.

    Returns:
        List of budget allocation dictionaries, or None if not found.
    """
    # Look for the budget_table code block
    pattern = r"```budget_table\s*\n(.*?)\n```"
    match = re.search(pattern, response_text, re.DOTALL)

    if match:
        try:
            table_json = match.group(1).strip()
            data = json.loads(table_json)

            if isinstance(data, list):
                logger.info("budget_table_parsed", row_count=len(data))
                return data
            else:
                logger.warning("budget_table_not_list", data_type=type(data).__name__)
                return None

        except json.JSONDecodeError as e:
            logger.error("budget_table_json_error", error=str(e))
            return None

    # Fallback: Try to find any JSON array that looks like a budget table
    json_pattern = r"\[[\s\S]*?\{[\s\S]*?\"Platform\"[\s\S]*?\}[\s\S]*?\]"
    json_match = re.search(json_pattern, response_text)

    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, list) and len(data) > 0:
                # Verify it has expected columns
                expected_cols = {"Platform", "Campaign/Tactic", "Reasoning"}
                if expected_cols.issubset(set(data[0].keys())):
                    logger.info("budget_table_parsed_fallback", row_count=len(data))
                    return data
        except json.JSONDecodeError:
            pass

    logger.warning("no_budget_table_found")
    return None


def clean_response_for_slack(response_text: str) -> str:
    """
    Clean and format the response text for Slack display.

    Removes the JSON code block (since we'll attach it as a file)
    and ensures proper Slack markdown formatting.

    Args:
        response_text: The full response text.

    Returns:
        Cleaned response suitable for Slack.
    """
    # Remove the budget_table code block
    cleaned = re.sub(r"```budget_table\s*\n.*?\n```", "", response_text, flags=re.DOTALL)

    # Remove any duplicate newlines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Ensure bold markers work in Slack (** -> *)
    # Slack uses single asterisks for bold
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"*\1*", cleaned)

    return cleaned.strip()


def format_markdown_table(data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    """
    Convert a list of dictionaries to a GitHub-flavored Markdown table.

    Args:
        data: List of dictionaries containing the data rows.
        columns: Optional list of column names. If not provided, uses keys from first row.

    Returns:
        A formatted Markdown table string.
    """
    if not data:
        return "_No data available._"

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    # Build header
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    # Build rows
    rows = []
    for row in data:
        row_values = [str(row.get(col, "")) for col in columns]
        rows.append("| " + " | ".join(row_values) + " |")

    return "\n".join([header, separator] + rows)


def generate_csv_buffer(data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> io.StringIO:
    """
    Convert a list of dictionaries to a CSV buffer.

    Args:
        data: List of dictionaries containing the data rows.
        columns: Optional list of column names. If not provided, uses keys from first row.

    Returns:
        A StringIO buffer containing the CSV data.
    """
    if not data:
        buffer = io.StringIO()
        buffer.write("No data available")
        buffer.seek(0)
        return buffer

    # Determine columns
    if columns is None:
        columns = list(data[0].keys())

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    buffer.seek(0)

    return buffer


def generate_reports(data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> Tuple[str, io.StringIO]:
    """
    Generate both Markdown table and CSV buffer from analysis data.

    Args:
        data: List of dictionaries containing budget allocation or performance data.
        columns: Optional list of column names to include and their order.

    Returns:
        A tuple of (markdown_table, csv_buffer).
    """
    markdown_table = format_markdown_table(data, columns)
    csv_buffer = generate_csv_buffer(data, columns)

    return markdown_table, csv_buffer
