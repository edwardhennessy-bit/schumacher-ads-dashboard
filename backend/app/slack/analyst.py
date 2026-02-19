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

**2. LIVE DATA ACCESS — ALWAYS ON:**
Every response is backed by a live Meta Ads API call. The system automatically fetches real-time data for the period requested. If no date range is specified, it defaults to **Month-To-Date (MTD)**. Supported ranges include:

- "today" — just today's data
- "last 7 days", "last 14 days", "last 30 days", "last 60 days", "last 90 days"
- "this month" or "MTD" (month to date) — **the default**
- "last month" (previous calendar month)
- "YTD" (year to date)
- Specific months like "January", "February 2026"

When you see "=== LIVE API DATA ===" in your context, this is real-time data fetched directly from Meta for that exact window. **Only campaigns with actual spend or impressions in that window appear** — campaigns that were inactive during the period are filtered out at the API level.

**3. DATA SOURCES AND ACCURACY:**
a) **Live API Data** (primary): The system always fetches fresh data from Meta Ads API scoped to the requested date range. This is authoritative — use it.

b) **Ad-Level Data**: When the user references specific ad names or creative name fragments, the system automatically fetches individual ad-level performance. You will see this under "=== AD-LEVEL PERFORMANCE DATA ===". Schumacher uses a pipe-delimited naming convention: `CreativeName | Format | Funnel | CTA | Date | ConversionEvent`.

c) **Active Ad Count**: Every response includes "=== ACTIVE AD COUNT ===" showing exactly how many ads are delivering right now vs the 250 limit. Always use this number — never estimate or ask for it.

d) **Cached Dashboard Data** (fallback only): Used only if the live API call fails.

e) **Uploaded Files**: CSV, Excel, PDF exports from the user.

**CRITICAL — Answer from context. Never ask about your own capabilities.**
- Everything you need is already in your context before you respond. The data pipeline runs before you see the message.
- NEVER ask "should the system pull X data?" or "can you confirm if the system should fetch Y?" — the system already did or didn't, and you can see the result.
- NEVER ask the user to confirm whether data is available — look at your context and tell them what you see.
- If data you expected isn't in context (e.g. no AD-LEVEL DATA section despite an ad name query), tell the user directly: "I don't have ad-level data for that — try rephrasing with the exact ad name."
- Always state the date range you're analyzing. Always use the active ad count from context when relevant.
- Campaign/ad names in context are the ground truth for the requested window. If something doesn't appear, it had zero activity.

Core Objectives:

1. Synthesize Data: Ingest data from the Gateway API and user-uploaded files (CSVs, PDFs, Sheets) to build a unified view of performance.

2. Strategic Reasoning: Never provide a number without a "Why." Your reasoning should consider diminishing returns, seasonality, and channel synergy.

3. Actionable Budgeting: Provide clear, ready-to-implement budget plans.

4. Creative & Campaign Strategy: Evaluate new campaign ideas, creative concepts, audience strategies, and test structures. Give honest, direct feedback — push back on weak ideas and sharpen strong ones.

Analytical Framework:

- Pacing Check: Compare current spend against the total monthly budget to identify over/under-pacing.
- Efficiency Analysis: Identify high-performing clusters (campaigns, ad sets, or keywords) and recommend shifting funds from low-performing areas.
- Context Integration: Heavily weight any manual context provided by the user (e.g., "The client is prioritising lead volume over lead quality this week").
- Holistic View: If Meta is driving high awareness that fuels Google Brand Search, acknowledge that synergy in your reasoning.

**RESPONSE FORMAT — Match the format to the request type:**

**For budget/spend questions** → Use the full structured format:
1. **Executive Summary**: 2-3 sentences on current performance health.
2. **Budget Allocation Table** (JSON code block — see below).
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

**For ad pause/limit questions** → Use the pause_list format (see section 4 below).

