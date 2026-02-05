"""Anthropic Claude client for AI-powered analysis and recommendations."""

from __future__ import annotations

import asyncio
import anthropic
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# System prompt for the Paid Media Analyst persona
ANALYST_SYSTEM_PROMPT = """You are JARVIS, a world-class Senior Paid Media Analyst and Strategist. Your goal is to maximize ROI/ROAS and scale performance across multi-channel environments (Google, Meta, TikTok, Bing, etc.). You are data-driven, skeptical of platform-automated "recommendations" that don't serve the bottom line, and highly focused on efficient budget allocation.

IMPORTANT - Your Capabilities:

**1. FILE PROCESSING:**
You CAN and DO process files that users upload to Slack. The system automatically processes:
- CSV files (performance data, reports)
- Excel files (.xlsx, .xls) including multi-sheet workbooks
- PDF documents (reports, presentations, briefs)
- Word documents (.docx)
- PowerPoint presentations (.pptx)
- Images (.png, .jpg, .gif, .webp) - screenshots, charts, etc.
- Text/Markdown files (.txt, .md)
- JSON files

When a user uploads a file, it is automatically processed and added to your context. You will see the extracted data in the "Additional Context" section. If file data appears there, acknowledge it and analyze it.

**2. LIVE DATA ACCESS:**
You CAN fetch live data from ad platforms for specific date ranges! When users ask about specific time periods, the system will automatically query the API. Supported date ranges include:

- "last 7 days", "last 14 days", "last 30 days", "last 60 days", "last 90 days"
- "this month" or "MTD" (month to date)
- "last month" (previous calendar month)
- "YTD" (year to date)
- Specific months like "January", "February 2026"

When you see "=== LIVE API DATA ===" in your context, this is real-time data fetched for the specific date range requested. Use this data for your analysis.

**3. DATA SOURCES:**
a) **Live API Data**: When a date range is detected in the user's query, the system automatically fetches fresh data from Meta Ads API for that period.

b) **Dashboard Data**: Default cached data from the Schumacher Dashboard showing recent performance.

c) **Uploaded Files**: Users can also upload CSV, Excel, or PDF exports for additional analysis.

Always be clear about which data source you're analyzing. If live data fetch fails, note that you're using cached dashboard data instead.

Core Objectives:

1. Synthesize Data: Ingest data from the Gateway API and user-uploaded files (CSVs, PDFs, Sheets) to build a unified view of performance.

2. Strategic Reasoning: Never provide a number without a "Why." Your reasoning should consider diminishing returns, seasonality, and channel synergy.

3. Actionable Budgeting: Provide clear, ready-to-implement budget plans.

Analytical Framework:

- Pacing Check: Compare current spend against the total monthly budget to identify over/under-pacing.
- Efficiency Analysis: Identify high-performing clusters (campaigns, ad sets, or keywords) and recommend shifting funds from low-performing areas.
- Context Integration: Heavily weight any manual context provided by the user (e.g., "The client is prioritising lead volume over lead quality this week").
- Holistic View: If Meta is driving high awareness that fuels Google Brand Search, acknowledge that synergy in your reasoning.

Response Requirements:
Every strategic recommendation must follow this structure:

1. **Executive Summary**: 2-3 sentences on current performance health.

2. **Budget Allocation Table**: A clear table with columns: [Platform, Campaign/Tactic, Current Spend, Recommended Spend, Delta (%), Reasoning].

3. **Strategic Deep-Dive**: Bullet points explaining the logic behind major shifts.

Format the Budget Allocation Table as valid JSON in a code block labeled ```budget_table``` with the following structure:
[
  {
    "Platform": "string",
    "Campaign/Tactic": "string",
    "Current Spend": "string (formatted as currency)",
    "Recommended Spend": "string (formatted as currency)",
    "Delta (%)": "string (e.g., '+15%' or '-10%')",
    "Reasoning": "string"
  }
]

Tone and Style:
- Professional, insightful, and direct.
- Avoid fluff; focus on "levers" that can be pulled to improve performance.
- When data is missing or ambiguous, state your assumptions clearly."""


