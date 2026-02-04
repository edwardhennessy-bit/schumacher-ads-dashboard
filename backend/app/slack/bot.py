"""JARVIS Slack Bot - Paid Media Intelligence Agent.

This bot integrates with the Schumacher Dashboard to provide
AI-powered paid media analysis via Slack.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
import httpx
import structlog

from .analyst import AnthropicAnalyst
from .file_processor import FileProcessor
from .utils import parse_budget_table_from_response, clean_response_for_slack, generate_reports
from app.services.meta_ads import MetaAdsService

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

            # Handle direct messages (not in channels)
            elif channel_type == "im":
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

        logger.info("slack_handlers_registered")

    def get_thread_key(self, channel: str, thread_ts: Optional[str]) -> str:
        """Generate a unique key for thread context storage."""
        return f"{channel}:{thread_ts or 'main'}"

    def get_thread_context(self, channel: str, thread_ts: Optional[str]) -> Dict[str, Any]:
        """Get or create context for a thread."""
        key = self.get_thread_key(channel, thread_ts)
        if key not in self._thread_contexts:
            self._thread_contexts[key] = {
                "uploaded_files": [],
                "user_context": [],
                "last_analysis": None,
            }
        return self._thread_contexts[key]

    def add_context_to_thread(
        self,
        channel: str,
        thread_ts: Optional[str],
        context: str,
    ) -> None:
        """Add user-provided context to a thread."""
        ctx = self.get_thread_context(channel, thread_ts)
        ctx["user_context"].append(context)
        self.analyst.add_context(context)
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

        logger.info("file_processed_and_stored", filename=filename, channel=channel)

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

    async def analyze_and_respond(
        self,
        client: AsyncWebClient,
        channel: str,
        thread_ts: Optional[str],
        user_query: str,
        mention_ts: str,
    ) -> None:
        """Perform analysis and respond with results."""
        reply_ts = thread_ts or mention_ts

        # Send initial "analyzing" message
        thinking_msg = await client.chat_postMessage(
            channel=channel,
            thread_ts=reply_ts,
            text=":hourglass_flowing_sand: Analyzing your request...",
        )

        try:
            # Fetch performance data from the integrated dashboard service
            performance_data = self._get_performance_data_from_dashboard()

            if not performance_data:
                logger.info("no_dashboard_data", message="Using file uploads only")

            # Get thread context
            ctx = self.get_thread_context(channel, thread_ts)

            # Build additional context from uploaded files and user context
            additional_context_parts = []

            if ctx["user_context"]:
                additional_context_parts.append(
                    "User-provided context:\n" + "\n".join(f"- {c}" for c in ctx["user_context"])
                )

            for file_data in ctx["uploaded_files"]:
                if file_data.get("type") == "performance_data":
                    additional_context_parts.append(
                        f"Uploaded file '{file_data['filename']}':\n"
                        f"Columns: {', '.join(file_data['columns'])}\n"
                        f"Row count: {file_data['row_count']}\n"
                        f"Sample data provided."
                    )
                    # Add a sample of the data
                    if file_data.get("data"):
                        sample = file_data["data"][:5]
                        additional_context_parts.append(f"Sample rows: {sample}")
                elif file_data.get("type") == "document":
                    additional_context_parts.append(
                        f"Uploaded document '{file_data['filename']}':\n"
                        f"{file_data.get('text_content', '')[:2000]}"
                    )

            additional_context = "\n\n".join(additional_context_parts) if additional_context_parts else None

            # Get AI analysis
            analysis = await self.analyst.analyze_performance(
                performance_data=performance_data,
                user_query=user_query,
                additional_context=additional_context,
            )

            # Store analysis in context
            ctx["last_analysis"] = analysis

            # Parse budget table for CSV generation
            budget_table = parse_budget_table_from_response(analysis)

            # Clean response for Slack
            slack_response = clean_response_for_slack(analysis)

            # Update the thinking message with the analysis
            await client.chat_update(
                channel=channel,
                ts=thinking_msg["ts"],
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
                ts=thinking_msg["ts"],
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
- Real-time Meta Ads performance analysis (from Schumacher Dashboard)
- File upload processing and analysis
- Strategic budget reallocation with reasoning
- Downloadable CSV reports
- Contextual memory throughout our conversation

*Example queries:*
- "Analyze current campaign performance and suggest optimizations"
- "How should I split the remaining $25k budget?"
- "Which campaigns should I pause?"
- "Compare remarketing vs prospecting CPL"
- _(upload a file)_ "Analyze this report and identify optimization opportunities"
"""
        await client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=help_text,
        )
