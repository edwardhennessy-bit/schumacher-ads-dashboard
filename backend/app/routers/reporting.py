"""
Reporting router for generating slide decks, docs, and email drafts.
"""

import json
import os
import structlog
from datetime import date, datetime
from typing import Optional

import anthropic
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
        gateway_token=settings.gateway_token,
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


# ── Weekly KPI Section ────────────────────────────────────────

class WeeklyKpiRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD


class WeeklyKpiResponse(BaseModel):
    text: str                    # The formatted KPI block text (copy-paste ready)
    period_label: str            # e.g. "Feb 1-22"
    meta_spend: float = 0
    google_spend: float = 0
    microsoft_spend: float = 0
    total_spend: float = 0
    google_leads: int = 0
    google_opportunities: int = 0
    google_lead_to_opp_pct: float = 0
    meta_leads: int = 0
    meta_remarketing_cpa: float = 0
    meta_prospecting_cpa: float = 0
    bing_cpa: float = 0
    bing_leads: int = 0


def _fmt_date_label(start: str, end: str) -> str:
    """Format a human-readable period label like 'Feb 1-22'."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if s.month == e.month and s.year == e.year:
        return f"{months[s.month - 1]} {s.day}-{e.day}"
    return f"{months[s.month - 1]} {s.day} - {months[e.month - 1]} {e.day}"


def _load_microsoft_data(start_date: str, end_date: str) -> dict:
    """Load Microsoft scraped data for the given date range."""
    data_file = os.path.join(
        os.path.dirname(__file__), "../../../data/microsoft_scraped.json"
    )
    if not os.path.exists(data_file):
        return {}
    try:
        with open(data_file) as f:
            all_data = json.load(f)
        range_key = f"{start_date}__{end_date}"
        return all_data.get(range_key) or all_data.get("latest") or {}
    except Exception:
        return {}


def _google_status(leads: int, opps: int, lead_to_opp_pct: float) -> str:
    """Determine Google status vs. targets (>950 leads/month AND ≥10% L2O)."""
    # Scale targets to partial month (compare daily rate or just check actuals)
    leads_on_track = leads >= 0  # always include; status is qualitative
    opp_rate_on_track = lead_to_opp_pct >= 10.0
    leads_threshold = leads > 500  # rough mid-month threshold
    if leads_threshold and opp_rate_on_track:
        return "On Track"
    return "Off Track"


def _meta_status(remarketing_cpa: float, prospecting_cpa: float) -> str:
    """Determine Meta status vs. targets."""
    if remarketing_cpa == 0 and prospecting_cpa == 0:
        return "Off Track"
    remarketing_ok = remarketing_cpa <= 35 or remarketing_cpa == 0
    prospecting_ok = prospecting_cpa <= 100 or prospecting_cpa == 0
    if remarketing_ok and prospecting_ok:
        return "On Track"
    return "Off Track"


def _bing_status(cpa: float) -> str:
    """Determine Bing status vs. target (<$55 CPA)."""
    if cpa == 0:
        return "No Data"
    return "On Track" if cpa <= 55 else "Off Track"


def _extract_action_value(actions: list, action_type: str) -> int:
    """Extract value for a specific action type from Meta API actions list."""
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == action_type:
            return int(float(action.get("value", 0)))
    return 0


def _segment_campaign_cpls(campaigns: list) -> dict:
    """Segment Meta campaigns into remarketing and prospecting buckets."""
    remarketing_spend = 0.0
    remarketing_leads = 0
    prospecting_spend = 0.0
    prospecting_leads = 0

    for camp in campaigns:
        name = camp.get("campaign_name", "").lower()
        spend = float(camp.get("spend", 0))
        leads = _extract_action_value(camp.get("actions", []), "lead")

        if "remarketing" in name:
            remarketing_spend += spend
            remarketing_leads += leads
        elif "visit" not in name:
            prospecting_spend += spend
            prospecting_leads += leads

    return {
        "remarketing_cpl": round(remarketing_spend / remarketing_leads, 2) if remarketing_leads > 0 else 0,
        "remarketing_leads": remarketing_leads,
        "prospecting_cpl": round(prospecting_spend / prospecting_leads, 2) if prospecting_leads > 0 else 0,
        "prospecting_leads": prospecting_leads,
    }


@router.post("/weekly-kpi-section", response_model=WeeklyKpiResponse)
async def generate_weekly_kpi_section(req: WeeklyKpiRequest):
    """
    Generate the Performance Metrics & KPIs section for the weekly agenda doc.
    Fetches live Meta + Google data and stored Microsoft data, then uses Claude
    to produce a copy-paste ready text block matching the standard template.
    """
    import asyncio as _asyncio
    from app.services.live_api import LiveAPIService, DateRange as LiveDateRange

    dr = LiveDateRange(start_date=req.start_date, end_date=req.end_date)
    period_label = _fmt_date_label(req.start_date, req.end_date)

    # ── 1. Fetch Meta via LiveAPIService (same path as metrics.py) ────────
    meta_spend = 0.0
    meta_leads = 0
    meta_remarketing_cpa = 0.0
    meta_prospecting_cpa = 0.0

    if settings.meta_access_token:
        try:
            live_svc = LiveAPIService(meta_access_token=settings.meta_access_token)
            account_id = settings.meta_ad_account_id or "act_142003632"

            meta_result, campaign_result = await _asyncio.gather(
                live_svc.get_meta_account_insights(account_id, dr),
                live_svc.get_meta_campaigns(account_id, dr),
            )

            if meta_result.get("success") and meta_result.get("data"):
                row = meta_result["data"][0]
                meta_spend = float(row.get("spend", 0))
                meta_leads = _extract_action_value(row.get("actions", []), "lead")

            if campaign_result.get("success"):
                segmented = _segment_campaign_cpls(campaign_result.get("campaigns", []))
                meta_remarketing_cpa = segmented["remarketing_cpl"]
                meta_prospecting_cpa = segmented["prospecting_cpl"]

        except Exception as e:
            logger.warning("meta_live_fetch_error", error=str(e))

    # ── 2. Fetch Google + Microsoft data ──────────────────────────────────
    collector = _build_data_collector()
    google_raw = await collector._fetch_google_overview(dr)
    ms_raw = _load_microsoft_data(req.start_date, req.end_date)

    # ── 3. Extract remaining metrics ─────────────────────────────────────
    google_spend = float(google_raw.get("spend", 0)) if google_raw else 0
    google_leads = int(google_raw.get("leads", 0)) if google_raw else 0
    google_opps = int(google_raw.get("opportunities", 0)) if google_raw else 0
    google_l2o = round(google_opps / google_leads * 100, 1) if google_leads > 0 else 0.0

    ms_spend = float(ms_raw.get("spend", 0)) if ms_raw else 0
    ms_leads = int(ms_raw.get("leads", 0)) if ms_raw else 0
    ms_cpa = float(ms_raw.get("cost_per_lead", 0)) if ms_raw else 0

    total_spend = meta_spend + google_spend + ms_spend

    # ── 3. Determine statuses ─────────────────────────────────
    google_status = _google_status(google_leads, google_opps, google_l2o)
    meta_status = _meta_status(meta_remarketing_cpa, meta_prospecting_cpa)
    bing_status = _bing_status(ms_cpa)

    # ── 4. Format the KPI block with Claude ───────────────────
    if settings.anthropic_api_key:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        data_context = f"""