class AnthropicAnalyst:
    """AI analyst powered by Anthropic's Claude for paid media strategy."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key.
            model: Model to use for analysis.
        """
        # Log API key info for debugging (masked)
        if api_key:
            logger.info("anthropic_client_init",
                       api_key_prefix=api_key[:20] if len(api_key) > 20 else "too_short",
                       api_key_length=len(api_key))
        else:
            logger.error("anthropic_client_init_no_key", api_key_provided=False)

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._conversation_context: List[Dict[str, str]] = []

    def clear_context(self) -> None:
        """Clear the conversation context for a fresh analysis."""
        self._conversation_context = []

    def add_context(self, context: str) -> None:
        """
        Add contextual information to the conversation.

        Args:
            context: Additional context string (e.g., client priorities, constraints).
        """
        self._conversation_context.append({
            "role": "user",
            "content": f"Additional context: {context}"
        })
        self._conversation_context.append({
            "role": "assistant",
            "content": "Understood. I'll incorporate this context into my analysis."
        })

    async def analyze_performance(
        self,
        performance_data: Dict[str, Any],
        user_query: str,
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Analyze performance data and generate strategic recommendations.

        Args:
            performance_data: Dictionary containing campaign/platform performance metrics.
            user_query: The user's specific question or request.
            additional_context: Optional additional context from uploaded files or thread.

        Returns:
            Analysis response with recommendations.
        """
        # Build the analysis prompt
        data_summary = self._format_performance_data(performance_data)

        prompt = f"""## Current Performance Data
{data_summary}

## User Request
{user_query}
"""
        if additional_context:
            prompt += f"""
## Additional Context
{additional_context}
"""

        # Build messages with conversation context
        messages = self._conversation_context.copy()
        messages.append({"role": "user", "content": prompt})

        logger.info("requesting_analysis", query_length=len(user_query))

        # Run synchronous Anthropic API call in thread pool to avoid blocking event loop
        def _make_request():
            return self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=ANALYST_SYSTEM_PROMPT,
                messages=messages,
            )

        response = await asyncio.to_thread(_make_request)

        analysis = response.content[0].text

        # Store this exchange in context for follow-up questions
        self._conversation_context.append({"role": "user", "content": prompt})
        self._conversation_context.append({"role": "assistant", "content": analysis})

        logger.info("analysis_complete", response_length=len(analysis))

        return analysis

    async def generate_budget_allocation(
        self,
        current_allocations: List[Dict[str, Any]],
        total_budget: float,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a budget allocation recommendation.

        Args:
            current_allocations: List of current budget allocations by campaign/platform.
            total_budget: Total budget to allocate.
            constraints: Optional constraints (min/max per platform, etc.).

        Returns:
            Budget allocation recommendation with reasoning.
        """
        prompt = f"""## Budget Allocation Request

**Total Budget to Allocate:** ${total_budget:,.2f}

**Current Allocations:**
{self._format_allocations(current_allocations)}
"""
        if constraints:
            prompt += f"""
**Constraints:**
{self._format_constraints(constraints)}
"""

        prompt += """
Please provide an optimized budget allocation with clear reasoning for each recommendation.
"""

        messages = self._conversation_context.copy()
        messages.append({"role": "user", "content": prompt})

        # Run synchronous Anthropic API call in thread pool to avoid blocking event loop
        def _make_request():
            return self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=ANALYST_SYSTEM_PROMPT,
                messages=messages,
            )

        response = await asyncio.to_thread(_make_request)

        return response.content[0].text

    def _format_performance_data(self, data: Dict[str, Any]) -> str:
        """Format performance data for the prompt."""
        lines = []

        if "summary" in data:
            summary = data["summary"]
            lines.append("### Account Summary")
            lines.append(f"- Total Spend: ${summary.get('total_spend', 0):,.2f}")
            lines.append(f"- Total Budget: ${summary.get('total_budget', 0):,.2f}")
            lines.append(f"- Impressions: {summary.get('impressions', 0):,}")
            lines.append(f"- Clicks: {summary.get('clicks', 0):,}")
            lines.append(f"- Leads: {summary.get('leads', 0):,}")
            lines.append(f"- Cost per Lead: ${summary.get('cost_per_lead', 0):.2f}")
            lines.append(f"- CTR: {summary.get('ctr', 0):.2f}%")
            lines.append(f"- CPC: ${summary.get('cpc', 0):.2f}")
            lines.append("")

        if "campaigns" in data:
            lines.append("### Campaign Performance")
            for campaign in data["campaigns"]:
                lines.append(f"**{campaign.get('name', 'Unknown')}** ({campaign.get('platform', 'Meta')})")
                lines.append(f"  - Status: {campaign.get('status', 'Unknown')}")
                lines.append(f"  - Spend: ${campaign.get('spend', 0):,.2f}")
                lines.append(f"  - Impressions: {campaign.get('impressions', 0):,}")
                lines.append(f"  - Clicks: {campaign.get('clicks', 0):,}")
                lines.append(f"  - Leads: {campaign.get('leads', 0):,}")
                lines.append(f"  - Cost per Lead: ${campaign.get('cost_per_lead', 0):.2f}")
                lines.append(f"  - CTR: {campaign.get('ctr', 0):.2f}%")
                lines.append("")

        if "platforms" in data:
            lines.append("### Platform Summary")
            for platform, metrics in data["platforms"].items():
                lines.append(f"**{platform}**")
                lines.append(f"  - Spend: ${metrics.get('spend', 0):,.2f}")
                lines.append(f"  - Leads: {metrics.get('leads', 0):,}")
                lines.append(f"  - Cost per Lead: ${metrics.get('cpl', 0):.2f}")
                lines.append("")

        return "\n".join(lines) if lines else "No performance data available."

    def _format_allocations(self, allocations: List[Dict[str, Any]]) -> str:
        """Format current allocations for the prompt."""
        lines = []
        for alloc in allocations:
            lines.append(
                f"- {alloc.get('platform', 'Unknown')} / {alloc.get('campaign', 'All')}: "
                f"${alloc.get('spend', 0):,.2f}"
            )
        return "\n".join(lines) if lines else "No current allocations."

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format constraints for the prompt."""
        lines = []
        for key, value in constraints.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "No specific constraints."
