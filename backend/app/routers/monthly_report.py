"""
Monthly Report router — generates the full 7-slide performance report for Schumacher Homes.

Slide structure (matching Jan 2026 PowerPoint template):
  1. Title & Agenda
  2. Paid Media KPIs & MoM Analysis (live data, Claude key takeaways)
  3. Design Center Scorecard (user-supplied HubSpot location data)
  4. Attribution & Data Integrity (user Q&A answers)
  5. Ad Development & Testing (top Meta creatives with thumbnails)
  6. Current Initiatives & Priority Updates (user-supplied)
  7. Strategic Recommendations (Claude-generated)
"""

from __future__ import annotations

import asyncio
import base64
import calendar
import io
import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import anthropic
import httpx
import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.routers.microsoft import _parse_float, _parse_int, SCHUMACHER_MICROSOFT_ACCOUNT_ID
from app.services.live_api import LiveAPIService, DateRange as LiveDateRange
from app.services.mcp_client import MCPGatewayClient

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["monthly_report"])
settings = get_settings()

META_API_BASE = "https://graph.facebook.com/v21.0"
META_ACCOUNT_ID = "act_142003632"


# ── Models ─────────────────────────────────────────────────────────────────

class LocationRow(BaseModel):
    location: str
    leads: int = 0
    visits: int = 0
    cpl: float = 0.0
    quotes: int = 0
    spend: float = 0.0


class AttributionAnswers(BaseModel):
    google_sync_status: str = "On Track"           # "On Track" | "In Progress" | "Off Track"
    meta_sync_status: str = "In Progress"
    microsoft_sync_status: str = "In Progress"
    pmax_status: str = ""                           # Free text
    meta_pixel_status: str = "Healthy"
    lead_scoring_status: str = "In Progress"
    hubspot_leads: int = 0
    platform_leads: int = 0
    hubspot_quotes: int = 0
    platform_quotes: int = 0
    action_items: str = ""                          # Free text, newline-separated


class MonthlySlidesRequest(BaseModel):
    start_date: str   # YYYY-MM-DD (first day of report month)
    end_date: str     # YYYY-MM-DD (last day of report month)
    prev_start_date: Optional[str] = None   # previous month start (auto-computed if omitted)
    prev_end_date: Optional[str] = None     # previous month end
    report_month_label: str = ""            # e.g. "January 2026" (auto-computed if omitted)

    # User-supplied slide content
    slide3_locations: List[LocationRow] = []
    slide3_key_insights: str = ""
    slide3_focus_areas: str = ""

    slide4_attribution: AttributionAnswers = AttributionAnswers()

    slide6_initiatives: str = ""   # Numbered list text

    # Optional overrides
    slide2_key_takeaways: str = ""
    slide2_next_steps: str = ""


class Creative(BaseModel):
    ad_id: str
    ad_name: str
    campaign_name: str
    spend: float
    leads: int
    clicks: int
    impressions: int
    cpl: Optional[float]
    ctr: float
    thumbnail_url: str = ""
    image_url: str = ""


class SlideContent(BaseModel):
    slide_number: int
    title: str
    content: Dict[str, Any]


class MonthlySlidesResponse(BaseModel):
    report_month: str
    period_label: str
    slides: List[SlideContent]
    top_creatives: List[Creative] = []


# ── Helper: date math ──────────────────────────────────────────────────────

def _prev_month_range(start_date: str) -> tuple[str, str]:
    """Given the first day of a month, return (start, end) of the previous month."""
    d = date.fromisoformat(start_date)
    first_of_this = date(d.year, d.month, 1)
    last_of_prev = first_of_this - timedelta(days=1)
    first_of_prev = date(last_of_prev.year, last_of_prev.month, 1)
    return first_of_prev.isoformat(), last_of_prev.isoformat()


def _month_label(start_date: str) -> str:
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    d = date.fromisoformat(start_date)
    return f"{months[d.month - 1]} {d.year}"


def _extract_action_value(actions: list, action_type: str) -> int:
    for a in actions or []:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0


# ── Helper: fetch Meta creatives with thumbnails ───────────────────────────

