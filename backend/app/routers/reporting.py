"""
Reporting router for generating slide decks, docs, and email drafts.
"""

import structlog
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.routers.auth import get_google_auth
from app.services.report_data import ReportDataCollector
from app.services.report_insights import ReportInsightsService
from app.services.slides_generator import SlidesGenerator
from app.services.docs_generator import DocsGenerator
from app.services.email_generator import EmailGenerator
from app.services.google_ads_api import GoogleAdsService
from app.services.mcp_client import MCPGatewayClient

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports_v2"])
settings = get_settings()

# ── Report history (in-memory for now, can move to DB later) ──
_report_history: list = []


# ── Request / response models ────────────────────────────────

class MonthlyReviewRequest(BaseModel):
    month: Optional[int] = None  # defaults to last month
    year: Optional[int] = None


class WeeklyAgendaRequest(BaseModel):
    week_of: Optional[str] = None  # YYYY-MM-DD, defaults to current week


class WeeklyEmailRequest(BaseModel):
    week_of: Optional[str] = None


class ReportResult(BaseModel):
    id: str = ""
    url: str = ""
    title: str = ""
    report_type: str = ""
    created_at: str = ""


class EmailDraftResult(BaseModel):
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    created_at: str = ""


# ── Helper to build services ─────────────────────────────────

def _build_data_collector() -> ReportDataCollector:
    """Build a report data collector with available services."""
    mcp_client = MCPGatewayClient(
        gateway_url=settings.gateway_url,
        token=settings.gateway_token,
    )
    google_ads = GoogleAdsService(mcp_client=mcp_client)
    return ReportDataCollector(
        google_ads_service=google_ads,
        mcp_client=mcp_client,
    )


def _build_insights() -> Optional[ReportInsightsService]:
    """Build Claude insights service if configured."""
    if settings.anthropic_api_key:
        return ReportInsightsService(api_key=settings.anthropic_api_key)
    return None


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/monthly-review", response_model=ReportResult)
async def generate_monthly_review(req: MonthlyReviewRequest):
    """Generate a Monthly Performance Review Google Slides deck."""
    google_auth = get_google_auth()
    if not google_auth.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Google not connected. Please authenticate via /api/auth/google/start first.",
        )

    # Default to previous month
    today = date.today()
    month = req.month or (today.month - 1 if today.month > 1 else 12)
    year = req.year or (today.year if today.month > 1 else today.year - 1)

    logger.info("generating_monthly_review", month=month, year=year)

    # 1. Collect data
    collector = _build_data_collector()
    data = await collector.collect_monthly_data(month, year)

    # 2. Generate AI insights
    insights_svc = _build_insights()
    insights = {}
    if insights_svc:
        insights = await insights_svc.generate_monthly_insights(data)

    # 3. Create Google Slides
    creds = google_auth.get_credentials()
    slides_gen = SlidesGenerator(creds)
    result = await slides_gen.create_monthly_review(data, insights)

    # 4. Record history
    record = ReportResult(
        id=result["id"],
        url=result["url"],
        title=result["title"],
        report_type="monthly_review",
        created_at=datetime.utcnow().isoformat(),
    )
    _report_history.insert(0, record.model_dump())

    return record


@router.post("/weekly-agenda", response_model=ReportResult)
async def generate_weekly_agenda(req: WeeklyAgendaRequest):
    """Generate a Weekly Agenda Google Doc."""
    google_auth = get_google_auth()
    if not google_auth.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Google not connected. Please authenticate via /api/auth/google/start first.",
        )

    week_of = req.week_of or date.today().isoformat()

    logger.info("generating_weekly_agenda", week_of=week_of)

    # 1. Collect data
    collector = _build_data_collector()
    data = await collector.collect_weekly_data(week_of)

    # 2. Generate AI insights
    insights_svc = _build_insights()
    insights = {}
    if insights_svc:
        insights = await insights_svc.generate_weekly_insights(data)

    # 3. Create Google Doc
    creds = google_auth.get_credentials()
    docs_gen = DocsGenerator(creds)
    result = await docs_gen.create_weekly_agenda(data, insights, week_of)

    # 4. Record history
    record = ReportResult(
        id=result["id"],
        url=result["url"],
        title=result["title"],
        report_type="weekly_agenda",
        created_at=datetime.utcnow().isoformat(),
    )
    _report_history.insert(0, record.model_dump())

    return record


@router.post("/weekly-email", response_model=EmailDraftResult)
async def generate_weekly_email(req: WeeklyEmailRequest):
    """Generate a weekly client update email draft."""
    week_of = req.week_of or date.today().isoformat()

    logger.info("generating_weekly_email", week_of=week_of)

    # 1. Collect data
    collector = _build_data_collector()
    data = await collector.collect_weekly_data(week_of)

    # 2. Generate AI insights
    insights_svc = _build_insights()
    insights = {}
    if insights_svc:
        insights = await insights_svc.generate_weekly_insights(data)

    # 3. Generate email
    email_gen = EmailGenerator()
    result = await email_gen.generate_weekly_email(data, insights, week_of)

    # 4. Record history
    record_data = {
        "id": "",
        "url": "",
        "title": result["subject"],
        "report_type": "weekly_email",
        "created_at": datetime.utcnow().isoformat(),
    }
    _report_history.insert(0, record_data)

    return EmailDraftResult(
        subject=result["subject"],
        body_html=result["body_html"],
        body_text=result["body_text"],
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/history")
async def get_report_history():
    """Get list of previously generated reports."""
    return _report_history[:50]