Reporting Period: {period_label}

SPEND:
- Total Paid Media Spend: ${total_spend:,.2f}
- Google: ${google_spend:,.2f}
- Meta: ${meta_spend:,.2f}
- Microsoft/Bing: ${ms_spend:,.2f}

GOOGLE ADS:
- Target: Lead Volume >950/month AND Lead to Opp % ≥10%
- Leads: {google_leads:,}
- Opportunities: {google_opps:,}
- Lead to Opp Rate: {google_l2o:.1f}%
- Status Assessment: {google_status}

META ADS:
- Target: Prospecting CPA <$100, Remarketing CPA <$35
- Leads: {meta_leads:,}
- Remarketing CPA: ${meta_remarketing_cpa:,.2f}
- Prospecting CPA: ${meta_prospecting_cpa:,.2f}
- Status Assessment: {meta_status}

BING / MICROSOFT ADS:
- Target: CPA <$55
- Leads/Conversions: {ms_leads:,}
- CPA: ${ms_cpa:,.2f}
- Status Assessment: {bing_status}
"""

        prompt = f"""You are a paid media analyst at an agency. Generate the "Performance Metrics & KPIs" section for a weekly client agenda document for Schumacher Homes (a national home builder).

Use EXACTLY this template format — do not change the structure, labels, or bullet indentation. Fill in all the $ and % values from the data provided. For the Status field, use "On Track" or "Off Track" based on the assessment provided. Keep any qualitative notes brief and factual.

