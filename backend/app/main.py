import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import structlog

from app.config import get_settings
from app.routers import metrics_router, campaigns_router, audits_router, reports_router, chat_router
from app.routers.gateway import router as gateway_router

settings = get_settings()

# Configure structured logging
def setup_logging(log_level: str = "info") -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

setup_logging(settings.log_level)
logger = structlog.get_logger(__name__)

# Global reference to Slack bot handler
slack_handler: Optional[AsyncSocketModeHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - start/stop Slack bot with the server."""
    global slack_handler

    # Startup
    if settings.enable_slack_bot and settings.is_slack_bot_configured():
        try:
            from app.slack.bot import SlackBot

            logger.info("initializing_jarvis_bot")

            bot = SlackBot(
                slack_bot_token=settings.slack_bot_token,
                slack_signing_secret=settings.slack_signing_secret,
                slack_app_token=settings.slack_app_token,
                anthropic_api_key=settings.anthropic_api_key,
            )

            slack_handler = AsyncSocketModeHandler(bot.app, settings.slack_app_token)

            # Start the Slack bot in a background task
            asyncio.create_task(slack_handler.start_async())

            logger.info("jarvis_bot_started", mode="socket_mode")
            print("JARVIS Slack bot is online and ready to serve.")

        except Exception as e:
            logger.error("jarvis_bot_startup_failed", error=str(e))
            print(f"Warning: Could not start JARVIS Slack bot: {e}")
    else:
        if settings.enable_slack_bot:
            logger.warning("jarvis_bot_not_configured",
                         message="Slack bot credentials not configured. Bot will not start.")
            print("Note: JARVIS Slack bot not configured. Set SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, and SLACK_APP_TOKEN to enable.")

    yield

    # Shutdown
    if slack_handler:
        try:
            await slack_handler.close_async()
            logger.info("jarvis_bot_stopped")
        except Exception as e:
            logger.error("jarvis_bot_shutdown_error", error=str(e))


app = FastAPI(
    title="Schumacher Ads Dashboard API",
    description="Backend API for Schumacher Homes Paid Media Intelligence Dashboard with JARVIS Slack Bot",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(metrics_router)
app.include_router(campaigns_router)
app.include_router(audits_router)
app.include_router(reports_router)
app.include_router(gateway_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "name": "Schumacher Ads Dashboard API",
        "version": "0.2.0",
        "status": "running",
        "mode": "demo" if not settings.meta_ad_account_id else "live",
        "jarvis_enabled": settings.enable_slack_bot and settings.is_slack_bot_configured(),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "jarvis_bot": "running" if slack_handler else "disabled",
    }


@app.get("/api/status")
async def api_status():
    """Get API status and configuration info."""
    return {
        "meta_connected": bool(settings.meta_ad_account_id),
        "claude_connected": bool(settings.anthropic_api_key),
        "slack_webhook_connected": bool(settings.slack_webhook_url),
        "jarvis_bot_configured": settings.is_slack_bot_configured(),
        "jarvis_bot_enabled": settings.enable_slack_bot,
        "jarvis_bot_running": slack_handler is not None,
        "database_url": settings.database_url.split("///")[0] + "///...",
    }
