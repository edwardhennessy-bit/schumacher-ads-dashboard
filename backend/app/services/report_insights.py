"""
Claude-powered insights service for report generation.

Uses the Anthropic Claude API to generate executive summaries,
recommendations, and narrative content for reports.
"""

import json
import structlog
from typing import Any, Dict

import anthropic

logger = structlog.get_logger(__name__)


class ReportInsightsService:
    """Generates AI-powered insights for performance reports."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    async def generate_monthly_insights(
        self, data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate all narrative sections for a monthly report."""
        data_summary = self._format_data_for_prompt(data)

        prompt = f"""You are a senior paid media strategist writing a monthly performance review for Schumacher Homes (a home builder). Based on the following performance data, generate:

1. **executive_summary** — 3-4 sentence overview of the month's performance. Highlight the most important KPIs and notable changes. Be specific with numbers.

2. **key_wins** — 3-5 bullet points of positive highlights (things that went well). Each bullet should be a concise, data-backed statement.

3. **areas_of_concern** — 2-4 bullet points of areas that need attention. Be constructive, not alarmist.

4. **recommendations** — 3-5 actionable recommendations for the next month. Be specific about what to do and why.

5. **next_steps** — 3-4 concrete next steps for testing and strategy. Include specific tactics to try.

Performance Data:
{data_summary}

Respond in JSON format with these exact keys: executive_summary, key_wins (array of strings), areas_of_concern (array of strings), recommendations (array of strings), next_steps (array of strings)."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text

            # Parse JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except Exception as e:
            logger.error("insights_generation_failed", error=str(e))
            return {
                "executive_summary": "Performance data is available but AI insights could not be generated.",
                "key_wins": [],
                "areas_of_concern": [],
                "recommendations": [],
                "next_steps": [],
            }

    async def generate_weekly_insights(
        self, data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate narrative for weekly agenda/email."""
        data_summary = self._format_data_for_prompt(data)

        prompt = f"""You are a senior paid media strategist writing a weekly performance update for Schumacher Homes (a home builder). Based on the following weekly performance data, generate:

1. **performance_snapshot** — 2-3 sentence summary of the week. Be concise and data-driven.

2. **platform_updates** — Brief update per platform (Meta, Google). 1-2 sentences each noting any notable changes or actions taken.

3. **discussion_topics** — 3-5 bullet points for a client meeting agenda. Include wins to celebrate, concerns to address, and upcoming plans.

4. **email_subject** — A professional email subject line for the weekly update (e.g., "Schumacher Homes Weekly Update — [Date Range]")

5. **email_body** — A professional, client-facing email body (3-4 paragraphs). Friendly but professional tone. Include key metrics, highlights, and what's coming next.

Performance Data:
{data_summary}

Respond in JSON format with these exact keys: performance_snapshot, platform_updates (object with "meta" and "google" keys), discussion_topics (array of strings), email_subject, email_body."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except Exception as e:
            logger.error("weekly_insights_failed", error=str(e))
            return {
                "performance_snapshot": "",
                "platform_updates": {"meta": "", "google": ""},
                "discussion_topics": [],
                "email_subject": "",
                "email_body": "",
            }

    def _format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format report data into a readable summary for Claude."""
        lines = []

        agg = data.get("aggregated", {})
        if agg:
            lines.append("=== CROSS-PLATFORM TOTALS ===")
            lines.append(f"Total Spend: ${agg.get('total_spend', 0):,.2f}")
            lines.append(f"Total Leads: {agg.get('total_leads', 0):,}")
            lines.append(f"Blended CPL: ${agg.get('blended_cpl', 0):,.2f}")
            lines.append(f"Total Opportunities: {agg.get('total_opportunities', 0):,}")
            lines.append(f"Blended Cost/Opportunity: ${agg.get('blended_cpo', 0):,.2f}")
            lines.append("")

        for key in ("meta", "google"):
            plat = data.get(key)
            if not plat:
                continue
            name = plat.get("platform", key.title())
            lines.append(f"=== {name.upper()} ===")
            lines.append(f"Spend: ${plat.get('spend', 0):,.2f} ({plat.get('spend_change', 0):+.1f}% vs prior period)")
            lines.append(f"Leads: {plat.get('leads', 0):,} ({plat.get('leads_change', 0):+.1f}%)")
            lines.append(f"CPL: ${plat.get('cost_per_lead', 0):,.2f} ({plat.get('cpl_change', 0):+.1f}%)")
            lines.append(f"Opportunities: {plat.get('opportunities', 0):,} ({plat.get('opportunities_change', 0):+.1f}%)")
            lines.append(f"Cost/Opportunity: ${plat.get('cost_per_opportunity', 0):,.2f}")
            lines.append(f"Impressions: {plat.get('impressions', 0):,}")
            lines.append(f"Clicks: {plat.get('clicks', 0):,}")
            lines.append(f"CTR: {plat.get('ctr', 0):.2f}%")
            lines.append(f"CPC: ${plat.get('cpc', 0):,.2f}")

            if plat.get("remarketing_cpl"):
                lines.append(f"Remarketing CPL: ${plat['remarketing_cpl']:,.2f} ({plat.get('remarketing_leads', 0)} leads)")
            if plat.get("prospecting_cpl"):
                lines.append(f"Prospecting CPL: ${plat['prospecting_cpl']:,.2f} ({plat.get('prospecting_leads', 0)} leads)")

            campaigns = plat.get("campaigns", [])
            if campaigns:
                lines.append(f"\nTop 5 Campaigns by Spend:")
                for c in campaigns[:5]:
                    lines.append(
                        f"  - {c.get('name', 'Unknown')}: "
                        f"${c.get('spend', 0):,.2f} spend, "
                        f"{c.get('leads', c.get('clicks', 0))} leads, "
                        f"${c.get('cost_per_lead', c.get('cpc', 0)):,.2f} CPL"
                    )
            lines.append("")

        return "\n".join(lines)