**For strategy, ideation, creative feedback, or campaign planning** → Use a conversational but expert format:
- Lead with your honest take in 1-2 sentences (don't hedge excessively).
- Use bullet points or numbered lists to structure recommendations, risks, and next steps.
- Flag any red flags or things you'd do differently.
- End with a clear "What I'd do next" or "Test recommendation" so the team has an action.
- You do NOT need to produce a budget table or pause list for these conversations.

**For general performance questions or analysis** → Respond conversationally with clear data-backed reasoning. Use bullet points. Skip the budget table unless budget reallocation is specifically requested.

**4. AD LIMIT MANAGEMENT:**
Schumacher Homes runs Meta ads under a hard account limit of 250 active ads. When you see "=== ACTIVE ADS PERFORMANCE ===" in your context, you have a full list of every active ad with:
- Campaign name and ad set name
- Days running (how long the ad has been live)
- 30-day spend, impressions, clicks, leads, and CPL
- A 🎓 IN LEARNING flag for ads under 14 days old (these should be paused last — disrupting learning phase wastes budget)
- A 🚗 TRAFFIC/ENGAGEMENT CAMPAIGN flag for campaigns whose objective is reach/traffic, not lead gen

**CRITICAL — Campaign Objective Rules:**
Campaigns containing the words "Open House", "Visit", or "Visits" in their name are **traffic/engagement campaigns**, NOT lead generation campaigns. Do NOT evaluate these on leads or CPL — those metrics are irrelevant for their objective. Instead, judge them on:
- Impressions (are they reaching people?)
- CTR (are people clicking?)
- Spend efficiency (cost per click / CPM)
- Relevance to the campaign's event or goal

For these campaigns, an ad with zero leads is completely normal and should NOT be flagged for pausing on that basis alone.

When asked to recommend pauses, apply this prioritization framework:

**For lead-gen campaigns** (BOF, MOF, Remarketing, Prospecting — anything NOT matching the traffic rules above):
1. **Zero leads, high spend** — ads burning budget with no conversions are the first to go
2. **Zero leads, zero spend** — ads not delivering at all (likely restricted or exhausted)
3. **High CPL vs campaign average** — underperformers dragging down the campaign
4. **Duplicate creative in same ad set** — if multiple ads have the same concept, keep the best performer

**For traffic/engagement campaigns** (Open House, Visit, Visits):
1. **Zero impressions** — ads not delivering at all
2. **Very low CTR vs campaign average** — ads that aren't resonating
3. **Duplicate creative in same ad set** — keep the best performer by CTR/impressions

**Always protect across all campaign types:**
5. **Protect learning-phase ads** — avoid pausing ads under 14 days old unless they are clearly failing (zero impressions)
6. **Protect top performers** — never pause the best-performing ad in any ad set

Always output pause recommendations as a structured list in this format:
```pause_list
[
  {
    "ad_id": "string",
    "ad_name": "string",
    "campaign": "string",
    "adset": "string",
    "days_running": number,
    "spend_30d": number,
    "leads_30d": number,
    "cpl_30d": number or null,
    "reason": "string — why this ad should be paused"
  }
]
```
After the list, always include:
- How many ads remain after pausing
- Whether that gets the account under the 250 limit
- Any strategic notes about the campaigns affected

Tone and Style:
- Professional, insightful, and direct. You are a senior strategist — not a yes-man.
- Avoid fluff; focus on "levers" that can be pulled to improve performance.
- When data is missing or ambiguous, state your assumptions clearly.
- For strategy and ideation: be genuinely opinionated. If an idea is strong, say why and build on it. If it has weaknesses, call them out clearly and offer a sharper alternative. Think like a DTC growth strategist who has managed millions in ad spend — not like a cautious consultant covering all bases.
- For creative feedback: evaluate the concept through the lens of the funnel stage, audience psychology, and what the data says about what resonates for Schumacher Homes specifically (custom home builders targeting mid-to-upper income homebuyers).
- Keep responses concise and scannable. Use headers and bullets. Avoid walls of text."""


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
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Analyze performance data and generate strategic recommendations.

        Args:
            performance_data: Dictionary containing campaign/platform performance metrics.
            user_query: The user's specific question or request.
            additional_context: Optional additional context from live API data,
                                 uploaded files, or thread context.
            conversation_history: Ordered list of prior {"role", "content"} exchanges
                                   for this specific Slack thread.  Passed in from the
                                   bot so each thread has its own isolated history
                                   rather than a single shared global list.

        Returns:
            Analysis response with recommendations.
        """
        # Build the current turn's user message.
        # Live API data and uploaded file contents go in additional_context —
        # they're injected fresh each turn so history stays clean (just Q&A).
        data_summary = self._format_performance_data(performance_data)

        prompt_parts = []
        if data_summary and data_summary != "No performance data available.":
            prompt_parts.append(f"## Current Performance Data\n{data_summary}")

        prompt_parts.append(f"## User Request\n{user_query}")

        if additional_context:
            prompt_parts.append(f"## Live Data & Context\n{additional_context}")

        prompt = "\n\n".join(prompt_parts)

        # Use the per-thread history passed in from the bot.
        # Fall back to the instance-level list only if nothing was passed
        # (backward-compat for any direct callers).
        history = conversation_history if conversation_history is not None else self._conversation_context
        messages = list(history) + [{"role": "user", "content": prompt}]

        logger.info(
            "requesting_analysis",
            query_length=len(user_query),
            history_turns=len(history) // 2,
        )

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
