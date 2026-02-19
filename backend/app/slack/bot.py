"""JARVIS Slack Bot - Paid Media Intelligence Agent.

This bot integrates with the Schumacher Dashboard to provide
AI-powered paid media analysis via Slack.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
import httpx
import structlog

from .analyst import AnthropicAnalyst
from .file_processor import FileProcessor
from .utils import parse_budget_table_from_response, clean_response_for_slack, generate_reports
from app.services.meta_ads import MetaAdsService
from app.services.live_api import (
    LiveAPIService,
    parse_date_range_from_query,
    get_account_id_from_query,
    DateRange,
)
from app.config import get_settings

logger = structlog.get_logger(__name__)


class SlackBot:
    """
    JARVIS Slack Bot - coordinates between Slack, Meta Ads data, and AI analysis.

    This bot is integrated directly with the Schumacher Dashboard, sharing
    the same data sources and services.
    """

    def __init__(
        self,
        slack_bot_token: str,
        slack_signing_secret: str,
        slack_app_token: str,
        anthropic_api_key: str,
    ):
        """
        Initialize the Slack Bot with all required credentials.

        Args:
            slack_bot_token: Slack Bot OAuth token.
            slack_signing_secret: Slack signing secret for request verification.
            slack_app_token: Slack App-level token for Socket Mode.
            anthropic_api_key: Anthropic API key for Claude.
        """
        self.app = AsyncApp(
            token=slack_bot_token,
            signing_secret=slack_signing_secret,
        )
        self.app_token = slack_app_token

        # Initialize services - shared with dashboard
        self.meta_service = MetaAdsService()

        # Initialize Live API service for direct Meta Graph API calls
        settings = get_settings()
        self.live_api = LiveAPIService(meta_access_token=settings.meta_access_token)

        # Initialize AI analyst
        self.analyst = AnthropicAnalyst(api_key=anthropic_api_key)

        # Initialize file processor
        self.file_processor = FileProcessor()

        # Thread context storage (channel_id:thread_ts -> context)
        self._thread_contexts: Dict[str, Dict[str, Any]] = {}

        # Register handlers
        self._register_handlers()

        logger.info("jarvis_bot_initialized")

    def _register_handlers(self) -> None:
        """Register all Slack event handlers."""

        @self.app.event("app_mention")
        async def handle_app_mention(ack, event: dict, client: AsyncWebClient) -> None:
            """Handle when the bot is mentioned in a channel."""
            await ack()
            channel = event["channel"]
            user = event["user"]
            text = event["text"]
            ts = event["ts"]
            thread_ts = event.get("thread_ts")

            logger.info("app_mention_received", channel=channel, user=user)

            # Remove the bot mention from the text
            clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

            # Check for special commands
            if clean_text.lower() == "help":
                await self.handle_help_command(client, channel, thread_ts or ts)
                return

            # Check for context addition
            context_match = re.match(r"context:\s*(.+)", clean_text, re.IGNORECASE)
            if context_match:
                context = context_match.group(1).strip()
                self.add_context_to_thread(channel, thread_ts, context)
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts or ts,
                    text=f":white_check_mark: Got it! I'll consider this context: _{context}_",
                )
                return

            # Check for clear context command
            if clean_text.lower() in ["clear context", "reset", "start over"]:
                key = self.get_thread_key(channel, thread_ts)
                if key in self._thread_contexts:
                    del self._thread_contexts[key]
                # analyst._conversation_context is now vestigial but clear it too
                self.analyst.clear_context()
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts or ts,
                    text=":broom: Context cleared! Starting fresh.",
                )
                return

            # Regular analysis request
            await self.analyze_and_respond(
                client=client,
                channel=channel,
                thread_ts=thread_ts,
                user_query=clean_text,
                mention_ts=ts,
            )

        @self.app.event("message")
        async def handle_message(ack, event: dict, client: AsyncWebClient) -> None:
            """Handle direct messages and messages with file uploads."""
            await ack()
            # Ignore bot messages
            if event.get("bot_id") or event.get("subtype") == "bot_message":
                return

            channel = event["channel"]
            channel_type = event.get("channel_type", "")
            thread_ts = event.get("thread_ts")
            ts = event["ts"]

            # Handle file uploads
            files_processed = []
            if "files" in event and event["files"]:
                logger.info("files_uploaded", count=len(event["files"]), channel=channel)

                for file_info in event["files"]:
                    if self.file_processor.can_process(file_info.get("name", "")):
                        result = await self.process_file_upload(
                            client=client,
                            channel=channel,
                            thread_ts=thread_ts,
                            file_info=file_info,
                        )
                        files_processed.append(result)

                        if result.get("type") == "error":
                            await client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts or ts,
                                text=f":warning: Could not process `{file_info.get('name')}`: {result.get('error')}",
                            )
                        else:
                            file_type = result.get("type", "file")
                            filename = result.get("filename", "file")

                            if file_type == "performance_data":
                                msg = (
                                    f":white_check_mark: Processed `{filename}` - "
                                    f"found {result.get('row_count', 0)} rows of performance data. "
                                    f"Mention me with a question to analyze it!"
                                )
                            elif file_type == "document":
                                msg = (
                                    f":white_check_mark: Processed `{filename}` - "
                                    f"I'll use this as context for analysis. "
                                    f"Mention me with a question!"
                                )
                            else:
                                msg = (
                                    f":white_check_mark: Processed `{filename}`. "
                                    f"Mention me with a question to get started!"
                                )

                            await client.chat_postMessage(
                                channel=channel,
                                thread_ts=thread_ts or ts,
                                text=msg,
                            )

            # Check if there's a text message along with the file upload that contains a question
            text = event.get("text", "").strip()
            # Remove any user/bot mentions from the text
            clean_text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

            # If files were uploaded and there's also a question, analyze immediately
            if files_processed and clean_text and len(clean_text) > 5:
                logger.info("file_upload_with_question", question=clean_text[:50])
                await self.analyze_and_respond(
                    client=client,
                    channel=channel,
                    thread_ts=thread_ts,
                    user_query=clean_text,
                    mention_ts=ts,
                )
                return

            # Handle direct messages (not in channels)
            if channel_type == "im" and not files_processed:
                text = event.get("text", "").strip()
                if text:
                    # In DMs, treat every message as a query
                    await self.analyze_and_respond(
                        client=client,
                        channel=channel,
                        thread_ts=thread_ts,
                        user_query=text,
                        mention_ts=ts,
                    )

        @self.app.event("file_shared")
        async def handle_file_shared(ack, event: dict, client: AsyncWebClient) -> None:
            """Handle when a file is shared (backup handler)."""
            await ack()
            logger.debug("file_shared_event", file_id=event.get("file_id"))

        @self.app.command("/analyze")
        async def handle_analyze_command(ack, body: dict, client: AsyncWebClient) -> None:
            """Handle the /analyze slash command."""
            await ack()

            channel = body["channel_id"]
            user = body["user_id"]
            text = body.get("text", "").strip()

            logger.info("analyze_command", channel=channel, user=user)

            if not text:
                await client.chat_postEphemeral(
                    channel=channel,
                    user=user,
                    text="Please provide a query. Example: `/analyze How should I reallocate the remaining $50k?`",
                )
                return

            # Post a message indicating analysis is starting
            msg = await client.chat_postMessage(
                channel=channel,
                text=f"<@{user}> requested analysis: _{text}_",
            )

            await self.analyze_and_respond(
                client=client,
                channel=channel,
                thread_ts=None,
                user_query=text,
                mention_ts=msg["ts"],
            )

        @self.app.command("/pmhelp")
        async def handle_help_slash_command(ack, body: dict, client: AsyncWebClient) -> None:
            """Handle the /pmhelp slash command."""
            await ack()

            channel = body["channel_id"]

            await self.handle_help_command(
                client=client,
                channel=channel,
                thread_ts=None,
            )

        @self.app.command("/adreview")
        async def handle_adreview_command(ack, body: dict, client: AsyncWebClient) -> None:
            """
            Handle the /adreview slash command.
            Fetches all active ads with performance data and asks Jarvis
            to recommend which to pause to get back under the 250 limit.
            """
            await ack()

            channel = body["channel_id"]
            user = body["user_id"]
            extra_context = body.get("text", "").strip()

            msg = await client.chat_postMessage(
                channel=channel,
                text=f"<@{user}> requested an ad review. :hourglass_flowing_sand: Pulling active ad performance data...",
            )

            query = (
                "Review all active ads and recommend which ones to pause to get the account "
                "back under the 250 ad limit. Prioritize pausing based on: zero leads + high spend, "
                "high CPL vs campaign average, and duplicate creatives. Protect ads still in the "
                "learning phase (under 14 days). Format your recommendations as a numbered pause list."
            )
            if extra_context:
                query += f"\n\nAdditional context from user: {extra_context}"

            await self.analyze_and_respond(
                client=client,
                channel=channel,
                thread_ts=msg["ts"],
                user_query=query,
                mention_ts=msg["ts"],
                force_ad_performance=True,
            )

        logger.info("slack_handlers_registered")

    # Maximum number of prior exchanges to carry in context per thread.
    # Each exchange = 1 user turn + 1 assistant turn.  Keeping this bounded
    # prevents token bloat while still giving Jarvis enough back-history to
    # follow a conversation without needing re-explanation.
    _MAX_HISTORY_TURNS = 10

    def get_thread_key(self, channel: str, thread_ts: Optional[str]) -> str:
        """
        Generate a unique key for thread context storage.

        Uses the Slack thread_ts when available so each thread gets its own
        isolated history.  Falls back to channel-level when no thread exists
        (e.g. top-level DMs or channel messages not in a thread).
        """
        if thread_ts:
            return f"{channel}:{thread_ts}"
        return f"{channel}:main"

    def get_thread_context(self, channel: str, thread_ts: Optional[str]) -> Dict[str, Any]:
        """Get or create context for a thread."""
        key = self.get_thread_key(channel, thread_ts)
        if key not in self._thread_contexts:
            self._thread_contexts[key] = {
                "uploaded_files": [],
                "user_context": [],
                "last_analysis": None,
                # Clean message history for this thread — stores dicts of
                # {"role": "user"|"assistant", "content": str} with the raw
                # user question and Jarvis's response (not the full data dump).
                "history": [],
            }
        logger.debug("get_thread_context", key=key,
                     history_turns=len(self._thread_contexts[key].get("history", [])) // 2)
        return self._thread_contexts[key]

    def _get_history(self, ctx: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return the bounded message history for this thread."""
        history = ctx.get("history", [])
        # Each turn is a user+assistant pair (2 items); keep last N turns
        max_messages = self._MAX_HISTORY_TURNS * 2
        return history[-max_messages:] if len(history) > max_messages else history

    def _append_history(
        self,
        ctx: Dict[str, Any],
        user_query: str,
        assistant_response: str,
    ) -> None:
        """Append a completed exchange to thread history."""
        history = ctx.setdefault("history", [])
        history.append({"role": "user", "content": user_query})
        history.append({"role": "assistant", "content": assistant_response})

    def add_context_to_thread(
        self,
        channel: str,
        thread_ts: Optional[str],
        context: str,
    ) -> None:
        """Add user-provided context to a thread."""
        ctx = self.get_thread_context(channel, thread_ts)
        ctx["user_context"].append(context)
        # Also inject it as a history exchange so Claude sees it as prior chat
        self._append_history(ctx, f"context: {context}", "Understood. I'll keep that in mind.")
        logger.info("context_added_to_thread", channel=channel, thread_ts=thread_ts)

    async def process_file_upload(
        self,
        client: AsyncWebClient,
        channel: str,
        thread_ts: Optional[str],
        file_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process an uploaded file and store in thread context."""
        filename = file_info.get("name", "unknown")

        if not self.file_processor.can_process(filename):
            logger.warning("unsupported_file_type", filename=filename)
            return {
                "type": "error",
                "filename": filename,
                "error": "Unsupported file type",
            }

        # Download file content
        file_url = file_info.get("url_private_download") or file_info.get("url_private")

        if not file_url:
            return {
                "type": "error",
                "filename": filename,
                "error": "Could not get file URL",
            }

        # Use httpx to download with proper auth
        async with httpx.AsyncClient() as http_client:
            file_response = await http_client.get(
                file_url,
                headers={"Authorization": f"Bearer {client.token}"},
            )
            file_content = file_response.content

        # Process the file
        processed = await self.file_processor.process_file(file_content, filename)

        # Store in thread context
        ctx = self.get_thread_context(channel, thread_ts)
        ctx["uploaded_files"].append(processed)

        logger.info(
            "file_processed_and_stored",
            filename=filename,
            channel=channel,
            thread_ts=thread_ts,
            context_key=self.get_thread_key(channel, thread_ts),
            total_files=len(ctx["uploaded_files"]),
            file_type=processed.get("type"),
        )

        return processed

    def _get_performance_data_from_dashboard(self) -> Dict[str, Any]:
        """
        Fetch performance data from the integrated Meta Ads service.

        This uses the same data source as the Schumacher Dashboard.
        """
        performance_data = {}

        try:
            # Get metrics overview (same as dashboard home page)
            metrics = self.meta_service.get_metrics_overview()
            performance_data["summary"] = {
                "total_spend": metrics.spend,
                "total_budget": 0,  # Budget tracking not yet implemented
                "impressions": metrics.impressions,
                "clicks": metrics.clicks,
                "leads": metrics.leads,
                "conversions": metrics.conversions,
                "cost_per_lead": metrics.cost_per_lead,
                "ctr": metrics.ctr,
                "cpc": metrics.cpc,
                "cpm": metrics.cpm,
                "active_ads": metrics.active_ads,
                "total_ads": metrics.total_ads,
                # Change metrics
                "spend_change": metrics.spend_change,
                "leads_change": metrics.leads_change,
                "cpl_change": metrics.cost_per_lead_change,
                # Segmented metrics
                "remarketing_cpl": metrics.remarketing_cpl,
                "prospecting_cpl": metrics.prospecting_cpl,
            }
        except Exception as e:
            logger.warning("metrics_overview_error", error=str(e))

        try:
            # Get campaign performance (same as dashboard campaigns page)
            campaigns = self.meta_service.get_campaigns()
            performance_data["campaigns"] = [
                {
                    "id": c.id,
                    "name": c.name,
                    "platform": "Meta",
                    "status": c.status,
                    "spend": c.spend,
                    "impressions": c.impressions,
                    "clicks": c.clicks,
                    "leads": c.leads,
                    "conversions": c.conversions,
                    "cost_per_lead": c.cost_per_lead,
                    "ctr": c.ctr,
                    "cpc": c.cpc,
                }
                for c in campaigns
            ]
        except Exception as e:
            logger.warning("campaigns_error", error=str(e))

        try:
            # Get trend data for context
            trends = self.meta_service.get_trend_data(days=7)
            if trends:
                total_spend = sum(t.spend for t in trends)
                total_leads = sum(t.leads for t in trends)
                performance_data["platforms"] = {
                    "Meta": {
                        "spend": total_spend,
                        "leads": total_leads,
                        "cpl": total_spend / total_leads if total_leads > 0 else 0,
                    }
                }
        except Exception as e:
            logger.warning("trends_error", error=str(e))

        return performance_data

    _AD_LIMIT_KEYWORDS = [
        "pause", "ad limit", "250", "over limit", "which ads", "ad review",
        "adreview", "too many ads", "cut ads", "reduce ads", "active ads",
    ]

    # Keywords that signal the user is asking about specific ads/creatives
    _AD_LOOKUP_KEYWORDS = [
        "ad ", "ads ", "creative", "batch", "batches", "specific ad",
        "this ad", "these ads", "the ad", "ad name", "ad called",
        "| car |", "| img |", "| bof |", "| mof |", "| tof |",
        "websiteleads", "learn more", "floorplan", "dreamhome",
        "modelhome", "winner +", "variant",
    ]

    def _is_ad_limit_query(self, query: str) -> bool:
        """Return True if the query is related to the ad limit / pausing ads."""
        q = query.lower()
        return any(kw in q for kw in self._AD_LIMIT_KEYWORDS)

    def _is_ad_lookup_query(self, query: str) -> bool:
        """
        Return True if the query references specific ads or creative names.
        This triggers ad-level data fetching so Jarvis can look up individual ads.
        """
        q = query.lower()
        # Pipe-delimited naming convention used in Schumacher ad names
        if q.count("|") >= 2:
            return True
        return any(kw in q for kw in self._AD_LOOKUP_KEYWORDS)

    def _extract_search_terms(self, query: str) -> List[str]:
        """
        Extract potential ad name fragments from the query to use as search filters.
        Splits on common delimiters and returns non-trivial tokens.
        """
        # Pull out pipe-delimited tokens if present (e.g. "Winner + floorplans | CAR | MOF")
        if "|" in query:
            # Take the full pipe-delimited expression as one search term per segment
            tokens = [t.strip() for t in query.replace("•", "").split("|")]
            # Also add the full ad name as a search term (everything before the last pipe segment)
            terms = [t for t in tokens if len(t) > 2]
            # Reconstruct likely full ad name segments (join adjacent tokens)
            if len(terms) >= 2:
                terms.append(" | ".join(terms[:3]))  # first 3 segments often = ad name
            return list(dict.fromkeys(terms))  # deduplicate preserving order

        # Otherwise use words longer than 4 chars that aren't stopwords
        stopwords = {"what", "how", "did", "does", "with", "about", "these", "those",
                     "that", "this", "from", "have", "show", "tell", "look", "give",
                     "their", "they", "them", "then", "than", "when", "where", "which"}
        words = re.findall(r"[A-Za-z0-9+]+", query)
        return [w for w in words if len(w) > 4 and w.lower() not in stopwords]

    # ── Loading bar helpers ───────────────────────────────────────────────────

    _BAR_FILL = "█"
    _BAR_EMPTY = "░"
    _BAR_WIDTH = 10

    def _render_status(
        self,
        steps: List[tuple],   # list of (label, state) where state: "done"|"active"|"pending"
        date_range: Optional[Any] = None,
    ) -> str:
        """
        Render an animated status block showing each pipeline stage.

        Each step is rendered as a bar segment:
          ████████░░  75%  ✅ Campaign data  (done)
          ██░░░░░░░░  20%  ⏳ Ad-level data  (active — animated dots)
                           ○ Thinking…       (pending)
        """
        done_count = sum(1 for _, s in steps if s == "done")
        total = len(steps)
        pct = int((done_count / total) * 100) if total else 0
        filled = int((done_count / total) * self._BAR_WIDTH) if total else 0

        bar = self._BAR_FILL * filled + self._BAR_EMPTY * (self._BAR_WIDTH - filled)

        date_str = ""
        if date_range:
            date_str = f"  `{date_range.start_date} → {date_range.end_date}`"

        lines = [f"`{bar}` {pct}%{date_str}", ""]

        for label, state in steps:
            if state == "done":
                lines.append(f"✅  {label}")
            elif state == "active":
                lines.append(f"⏳  {label}")
            else:
                lines.append(f"○  _{label}_")

        return "\n".join(lines)

    async def _update_status(
        self,
        client: AsyncWebClient,
        channel: str,
        ts: str,
        steps: List[tuple],
        date_range: Optional[Any] = None,
    ) -> None:
        """Push a status update to the loading message."""
        try:
            await client.chat_update(
                channel=channel,
                ts=ts,
                text=self._render_status(steps, date_range),
            )
        except Exception:
            pass  # Never let a status update crash the pipeline

    # ── Main analysis handler ─────────────────────────────────────────────────

    async def analyze_and_respond(
        self,
        client: AsyncWebClient,
        channel: str,
        thread_ts: Optional[str],
        user_query: str,
        mention_ts: str,
        force_ad_performance: bool = False,
    ) -> None:
        """Perform analysis and respond with results."""
        reply_ts = thread_ts or mention_ts

        # Resolve date range up front so the status bar can show it immediately
        date_range = parse_date_range_from_query(user_query)
        if date_range is None:
            date_range = DateRange.this_month()
            logger.info("no_date_range_in_query_defaulting_to_mtd")

        account_id = get_account_id_from_query(user_query)

        # Decide which extra fetch stages we'll need
        needs_ad_limit = force_ad_performance or self._is_ad_limit_query(user_query)
        needs_ad_lookup = (not needs_ad_limit) and self._is_ad_lookup_query(user_query)

        # Build the step list for the status bar
        base_steps: List[tuple] = [
            ("Account & campaign data", "active"),
        ]
        if needs_ad_limit:
            base_steps.append(("Active ads inventory", "pending"))
        if needs_ad_lookup:
            base_steps.append(("Ad-level creative data", "pending"))
        base_steps.append(("Thinking…", "pending"))

        # Post the initial loading message
        thinking_msg = await client.chat_postMessage(
            channel=channel,
            thread_ts=reply_ts,
            text=self._render_status(base_steps, date_range),
        )
        ts = thinking_msg["ts"]

        def steps_with(updates: dict) -> List[tuple]:
            """Return updated step list with state overrides by label."""
            return [(lbl, updates.get(lbl, st)) for lbl, st in base_steps]

        try:
            live_api_context = None
            live_data_success = False

            logger.info(
                "fetching_live_data",
                date_range=f"{date_range.start_date} to {date_range.end_date}",
                query=user_query[:50]
            )

            # ── Stage 1: Account summary + campaign breakdown + active ad count ─
            # All three fetched in parallel so Jarvis always has the exact
            # active ad count in every response — no guessing or asking.
            try:
                insights_data, campaign_data, active_count_data = await asyncio.gather(
                    self.live_api.get_meta_account_insights(
                        account_id=account_id,
                        date_range=date_range,
                        level="account"
                    ),
                    self.live_api.get_meta_campaigns(
                        account_id=account_id,
                        date_range=date_range
                    ),
                    self.live_api.get_meta_active_ads_count(account_id),
                )

                if insights_data.get("success"):
                    live_api_context = self.live_api.format_insights_for_context(insights_data)
                    live_data_success = True
                    if campaign_data.get("success"):
                        live_api_context += "\n\n" + self.live_api.format_campaigns_for_context(campaign_data)

                    # Always append the real-time active ad count
                    if active_count_data.get("success"):
                        active_count = active_count_data["active_ads"]
                        headroom = 250 - active_count
                        live_api_context += (
                            f"\n\n=== ACTIVE AD COUNT (real-time, today) ===\n"
                            f"Delivering ads right now: {active_count} / 250 limit\n"
                            f"Headroom before limit: {headroom} ads\n"
                            f"Status: {'⚠️ OVER LIMIT' if headroom < 0 else ('🟡 CLOSE TO LIMIT' if headroom < 20 else '🟢 OK')}"
                        )

                    logger.info(
                        "live_data_fetched_successfully",
                        account_id=account_id,
                        date_range=f"{date_range.start_date} to {date_range.end_date}",
                        campaign_count=len(campaign_data.get("campaigns", [])),
                        active_ads=active_count_data.get("active_ads"),
                    )
                else:
                    error_msg = insights_data.get("error", "Unknown error")
                    logger.warning("live_data_fetch_failed", error=error_msg)
                    live_api_context = (
                        f"=== DATE RANGE REQUESTED ===\n"
                        f"Period: {date_range.start_date} to {date_range.end_date}\n"
                        f"Account: {account_id}\n"
                        f"Note: Live data fetch failed ({error_msg}). Falling back to cached data.\n"
                    )
            except Exception as e:
                logger.warning("live_data_fetch_error", error=str(e))
                live_api_context = (
                    f"=== DATE RANGE REQUESTED ===\n"
                    f"Period: {date_range.start_date} to {date_range.end_date}\n"
                    f"Note: Could not fetch live data ({str(e)}). Falling back to cached data.\n"
                )

            # Mark stage 1 done, activate next stage
            if needs_ad_limit:
                await self._update_status(client, channel, ts, steps_with({
                    "Account & campaign data": "done",
                    "Active ads inventory": "active",
                }), date_range)
            elif needs_ad_lookup:
                await self._update_status(client, channel, ts, steps_with({
                    "Account & campaign data": "done",
                    "Ad-level creative data": "active",
                }), date_range)
            else:
                await self._update_status(client, channel, ts, steps_with({
                    "Account & campaign data": "done",
                    "Thinking…": "active",
                }), date_range)

            logger.info("live_data_context_built", has_context=bool(live_api_context), success=live_data_success)

            if live_data_success:
                performance_data = {}
            else:
                performance_data = self._get_performance_data_from_dashboard()

            # Get thread context
            ctx = self.get_thread_context(channel, thread_ts)

            logger.info(
                "analysis_context_check",
                channel=channel,
                thread_ts=thread_ts,
                context_key=self.get_thread_key(channel, thread_ts),
                files_in_context=len(ctx["uploaded_files"]),
                user_context_items=len(ctx["user_context"]),
            )

            # Build additional context from uploaded files and user context
            additional_context_parts = []

            if ctx["user_context"]:
                additional_context_parts.append(
                    "User-provided context:\n" + "\n".join(f"- {c}" for c in ctx["user_context"])
                )

            for file_data in ctx["uploaded_files"]:
                file_type = file_data.get("type", "unknown")
                filename = file_data.get("filename", "unknown")

                if file_type in ("performance_data", "tabular"):
                    columns = file_data.get("columns", [])
                    row_count = file_data.get("row_count", 0)
                    data = file_data.get("data", [])
                    additional_context_parts.append(
                        f"=== UPLOADED FILE: '{filename}' ===\n"
                        f"Type: {file_type}\n"
                        f"Columns: {', '.join(columns)}\n"
                        f"Total rows: {row_count}\n"
                    )
                    if data:
                        if len(data) <= 50:
                            additional_context_parts.append(f"Complete data:\n{data}")
                        else:
                            additional_context_parts.append(f"First 20 rows:\n{data[:20]}")
                            additional_context_parts.append(f"Last 10 rows:\n{data[-10:]}")

                elif file_type == "spreadsheet":
                    sheets = file_data.get("sheets", {})
                    sheet_names = file_data.get("sheet_names", [])
                    additional_context_parts.append(
                        f"=== UPLOADED SPREADSHEET: '{filename}' ===\n"
                        f"Sheets: {', '.join(sheet_names)}\n"
                    )
                    for sheet_name, sheet_data in sheets.items():
                        if sheet_data:
                            additional_context_parts.append(
                                f"\n--- Sheet '{sheet_name}' ({len(sheet_data)} rows) ---\n"
                                f"{sheet_data[:20] if len(sheet_data) > 20 else sheet_data}"
                            )

                elif file_type == "document":
                    text_content = file_data.get("text_content", "")
                    additional_context_parts.append(
                        f"=== UPLOADED DOCUMENT: '{filename}' ===\n"
                        f"Format: {file_data.get('format', 'unknown')}\n"
                        f"Content:\n{text_content[:4000]}"
                    )

                elif file_type == "json":
                    json_data = file_data.get("data", {})
                    additional_context_parts.append(
                        f"=== UPLOADED JSON: '{filename}' ===\n"
                        f"Data:\n{json_data}"
                    )

                elif file_type == "image":
                    additional_context_parts.append(
                        f"=== UPLOADED IMAGE: '{filename}' ===\n"
                        f"Format: {file_data.get('format', 'unknown')}\n"
                        f"Size: {file_data.get('size_bytes', 0) / 1024:.1f} KB\n"
                        f"(Image content available for visual analysis)"
                    )

                else:
                    additional_context_parts.append(
                        f"=== UPLOADED FILE: '{filename}' (type: {file_type}) ===\n"
                        f"Data: {str(file_data)[:2000]}"
                    )

            # ── Stage 2a: Active ads inventory (pause/limit queries) ──────────
            if needs_ad_limit:
                try:
                    ad_perf_data = await self.live_api.get_meta_active_ads_with_performance(account_id)
                    if ad_perf_data.get("success"):
                        ad_perf_context = self.live_api.format_active_ads_for_jarvis(ad_perf_data)
                        additional_context_parts.insert(0, ad_perf_context)
                        logger.info("ad_performance_context_injected", ad_count=ad_perf_data.get("total_active_ads"))
                except Exception as e:
                    logger.warning("ad_performance_fetch_failed", error=str(e))

                await self._update_status(client, channel, ts, steps_with({
                    "Account & campaign data": "done",
                    "Active ads inventory": "done",
                    "Thinking…": "active",
                }), date_range)

            # ── Stage 2b: Ad-level creative lookup ────────────────────────────
            elif needs_ad_lookup:
                try:
                    search_terms = self._extract_search_terms(user_query)
                    logger.info("ad_lookup_triggered", search_terms=search_terms)

                    ad_lookup_data = await self.live_api.get_meta_ads_by_date_range(
                        account_id=account_id,
                        date_range=date_range,
                        search_terms=search_terms if search_terms else None,
                    )
                    if ad_lookup_data.get("success"):
                        ad_lookup_context = self.live_api.format_ads_for_context(ad_lookup_data)
                        additional_context_parts.insert(0, ad_lookup_context)
                        logger.info(
                            "ad_lookup_context_injected",
                            ad_count=ad_lookup_data.get("total_ads"),
                            search_terms=search_terms,
                        )
                    else:
                        logger.warning("ad_lookup_failed", error=ad_lookup_data.get("error"))
                except Exception as e:
                    logger.warning("ad_lookup_fetch_failed", error=str(e))

                await self._update_status(client, channel, ts, steps_with({
                    "Account & campaign data": "done",
                    "Ad-level creative data": "done",
                    "Thinking…": "active",
                }), date_range)

            # Add live API data to context
            if live_api_context:
                additional_context_parts.insert(0, live_api_context)

            additional_context = "\n\n".join(additional_context_parts) if additional_context_parts else None

            # ── Stage 3: AI analysis ──────────────────────────────────────────
            # Pull the clean Q&A history for this specific thread so Jarvis
            # has full conversational context without re-explanation.
            thread_history = self._get_history(ctx)

            analysis = await self.analyst.analyze_performance(
                performance_data=performance_data,
                user_query=user_query,
                additional_context=additional_context,
                conversation_history=thread_history,
            )

            # Store this exchange back into thread history as clean Q&A
            # (just the raw question + Jarvis's answer — not the data dumps)
            self._append_history(ctx, user_query, analysis)
            ctx["last_analysis"] = analysis

            budget_table = parse_budget_table_from_response(analysis)
            slack_response = clean_response_for_slack(analysis)

            # Replace the loading bar with the final answer
            await client.chat_update(
                channel=channel,
                ts=ts,
                text=slack_response,
            )

            # If we have a budget table, generate and upload CSV
            if budget_table:
                markdown_table, csv_buffer = generate_reports(budget_table)

                # Upload CSV as a file
                csv_bytes = csv_buffer.getvalue().encode("utf-8")

                await client.files_upload_v2(
                    channel=channel,
                    thread_ts=reply_ts,
                    content=csv_bytes,
                    filename="budget_allocation.csv",
                    title="Budget Allocation Recommendations",
                    initial_comment=":chart_with_upwards_trend: Here's the budget allocation as a downloadable CSV:",
                )

                logger.info("csv_uploaded", channel=channel, rows=len(budget_table))

        except Exception as e:
            logger.error("analysis_error", error=str(e), error_type=type(e).__name__)
            await client.chat_update(
                channel=channel,
                ts=ts,
                text=f":x: Sorry, I encountered an error while analyzing: {str(e)}",
            )

    async def handle_help_command(
        self,
        client: AsyncWebClient,
        channel: str,
        thread_ts: Optional[str],
    ) -> None:
        """Send help information to the user."""
        help_text = """*JARVIS - Paid Media Intelligence* :robot_face:

At your service. I analyze paid media performance and optimize budget allocation, integrated with the Schumacher Dashboard.

*How to engage me:*
- Mention me with a question: `@Jarvis How should I reallocate the remaining $50k?`
- Upload files directly - I can process them automatically!
- Add context: `@Jarvis context: Focus on lead generation this month`

*File Processing - I can analyze:* :page_facing_up:
- *CSV files* - Performance reports, exports from ad platforms
- *Excel files* (.xlsx, .xls) - Multi-sheet workbooks with data
- *PDF documents* - Reports, presentations, strategy briefs
- *Word documents* (.docx) - Briefs, notes, strategy docs
- *PowerPoint slides* (.pptx) - Presentations and slide decks
- *Images* (.png, .jpg, .gif) - Screenshots, charts, visuals
- *Text/Markdown* (.txt, .md) - Notes and documentation
- *JSON files* - Data exports, API responses

Just upload any of these files and I'll automatically extract and analyze the content. Then mention me with your question!

*My capabilities:*
- Real-time Meta Ads performance analysis with custom date ranges
- File upload processing and analysis
- Strategic budget reallocation with reasoning
- Downloadable CSV reports
- Contextual memory throughout our conversation

*Date Ranges I support:* :calendar:
- "last 7 days", "last 14 days", "last 30 days", "last 60 days", "last 90 days"
- "this month" or "MTD" (month to date)
- "last month" (previous calendar month)
- "YTD" (year to date)
- Specific months like "January", "February 2026"

*Example queries:*
- "Analyze current campaign performance and suggest optimizations"
- "How did we perform last 7 days?"
- "Show me January performance data"
- "Compare MTD vs last month"
- "How should I split the remaining $25k budget?"
- "Which campaigns should I pause?"
- _(upload a file)_ "Analyze this report and identify optimization opportunities"
"""
        await client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=help_text,
        )