async def _fetch_top_creatives(
    dr: LiveDateRange,
    limit: int = 5,
) -> List[Creative]:
    """Fetch top N Meta ads by leads, enriched with creative thumbnail URLs."""
    if not settings.meta_access_token:
        return []

    since = dr.start_date
    until = dr.end_date
    token = settings.meta_access_token

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: get ad-level insights sorted by leads
            insights_resp = await client.get(
                f"{META_API_BASE}/{META_ACCOUNT_ID}/insights",
                params={
                    "access_token": token,
                    "level": "ad",
                    "fields": "ad_id,ad_name,campaign_name,spend,impressions,clicks,ctr,actions",
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "limit": 200,
                    "action_attribution_windows": '["7d_click","1d_view"]',
                },
            )
            insights_resp.raise_for_status()
            ads_raw = insights_resp.json().get("data", [])

            # Score by leads then spend
            enriched = []
            for a in ads_raw:
                leads = _extract_action_value(a.get("actions", []), "lead")
                spend = float(a.get("spend", 0))
                if spend < 1 and leads == 0:
                    continue
                clicks = int(a.get("clicks", 0))
                impressions = int(a.get("impressions", 0))
                enriched.append({
                    "ad_id": a.get("ad_id", ""),
                    "ad_name": a.get("ad_name", ""),
                    "campaign_name": a.get("campaign_name", ""),
                    "spend": round(spend, 2),
                    "leads": leads,
                    "clicks": clicks,
                    "impressions": impressions,
                    "cpl": round(spend / leads, 2) if leads > 0 else None,
                    "ctr": round(float(a.get("ctr", 0)), 2),
                })

            # Sort: leads desc, then spend desc
            enriched.sort(key=lambda x: (x["leads"], x["spend"]), reverse=True)
            top = enriched[:limit]

            # Step 2: fetch creative thumbnails for each ad
            async def _get_thumbnail(ad_id: str) -> tuple[str, str, str]:
                """Returns (ad_id, thumbnail_url, image_url)."""
                try:
                    resp = await client.get(
                        f"{META_API_BASE}/{ad_id}",
                        params={
                            "access_token": token,
                            "fields": "creative{thumbnail_url,image_url,object_story_spec}",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    creative = data.get("creative", {})
                    return (
                        ad_id,
                        creative.get("thumbnail_url", ""),
                        creative.get("image_url", ""),
                    )
                except Exception:
                    return (ad_id, "", "")

            thumbnail_tasks = [_get_thumbnail(ad["ad_id"]) for ad in top]
            thumbnails = await asyncio.gather(*thumbnail_tasks)
            thumb_map = {ad_id: (tn, img) for ad_id, tn, img in thumbnails}

            result = []
            for ad in top:
                tn, img = thumb_map.get(ad["ad_id"], ("", ""))
                result.append(Creative(
                    ad_id=ad["ad_id"],
                    ad_name=ad["ad_name"],
                    campaign_name=ad["campaign_name"],
                    spend=ad["spend"],
                    leads=ad["leads"],
                    clicks=ad["clicks"],
                    impressions=ad["impressions"],
                    cpl=ad["cpl"],
                    ctr=ad["ctr"],
                    thumbnail_url=tn,
                    image_url=img,
                ))

            logger.info("top_creatives_fetched", count=len(result))
            return result

    except Exception as e:
        logger.error("top_creatives_fetch_error", error=str(e))
        return []


# ── Helper: fetch all platform metrics for a period ───────────────────────

async def _fetch_platform_metrics(start: str, end: str) -> Dict[str, Any]:
    """Fetch Meta, Google, and Microsoft totals for a date range."""
    dr = LiveDateRange(start_date=start, end_date=end)
    mcp = MCPGatewayClient(gateway_url=settings.gateway_url, gateway_token=settings.gateway_token)

    results = {"meta": {}, "google": {}, "microsoft": {}}

    # Meta
    if settings.meta_access_token:
        try:
            svc = LiveAPIService(meta_access_token=settings.meta_access_token)
            account_insight, campaign_data = await asyncio.gather(
                svc.get_meta_account_insights(META_ACCOUNT_ID, dr),
                svc.get_meta_campaigns(META_ACCOUNT_ID, dr),
            )
            if account_insight.get("success") and account_insight.get("data"):
                row = account_insight["data"][0]
                meta_spend = float(row.get("spend", 0))
                meta_leads = _extract_action_value(row.get("actions", []), "lead")
                results["meta"] = {
                    "spend": meta_spend,
                    "leads": meta_leads,
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "cpl": round(meta_spend / meta_leads, 2) if meta_leads > 0 else 0,
                }

            # Segment remarketing vs prospecting
            if campaign_data.get("success"):
                rem_spend = rem_leads = pro_spend = pro_leads = 0
                for c in campaign_data.get("campaigns", []):
                    name = c.get("campaign_name", "").lower()
                    sp = float(c.get("spend", 0))
                    lds = _extract_action_value(c.get("actions", []), "lead")
                    if "remarketing" in name:
                        rem_spend += sp; rem_leads += lds
                    elif "visit" not in name:
                        pro_spend += sp; pro_leads += lds
                results["meta"]["remarketing_cpl"] = round(rem_spend / rem_leads, 2) if rem_leads > 0 else 0
                results["meta"]["remarketing_leads"] = rem_leads
                results["meta"]["prospecting_cpl"] = round(pro_spend / pro_leads, 2) if pro_leads > 0 else 0
                results["meta"]["prospecting_leads"] = pro_leads
        except Exception as e:
            logger.warning("meta_fetch_error", error=str(e))

    # Google
    if mcp.is_configured:
        try:
            google_raw = await mcp.call_tool("googleads_campaign_performance", {
                "startDate": start,
                "endDate": end,
            })
            if isinstance(google_raw, list):
                g_spend = sum(float(r.get("cost", 0)) for r in google_raw)
                g_leads = sum(int(r.get("conversions", 0)) for r in google_raw)
                g_clicks = sum(int(r.get("clicks", 0)) for r in google_raw)
                results["google"] = {
                    "spend": round(g_spend, 2),
                    "leads": g_leads,
                    "clicks": g_clicks,
                    "cpl": round(g_spend / g_leads, 2) if g_leads > 0 else 0,
                }
        except Exception as e:
            logger.warning("google_fetch_error", error=str(e))

    # Microsoft
    if mcp.is_configured:
        try:
            ms_raw = await mcp.call_tool("microsoft_ads_campaign_performance", {
                "accountId": SCHUMACHER_MICROSOFT_ACCOUNT_ID,
                "startDate": start,
                "endDate": end,
            })
            rows = ms_raw if isinstance(ms_raw, list) else ms_raw.get("data", [])
            ms_spend = round(sum(_parse_float(r.get("Spend", 0)) for r in rows), 2)
            ms_leads = sum(_parse_int(r.get("Conversions", 0)) for r in rows)
            ms_clicks = sum(_parse_int(r.get("Clicks", 0)) for r in rows)
            results["microsoft"] = {
                "spend": ms_spend,
                "leads": ms_leads,
                "clicks": ms_clicks,
                "cpl": round(ms_spend / ms_leads, 2) if ms_leads > 0 else 0,
            }
        except Exception as e:
            logger.warning("microsoft_fetch_error", error=str(e))

    return results


# ── Claude generation helpers ─────────────────────────────────────────────

def _claude_client() -> Optional[anthropic.Anthropic]:
    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return None


def _ask_claude(client: anthropic.Anthropic, prompt: str, max_tokens: int = 800) -> str:
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.error("claude_generation_error", error=str(e))
        return ""


def _pct_change(current: float, previous: float) -> str:
    if previous == 0:
        return "N/A"
    pct = ((current - previous) / previous) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def _arrow(current: float, previous: float, invert: bool = False) -> str:
    """Return ▲ or ▼ based on direction; invert=True means lower is better."""
    if previous == 0:
        return ""
    up = current > previous
    if invert:
        return "▼" if up else "▲"
    return "▲" if up else "▼"


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/top-creatives", response_model=List[Creative])
async def get_top_creatives(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    limit: int = Query(5, ge=1, le=20),
):
    """Fetch top Meta ad creatives by leads for a period, with thumbnail URLs."""
    dr = LiveDateRange(start_date=start_date, end_date=end_date)
    creatives = await _fetch_top_creatives(dr, limit=limit)
    return creatives


@router.post("/monthly-slides", response_model=MonthlySlidesResponse)
async def generate_monthly_slides(req: MonthlySlidesRequest):
    """
    Generate all 7 slides of the monthly performance report.
    Returns structured JSON for each slide that the frontend renders.
    """
    # ── Date setup ────────────────────────────────────────────────────────
    if not req.prev_start_date or not req.prev_end_date:
        prev_start, prev_end = _prev_month_range(req.start_date)
    else:
        prev_start, prev_end = req.prev_start_date, req.prev_end_date

    month_label = req.report_month_label or _month_label(req.start_date)

    # ── Fetch platform data (current + previous month in parallel) ────────
    logger.info("monthly_slides_generating", month=month_label)
    curr_metrics, prev_metrics, top_creatives = await asyncio.gather(
        _fetch_platform_metrics(req.start_date, req.end_date),
        _fetch_platform_metrics(prev_start, prev_end),
        _fetch_top_creatives(LiveDateRange(start_date=req.start_date, end_date=req.end_date)),
    )

    curr_meta = curr_metrics.get("meta", {})
    curr_goog = curr_metrics.get("google", {})
    curr_ms   = curr_metrics.get("microsoft", {})
    prev_meta = prev_metrics.get("meta", {})
    prev_goog = prev_metrics.get("google", {})
    prev_ms   = prev_metrics.get("microsoft", {})

    total_spend = (curr_meta.get("spend", 0) + curr_goog.get("spend", 0) + curr_ms.get("spend", 0))
    total_leads = (curr_meta.get("leads", 0) + curr_goog.get("leads", 0) + curr_ms.get("leads", 0))
    blended_cpl = round(total_spend / total_leads, 2) if total_leads > 0 else 0

    # ── Claude for AI-generated content ───────────────────────────────────
    ai = _claude_client()
    slides: List[SlideContent] = []

    # ── SLIDE 1: Title & Agenda ───────────────────────────────────────────
    slides.append(SlideContent(
        slide_number=1,
        title=f"{month_label} Report",
        content={
            "headline": f"{month_label} Report",
            "agenda": [
                "Performance Reporting & Data Integrity",
                "Ad Development & Testing",
                "Priority Updates / New Business",
            ],
        },
    ))

    # ── SLIDE 2: KPIs & MoM Analysis ─────────────────────────────────────
    # Build the MoM comparison table rows
    mom_rows = [
        {
            "metric": "Google Spend",
            "prev": f"${prev_goog.get('spend', 0):,.0f}",
            "curr": f"${curr_goog.get('spend', 0):,.0f}",
            "change": _pct_change(curr_goog.get("spend", 0), prev_goog.get("spend", 0)),
            "direction": _arrow(curr_goog.get("spend", 0), prev_goog.get("spend", 0)),
            "invert": False,
        },
        {
            "metric": "Google Leads",
            "prev": f"{prev_goog.get('leads', 0):,}",
            "curr": f"{curr_goog.get('leads', 0):,}",
            "change": _pct_change(curr_goog.get("leads", 0), prev_goog.get("leads", 0)),
            "direction": _arrow(curr_goog.get("leads", 0), prev_goog.get("leads", 0)),
            "invert": False,
        },
        {
            "metric": "Google CPL",
            "prev": f"${prev_goog.get('cpl', 0):,.2f}",
            "curr": f"${curr_goog.get('cpl', 0):,.2f}",
            "change": _pct_change(curr_goog.get("cpl", 0), prev_goog.get("cpl", 0)),
            "direction": _arrow(curr_goog.get("cpl", 0), prev_goog.get("cpl", 0), invert=True),
            "invert": True,
        },
        {
            "metric": "Meta Spend",
            "prev": f"${prev_meta.get('spend', 0):,.0f}",
            "curr": f"${curr_meta.get('spend', 0):,.0f}",
            "change": _pct_change(curr_meta.get("spend", 0), prev_meta.get("spend", 0)),
            "direction": _arrow(curr_meta.get("spend", 0), prev_meta.get("spend", 0)),
            "invert": False,
        },
        {
            "metric": "Meta Leads",
            "prev": f"{prev_meta.get('leads', 0):,}",
            "curr": f"{curr_meta.get('leads', 0):,}",
            "change": _pct_change(curr_meta.get("leads", 0), prev_meta.get("leads", 0)),
            "direction": _arrow(curr_meta.get("leads", 0), prev_meta.get("leads", 0)),
            "invert": False,
        },
        {
            "metric": "Meta Remarketing CPL",
            "prev": f"${prev_meta.get('remarketing_cpl', 0):,.2f}",
            "curr": f"${curr_meta.get('remarketing_cpl', 0):,.2f}",
            "change": _pct_change(curr_meta.get("remarketing_cpl", 0), prev_meta.get("remarketing_cpl", 0)),
            "direction": _arrow(curr_meta.get("remarketing_cpl", 0), prev_meta.get("remarketing_cpl", 0), invert=True),
            "invert": True,
        },
        {
            "metric": "Meta Prospecting CPL",
            "prev": f"${prev_meta.get('prospecting_cpl', 0):,.2f}",
            "curr": f"${curr_meta.get('prospecting_cpl', 0):,.2f}",
            "change": _pct_change(curr_meta.get("prospecting_cpl", 0), prev_meta.get("prospecting_cpl", 0)),
            "direction": _arrow(curr_meta.get("prospecting_cpl", 0), prev_meta.get("prospecting_cpl", 0), invert=True),
            "invert": True,
        },
        {
            "metric": "Microsoft Spend",
            "prev": f"${prev_ms.get('spend', 0):,.0f}",
            "curr": f"${curr_ms.get('spend', 0):,.0f}",
            "change": _pct_change(curr_ms.get("spend", 0), prev_ms.get("spend", 0)),
            "direction": _arrow(curr_ms.get("spend", 0), prev_ms.get("spend", 0)),
            "invert": False,
        },
        {
            "metric": "Microsoft Leads",
            "prev": f"{prev_ms.get('leads', 0):,}",
            "curr": f"{curr_ms.get('leads', 0):,}",
            "change": _pct_change(curr_ms.get("leads", 0), prev_ms.get("leads", 0)),
            "direction": _arrow(curr_ms.get("leads", 0), prev_ms.get("leads", 0)),
            "invert": False,
        },
        {
            "metric": "Microsoft CPL",
            "prev": f"${prev_ms.get('cpl', 0):,.2f}",
            "curr": f"${curr_ms.get('cpl', 0):,.2f}",
            "change": _pct_change(curr_ms.get("cpl", 0), prev_ms.get("cpl", 0)),
            "direction": _arrow(curr_ms.get("cpl", 0), prev_ms.get("cpl", 0), invert=True),
            "invert": True,
        },
    ]

    # Generate key takeaways with Claude if not provided
    key_takeaways = req.slide2_key_takeaways
    next_steps = req.slide2_next_steps
    if ai and not key_takeaways:
        prev_month_name = _month_label(prev_start)
        prompt = f"""You are a senior paid media strategist writing a monthly client report for Schumacher Homes (national home builder, 32 locations).

Write 3-4 concise key takeaways for the MoM performance summary slide. Be specific, data-driven, and strategic. Each takeaway is 1-2 sentences.

{prev_month_name} vs {month_label} Data:
- Google: Spend ${prev_goog.get('spend',0):,.0f} → ${curr_goog.get('spend',0):,.0f}, Leads {prev_goog.get('leads',0)} → {curr_goog.get('leads',0)}, CPL ${prev_goog.get('cpl',0):,.2f} → ${curr_goog.get('cpl',0):,.2f}
- Meta: Spend ${prev_meta.get('spend',0):,.0f} → ${curr_meta.get('spend',0):,.0f}, Leads {prev_meta.get('leads',0)} → {curr_meta.get('leads',0)}, Remarketing CPL ${prev_meta.get('remarketing_cpl',0):,.2f} → ${curr_meta.get('remarketing_cpl',0):,.2f}, Prospecting CPL ${prev_meta.get('prospecting_cpl',0):,.2f} → ${curr_meta.get('prospecting_cpl',0):,.2f}
- Microsoft: Spend ${prev_ms.get('spend',0):,.0f} → ${curr_ms.get('spend',0):,.0f}, Leads {prev_ms.get('leads',0)} → {curr_ms.get('leads',0)}, CPL ${prev_ms.get('cpl',0):,.2f} → ${curr_ms.get('cpl',0):,.2f}
- Total Spend: ${(prev_meta.get('spend',0)+prev_goog.get('spend',0)+prev_ms.get('spend',0)):,.0f} → ${total_spend:,.0f}
- Total Leads: {(prev_meta.get('leads',0)+prev_goog.get('leads',0)+prev_ms.get('leads',0)):,} → {total_leads:,}

Write just the bullet points (3-4 items), no headers or preamble. Start each with a dash (-)."""
        raw = _ask_claude(ai, prompt, 400)
        key_takeaways = raw

    slides.append(SlideContent(
        slide_number=2,
        title="Paid Media KPIs & MoM Analysis",
        content={
            "subtitle": f"Ad Platform Data | {month_label} | 32 Locations",
            "summary_stats": {
                "total_leads": total_leads,
                "blended_cpl": blended_cpl,
                "total_spend": total_spend,
            },
            "prev_month_label": _month_label(prev_start),
            "curr_month_label": month_label,
            "mom_table": mom_rows,
            "key_takeaways": key_takeaways,
            "next_steps": next_steps,
        },
    ))

    # ── SLIDE 3: Design Center Scorecard ──────────────────────────────────
    locations = [loc.model_dump() for loc in req.slide3_locations]

    # Calculate aggregate totals + cost per visit
    total_visits = sum(loc.get("visits", 0) for loc in locations)
    total_loc_spend = sum(loc.get("spend", 0) for loc in locations)
    total_loc_leads = sum(loc.get("leads", 0) for loc in locations)
    total_quotes = sum(loc.get("quotes", 0) for loc in locations)
    avg_cpl = round(total_loc_spend / total_loc_leads, 2) if total_loc_leads > 0 else 0
    cost_per_visit = round(total_loc_spend / total_visits, 2) if total_visits > 0 else 0

    # Sort into top performers (low CPL, high leads) and needs attention (high CPL or low volume)
    sorted_locs = sorted(locations, key=lambda x: (-(x.get("leads", 0)), x.get("cpl", 9999)))
    top_performers = [l for l in sorted_locs if l.get("cpl", 9999) < 150 and l.get("leads", 0) > 30][:5]
    needs_attention = [l for l in sorted_locs if l.get("cpl", 0) > 150 or (l.get("leads", 0) > 0 and l.get("visits", 0) == 0)][:6]

    # Generate key insights with Claude if not provided
    slide3_insights = req.slide3_key_insights
    if ai and locations and not slide3_insights:
        loc_summary = "\n".join([
            f"- {l['location']}: {l['leads']} leads, {l['visits']} visits, ${l['cpl']:.2f} CPL, {l['quotes']} quotes, ${l['spend']:,.0f} spend"
            for l in sorted_locs[:15]
        ])
        prompt = f"""You are a senior paid media strategist analyzing location-level performance for Schumacher Homes (national home builder, 32 locations).

Write 4-5 concise, specific key insights about this month's location data. Highlight top performers, underperformers, and notable patterns (e.g. high spend + low visits, efficient CPL markets worth scaling, etc.).

Location data ({month_label}):
{loc_summary}

Totals: {total_loc_leads} leads, {total_visits} visits, ${avg_cpl:.2f} avg CPL, ${cost_per_visit:.2f} cost per visit, ${total_loc_spend:,.0f} total spend

Write just the bullet points (4-5 items), no headers. Start each with a dash (-)."""
        slide3_insights = _ask_claude(ai, prompt, 400)

    slides.append(SlideContent(
        slide_number=3,
        title="Design Center Scorecard",
        content={
            "subtitle": f"HubSpot Data | {month_label} | 32 Locations",
            "summary_stats": {
                "total_leads": total_loc_leads,
                "avg_cpl": avg_cpl,
                "total_visits": total_visits,
                "total_quotes": total_quotes,
                "cost_per_visit": cost_per_visit,
                "total_spend": total_loc_spend,
            },
            "top_performers": top_performers,
            "needs_attention": needs_attention,
            "all_locations": sorted_locs,
            "key_insights": slide3_insights,
            "focus_areas": req.slide3_focus_areas,
        },
    ))

    # ── SLIDE 4: Attribution & Data Integrity ─────────────────────────────
    attr = req.slide4_attribution
    platform_leads = attr.platform_leads or total_leads
    hubspot_leads = attr.hubspot_leads or total_loc_leads
    lead_variance = platform_leads - hubspot_leads
    lead_accuracy = round((1 - abs(lead_variance) / platform_leads) * 100, 1) if platform_leads > 0 else 0

    slides.append(SlideContent(
        slide_number=4,
        title="Attribution & Data Integrity",
        content={
            "hubspot_sync": {
                "overall_status": "In Progress",
                "google_status": attr.google_sync_status,
                "meta_status": attr.meta_sync_status,
                "microsoft_status": attr.microsoft_sync_status,
            },
            "accuracy_table": [
                {
                    "metric": "Leads",
                    "platform": platform_leads,
                    "hubspot": hubspot_leads,
                    "variance": f"{lead_variance:+,} ({abs(lead_variance/platform_leads*100):.1f}%)" if platform_leads > 0 else "—",
                    "accuracy": f"{lead_accuracy}%",
                    "on_target": lead_accuracy >= 85,
                },
                {
                    "metric": "Quotes / Opps",
                    "platform": attr.platform_quotes,
                    "hubspot": attr.hubspot_quotes,
                    "variance": f"{attr.hubspot_quotes - attr.platform_quotes:+,}" if attr.platform_quotes > 0 else "—",
                    "accuracy": "—",
                    "on_target": None,
                },
            ],
            "pmax_status": attr.pmax_status,
            "meta_pixel_status": attr.meta_pixel_status,
            "lead_scoring_status": attr.lead_scoring_status,
            "action_items": [line.strip() for line in attr.action_items.split("\n") if line.strip()],
        },
    ))

    # ── SLIDE 5: Ad Development & Testing ─────────────────────────────────
    slides.append(SlideContent(
        slide_number=5,
        title="Ad Development & Testing",
        content={
            "subtitle": f"Top Performing Meta Creatives | {month_label}",
            "creatives": [c.model_dump() for c in top_creatives],
            "note": "Creatives ranked by lead volume for the reporting period.",
        },
    ))

    # ── SLIDE 6: Current Initiatives ─────────────────────────────────────
    initiatives_lines = [
        line.strip() for line in req.slide6_initiatives.split("\n") if line.strip()
    ] if req.slide6_initiatives else []

    slides.append(SlideContent(
        slide_number=6,
        title="Current Initiatives & Priority Updates",
        content={
            "initiatives": initiatives_lines,
        },
    ))

    # ── SLIDE 7: Strategic Recommendations ───────────────────────────────
    recommendations: List[Dict[str, str]] = []
    whats_next = ""

    if ai:
        context_parts = [
            f"Month: {month_label}",
            f"Total Spend: ${total_spend:,.2f} | Total Leads: {total_leads:,} | Blended CPL: ${blended_cpl:,.2f}",
            f"Google: ${curr_goog.get('spend',0):,.0f} spend, {curr_goog.get('leads',0):,} leads, ${curr_goog.get('cpl',0):,.2f} CPL",
            f"Meta: ${curr_meta.get('spend',0):,.0f} spend, {curr_meta.get('leads',0):,} leads, Remarketing CPL ${curr_meta.get('remarketing_cpl',0):,.2f}, Prospecting CPL ${curr_meta.get('prospecting_cpl',0):,.2f}",
            f"Microsoft: ${curr_ms.get('spend',0):,.0f} spend, {curr_ms.get('leads',0):,} leads, ${curr_ms.get('cpl',0):,.2f} CPL",
        ]
        if locations:
            context_parts.append(f"HubSpot: {total_loc_leads} leads, {total_visits} visits, ${cost_per_visit:.2f} cost/visit")
        if initiatives_lines:
            context_parts.append(f"Active initiatives: {'; '.join(initiatives_lines[:4])}")

        prompt = f"""You are a senior paid media strategist writing the strategic recommendations slide for a monthly client report for Schumacher Homes (national home builder).

Write 3 strategic recommendations. Each should have:
- A bold title (short, 4-8 words)
- 2-3 sentences of supporting rationale with specific data references

Then write a "What's Next" paragraph (2-3 sentences) about the outlook for next month.

Performance context:
{chr(10).join(context_parts)}

Format your response EXACTLY as:
REC1_TITLE: [title]
REC1_BODY: [body]
REC2_TITLE: [title]
REC2_BODY: [body]
REC3_TITLE: [title]
REC3_BODY: [body]
WHATS_NEXT: [paragraph]"""

        raw = _ask_claude(ai, prompt, 700)
        # Parse the structured response
        for i in range(1, 4):
            title_key = f"REC{i}_TITLE:"
            body_key = f"REC{i}_BODY:"
            title = ""
            body = ""
            for line in raw.split("\n"):
                if line.startswith(title_key):
                    title = line[len(title_key):].strip()
                elif line.startswith(body_key):
                    body = line[len(body_key):].strip()
            if title:
                recommendations.append({"title": title, "body": body})

        for line in raw.split("\n"):
            if line.startswith("WHATS_NEXT:"):
                whats_next = line[len("WHATS_NEXT:"):].strip()

    slides.append(SlideContent(
        slide_number=7,
        title="Strategic Recommendations",
        content={
            "recommendations": recommendations,
            "whats_next": whats_next,
        },
    ))

    logger.info("monthly_slides_complete", month=month_label, slide_count=len(slides))

    return MonthlySlidesResponse(
        report_month=month_label,
        period_label=f"{req.start_date} – {req.end_date}",
        slides=slides,
        top_creatives=top_creatives,
    )


# ── Scorecard file parser ─────────────────────────────────────────────────

_SCORECARD_SYSTEM = """You are an expert data extraction assistant. Extract Design Center Scorecard data for Schumacher Homes from the provided content. Return ONLY valid JSON with this exact structure:
{
  "locations": [
    {"location": "Location Name", "leads": 0, "visits": 0, "cpl": 0.0, "quotes": 0, "spend": 0.0}
  ],
  "key_insights": "",
  "focus_areas": ""
}
Rules:
- "location" is the design center / market name (string)
- "leads" is the number of leads (integer)
- "visits" is the number of visits or appointments (integer)
- "cpl" is cost per lead in dollars (float)
- "quotes" is the number of quotes or opportunities (integer)
- "spend" is the total ad spend in dollars (float)
- If a column is not present, use 0
- If you can infer key_insights from the data (2-4 bullet points separated by newlines), include them; otherwise leave empty
- If you can identify focus_areas, include them; otherwise leave empty
- Return ONLY the JSON object — no markdown fences, no explanation"""


@router.post("/parse-scorecard")
async def parse_scorecard_file(file: UploadFile = File(...)):
    """
    Accept a file upload (CSV, XLSX, PDF, or image) and use Claude to extract
    Design Center Scorecard location data (location, leads, visits, CPL, quotes, spend).
    Returns structured JSON ready to populate the wizard table.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    content_bytes = await file.read()
    filename = file.filename or ""
    content_type = file.content_type or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    text_content: Optional[str] = None
    image_base64: Optional[str] = None
    image_media_type: Optional[str] = None

    try:
        if ext in ("csv", "tsv") or "csv" in content_type:
            text_content = content_bytes.decode("utf-8", errors="replace")

        elif ext in ("xlsx", "xls") or "spreadsheet" in content_type or "excel" in content_type:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content_bytes), read_only=True, data_only=True)
            ws = wb.active
            rows = []
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    rows.append("\t".join(str(c) if c is not None else "" for c in row))
            text_content = "\n".join(rows)

        elif ext == "pdf" or "pdf" in content_type:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            text_content = "\n".join(page.extract_text() or "" for page in reader.pages)

        elif ext in ("png", "jpg", "jpeg", "webp", "gif") or "image" in content_type:
            image_base64 = base64.standard_b64encode(content_bytes).decode("utf-8")
            type_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "webp": "image/webp", "gif": "image/gif"}
            image_media_type = type_map.get(ext, "image/png")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: '{ext or content_type}'. Upload a CSV, XLSX, PDF, or image.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read file: {e}")

    # Call Claude
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_prompt = "Extract the Design Center Scorecard location data from this content."

    try:
        if image_base64 and image_media_type:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=_SCORECARD_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_media_type,
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": user_prompt},
                    ],
                }],
            )
        else:
            trimmed = (text_content or "")[:10000]
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=_SCORECARD_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": f"{user_prompt}\n\nFile content:\n{trimmed}",
                }],
            )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if Claude adds them
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        logger.info("scorecard_parsed", location_count=len(parsed.get("locations", [])))
        return parsed

    except json.JSONDecodeError as e:
        logger.error("scorecard_json_parse_error", error=str(e))
        raise HTTPException(status_code=500, detail="Claude returned unparseable JSON. Try a cleaner file format.")
    except Exception as e:
        logger.error("scorecard_parse_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