TEMPLATE:
Performance Metrics & KPIs
Reporting Period: {period_label}
Performance Notes
Primary KPI Tracking / Channel
* Paid Media
   * Total Paid Media Spend: ${total_spend:,.2f}
      * Google: ${google_spend:,.2f}
      * Meta: ${meta_spend:,.2f}
      * Microsoft: ${ms_spend:,.2f}
* __Google:__
* Target: Lead Volume >950/month AND Lead to Opp % ≥10%
   * Status: {google_status}
   * Leads: {google_leads:,}
   * Opportunities: {google_opps:,}
      * Lead to Opp Rate: {google_l2o:.1f}%
* __Meta:__
* Increase Volume of Meta Website Leads While keeping CPAs for Prospecting below $100 per website lead and for Remarketing below $35* per website lead (adjusted to include new full funnel remarketing and the associated value)
   * Status: {meta_status}
      * Leads: {meta_leads:,}
      * Remarketing CPA: ${meta_remarketing_cpa:,.2f}
      * Prospecting CPA: ${meta_prospecting_cpa:,.2f}
* __Bing:__
* Keep CPAs on Bing below $55 while ensuring we hit for all locations
   * Status: {bing_status}
      * CPA: ${ms_cpa:,.2f}

Data for context:
{data_context}

Return ONLY the formatted text block — no explanations, no markdown code fences, no preamble. The output should be ready to copy-paste directly into a Google Doc."""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            kpi_text = response.content[0].text.strip()
        except Exception as e:
            logger.error("kpi_section_ai_failed", error=str(e))
            kpi_text = _build_fallback_text(
                period_label, total_spend, google_spend, meta_spend, ms_spend,
                google_leads, google_opps, google_l2o, google_status,
                meta_leads, meta_remarketing_cpa, meta_prospecting_cpa, meta_status,
                ms_cpa, bing_status
            )
    else:
        kpi_text = _build_fallback_text(
            period_label, total_spend, google_spend, meta_spend, ms_spend,
            google_leads, google_opps, google_l2o, google_status,
            meta_leads, meta_remarketing_cpa, meta_prospecting_cpa, meta_status,
            ms_cpa, bing_status
        )

    logger.info(
        "weekly_kpi_section_generated",
        period=period_label,
        total_spend=total_spend,
        google_leads=google_leads,
        meta_leads=meta_leads,
    )

    return WeeklyKpiResponse(
        text=kpi_text,
        period_label=period_label,
        meta_spend=meta_spend,
        google_spend=google_spend,
        microsoft_spend=ms_spend,
        total_spend=total_spend,
        google_leads=google_leads,
        google_opportunities=google_opps,
        google_lead_to_opp_pct=google_l2o,
        meta_leads=meta_leads,
        meta_remarketing_cpa=meta_remarketing_cpa,
        meta_prospecting_cpa=meta_prospecting_cpa,
        bing_cpa=ms_cpa,
        bing_leads=ms_leads,
    )


def _build_fallback_text(
    period_label: str,
    total_spend: float, google_spend: float, meta_spend: float, ms_spend: float,
    google_leads: int, google_opps: int, google_l2o: float, google_status: str,
    meta_leads: int, meta_remarketing_cpa: float, meta_prospecting_cpa: float, meta_status: str,
    ms_cpa: float, bing_status: str,
) -> str:
    """Build the KPI text block without AI (direct template fill)."""
    return f"""Performance Metrics & KPIs
Reporting Period: {period_label}
Performance Notes
Primary KPI Tracking / Channel
* Paid Media
   * Total Paid Media Spend: ${total_spend:,.2f}
      * Google: ${google_spend:,.2f}
      * Meta: ${meta_spend:,.2f}
      * Microsoft: ${ms_spend:,.2f}
* __Google:__
* Target: Lead Volume >950/month AND Lead to Opp % ≥10%
   * Status: {google_status}
   * Leads: {google_leads:,}
   * Opportunities: {google_opps:,}
      * Lead to Opp Rate: {google_l2o:.1f}%
* __Meta:__
* Increase Volume of Meta Website Leads While keeping CPAs for Prospecting below $100 per website lead and for Remarketing below $35* per website lead (adjusted to include new full funnel remarketing and the associated value)
   * Status: {meta_status}
      * Leads: {meta_leads:,}
      * Remarketing CPA: ${meta_remarketing_cpa:,.2f}
      * Prospecting CPA: ${meta_prospecting_cpa:,.2f}
* __Bing:__
* Keep CPAs on Bing below $55 while ensuring we hit for all locations
   * Status: {bing_status}
      * CPA: ${ms_cpa:,.2f}"""
