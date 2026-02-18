"""
Google Docs generator for Weekly Agendas.

Creates structured Google Docs with performance snapshots,
action items, platform updates, and discussion topics.
"""

import structlog
from typing import Any, Dict, List
from datetime import date

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = structlog.get_logger(__name__)


def _fmt_currency(value: float) -> str:
    if abs(value) >= 1000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _fmt_number(value) -> str:
    v = int(round(value)) if isinstance(value, float) else value
    return f"{v:,}" if abs(v) >= 1000 else str(v)


class DocsGenerator:
    """Creates Google Docs documents for weekly agendas."""

    def __init__(self, credentials: Credentials):
        self.service = build("docs", "v1", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    async def create_weekly_agenda(
        self,
        data: Dict[str, Any],
        insights: Dict[str, Any],
        week_of: str,
    ) -> Dict[str, str]:
        """Create a weekly agenda Google Doc.

        Returns {"id": doc_id, "url": doc_url, "title": title}
        """
        d = date.fromisoformat(week_of)
        title = f"Schumacher Homes — Weekly Agenda — {d.strftime('%B %d, %Y')}"

        # Create the document
        doc = self.service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]

        # Build content requests (insert in reverse order since each inserts at index 1)
        requests = []
        idx = 1  # Start after the title

        # ── Performance Snapshot ──────────────────────────────────
        idx = self._add_heading(requests, idx, "Performance Snapshot")
        snapshot = insights.get("performance_snapshot", "")
        if snapshot:
            idx = self._add_paragraph(requests, idx, snapshot)
        idx = self._add_paragraph(requests, idx, "")

        # KPI summary table as text
        agg = data.get("aggregated", {})
        kpi_lines = [
            f"Total Spend: {_fmt_currency(agg.get('total_spend', 0))}",
            f"Total Leads: {_fmt_number(agg.get('total_leads', 0))}",
            f"Blended CPL: {_fmt_currency(agg.get('blended_cpl', 0))}",
            f"Opportunities: {_fmt_number(agg.get('total_opportunities', 0))}",
            f"Cost / Opportunity: {_fmt_currency(agg.get('blended_cpo', 0))}",
        ]
        for line in kpi_lines:
            idx = self._add_bullet(requests, idx, line)
        idx = self._add_paragraph(requests, idx, "")

        # ── Platform Updates ──────────────────────────────────────
        idx = self._add_heading(requests, idx, "Platform Updates")

        platform_updates = insights.get("platform_updates", {})

        # Meta section
        meta = data.get("meta")
        if meta:
            idx = self._add_subheading(requests, idx, "Meta (Facebook / Instagram)")
            meta_update = platform_updates.get("meta", "")
            if meta_update:
                idx = self._add_paragraph(requests, idx, meta_update)
            meta_summary = (
                f"Spend: {_fmt_currency(meta.get('spend', 0))}  |  "
                f"Leads: {_fmt_number(meta.get('leads', 0))}  |  "
                f"CPL: {_fmt_currency(meta.get('cost_per_lead', 0))}"
            )
            idx = self._add_paragraph(requests, idx, meta_summary)
            idx = self._add_paragraph(requests, idx, "")

        # Google section
        google = data.get("google")
        if google:
            idx = self._add_subheading(requests, idx, "Google Ads")
            google_update = platform_updates.get("google", "")
            if google_update:
                idx = self._add_paragraph(requests, idx, google_update)
            google_summary = (
                f"Spend: {_fmt_currency(google.get('spend', 0))}  |  "
                f"MQLs: {_fmt_number(google.get('leads', 0))}  |  "
                f"CPL: {_fmt_currency(google.get('cost_per_lead', 0))}  |  "
                f"Opps: {_fmt_number(google.get('opportunities', 0))}"
            )
            idx = self._add_paragraph(requests, idx, google_summary)
            idx = self._add_paragraph(requests, idx, "")

        # ── Status & Action Items ─────────────────────────────────
        idx = self._add_heading(requests, idx, "Status & Action Items")
        idx = self._add_bullet(requests, idx, "[Open items from last week]")
        idx = self._add_bullet(requests, idx, "[New items this week]")
        idx = self._add_paragraph(requests, idx, "")

        # ── Discussion Topics ─────────────────────────────────────
        idx = self._add_heading(requests, idx, "Discussion Topics")
        topics = insights.get("discussion_topics", [])
        if topics:
            for topic in topics:
                idx = self._add_bullet(requests, idx, topic)
        else:
            idx = self._add_bullet(requests, idx, "Wins & Highlights")
            idx = self._add_bullet(requests, idx, "Areas of Concern")
            idx = self._add_bullet(requests, idx, "Upcoming Plans & Tests")
            idx = self._add_bullet(requests, idx, "Budget Review")
        idx = self._add_paragraph(requests, idx, "")

        # Execute all requests
        if requests:
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests},
            ).execute()

        url = f"https://docs.google.com/document/d/{doc_id}/edit"
        logger.info("doc_created", title=title, url=url)
        return {"id": doc_id, "url": url, "title": title}

    # ── Helpers ────────────────────────────────────────────────────

    def _add_heading(
        self, requests: List, idx: int, text: str
    ) -> int:
        """Add a heading and return the new index."""
        requests.append({
            "insertText": {"location": {"index": idx}, "text": text + "\n"}
        })
        end = idx + len(text)
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end + 1},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        })
        return end + 1

    def _add_subheading(
        self, requests: List, idx: int, text: str
    ) -> int:
        """Add a subheading."""
        requests.append({
            "insertText": {"location": {"index": idx}, "text": text + "\n"}
        })
        end = idx + len(text)
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": idx, "endIndex": end + 1},
                "paragraphStyle": {"namedStyleType": "HEADING_3"},
                "fields": "namedStyleType",
            }
        })
        return end + 1

    def _add_paragraph(
        self, requests: List, idx: int, text: str
    ) -> int:
        """Add a normal paragraph."""
        full = text + "\n"
        requests.append({
            "insertText": {"location": {"index": idx}, "text": full}
        })
        return idx + len(full)

    def _add_bullet(
        self, requests: List, idx: int, text: str
    ) -> int:
        """Add a bullet point."""
        full = text + "\n"
        requests.append({
            "insertText": {"location": {"index": idx}, "text": full}
        })
        end = idx + len(full)
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": idx, "endIndex": end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })
        return end
