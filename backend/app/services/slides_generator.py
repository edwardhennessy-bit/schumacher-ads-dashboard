"""
Google Slides generator for Monthly Performance Reviews.

Creates aesthetically pleasing slide decks with performance data,
platform breakdowns, campaign tables, and AI-generated insights.
"""

import calendar
import structlog
from typing import Any, Dict, List, Union

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = structlog.get_logger(__name__)

# ── Brand colors ──────────────────────────────────────────────────
DARK_BG = {"red": 0.12, "green": 0.12, "blue": 0.14}        # #1F1F24
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
LIGHT_GRAY = {"red": 0.95, "green": 0.95, "blue": 0.96}     # #F2F2F5
GREEN = {"red": 0.13, "green": 0.77, "blue": 0.37}           # #22C55E
RED = {"red": 0.94, "green": 0.27, "blue": 0.27}             # #EF4444
BLUE = {"red": 0.24, "green": 0.47, "blue": 0.96}            # #3B78F5
PURPLE = {"red": 0.58, "green": 0.34, "blue": 0.92}          # #9456EB
ACCENT_GRAY = {"red": 0.6, "green": 0.6, "blue": 0.65}      # #9999A6

# Slide dimensions (default 10" x 5.625" = 25400000 x 14287500 EMU)
SLIDE_W = 9144000
SLIDE_H = 5143125

EMU_PER_INCH = 914400
EMU_PER_PT = 12700


def _emu(inches: float) -> int:
    return int(inches * EMU_PER_INCH)


def _pt(points: float) -> int:
    return int(points * EMU_PER_PT)


def _fmt_currency(value: float) -> str:
    if abs(value) >= 1000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _fmt_number(value: Union[int, float]) -> str:
    if isinstance(value, float):
        value = int(round(value))
    if abs(value) >= 1000:
        return f"{value:,}"
    return str(value)


def _fmt_pct(value: float) -> str:
    return f"{value:+.1f}%"


def _change_color(change: float, invert: bool = False) -> Dict:
    """Green for improvement, red for decline."""
    is_good = change < 0 if invert else change > 0
    return GREEN if is_good else RED if change != 0 else ACCENT_GRAY


class SlidesGenerator:
    """Creates Google Slides presentations for performance reviews."""

    def __init__(self, credentials: Credentials):
        self.service = build("slides", "v1", credentials=credentials)
        self.drive_service = build("drive", "v3", credentials=credentials)

    async def create_monthly_review(
        self,
        data: Dict[str, Any],
        insights: Dict[str, Any],
    ) -> Dict[str, str]:
        """Create a full monthly performance review deck.

        Returns {"id": presentation_id, "url": presentation_url, "title": title}
        """
        month = data["month"]
        year = data["year"]
        month_name = calendar.month_name[month]
        title = f"Schumacher Homes — {month_name} {year} Performance Review"

        # 1. Create presentation
        presentation = self.service.presentations().create(
            body={"title": title}
        ).execute()
        pres_id = presentation["presentationId"]

        # Build all slide requests
        requests = []

        # Delete the default blank slide
        default_slides = presentation.get("slides", [])
        if default_slides:
            requests.append({
                "deleteObject": {"objectId": default_slides[0]["objectId"]}
            })

        # Add slides
        requests.extend(self._title_slide(month_name, year))
        requests.extend(self._executive_summary_slide(data, insights))
        requests.extend(self._kpi_overview_slide(data))

        if data.get("meta"):
            requests.extend(self._platform_slide(data["meta"], "Meta", BLUE))
        if data.get("google"):
            requests.extend(self._platform_slide(data["google"], "Google Ads", GREEN))

        requests.extend(self._campaign_performance_slide(data))
        requests.extend(self._recommendations_slide(insights))
        requests.extend(self._next_steps_slide(insights))

        # Execute all requests
        if requests:
            self.service.presentations().batchUpdate(
                presentationId=pres_id,
                body={"requests": requests},
            ).execute()

        url = f"https://docs.google.com/presentation/d/{pres_id}/edit"
        logger.info("slides_created", title=title, url=url)
        return {"id": pres_id, "url": url, "title": title}

    # ── Slide builders ────────────────────────────────────────────

    def _title_slide(self, month_name: str, year: int) -> List[Dict]:
        """Dark background title slide."""
        slide_id = "slide_title"
        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": 0}},
            # Dark background
            self._set_bg(slide_id, DARK_BG),
            # Title text
            *self._add_text_box(
                slide_id, "title_main",
                f"Monthly Performance Review",
                x=0.8, y=1.5, w=8.4, h=1.0,
                font_size=36, bold=True, color=WHITE,
            ),
            # Subtitle
            *self._add_text_box(
                slide_id, "title_sub",
                f"Schumacher Homes  ·  {month_name} {year}",
                x=0.8, y=2.5, w=8.4, h=0.6,
                font_size=18, color=ACCENT_GRAY,
            ),
            # Brand line
            *self._add_shape(
                slide_id, "title_line",
                x=0.8, y=3.3, w=2.0, h=0.03,
                fill=GREEN,
            ),
        ]
        return requests

    def _executive_summary_slide(
        self, data: Dict, insights: Dict
    ) -> List[Dict]:
        """Executive summary with narrative text."""
        slide_id = "slide_exec"
        summary = insights.get("executive_summary", "")
        wins = insights.get("key_wins", [])
        concerns = insights.get("areas_of_concern", [])

        wins_text = "\n".join(f"  ✓  {w}" for w in wins) if wins else ""
        concerns_text = "\n".join(f"  ⚠  {c}" for c in concerns) if concerns else ""

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": 1}},
            self._set_bg(slide_id, WHITE),
            *self._add_text_box(
                slide_id, "exec_title", "Executive Summary",
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=DARK_BG,
            ),
            *self._add_shape(slide_id, "exec_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=GREEN),
            *self._add_text_box(
                slide_id, "exec_summary", summary,
                x=0.6, y=1.1, w=8.8, h=1.0,
                font_size=12, color=DARK_BG,
            ),
        ]

        if wins_text:
            requests.extend(self._add_text_box(
                slide_id, "exec_wins_title", "Key Wins",
                x=0.6, y=2.2, w=4.0, h=0.4,
                font_size=14, bold=True, color=GREEN,
            ))
            requests.extend(self._add_text_box(
                slide_id, "exec_wins", wins_text,
                x=0.6, y=2.6, w=4.2, h=2.5,
                font_size=10, color=DARK_BG,
            ))

        if concerns_text:
            requests.extend(self._add_text_box(
                slide_id, "exec_concerns_title", "Areas of Focus",
                x=5.2, y=2.2, w=4.0, h=0.4,
                font_size=14, bold=True, color=RED,
            ))
            requests.extend(self._add_text_box(
                slide_id, "exec_concerns", concerns_text,
                x=5.2, y=2.6, w=4.2, h=2.5,
                font_size=10, color=DARK_BG,
            ))

        return requests

    def _kpi_overview_slide(self, data: Dict) -> List[Dict]:
        """Cross-platform KPI cards slide."""
        slide_id = "slide_kpi"
        agg = data.get("aggregated", {})

        kpis = [
            ("Total Spend", _fmt_currency(agg.get("total_spend", 0)), None, False),
            ("Total Leads", _fmt_number(agg.get("total_leads", 0)), None, False),
            ("Blended CPL", _fmt_currency(agg.get("blended_cpl", 0)), None, True),
            ("Opportunities", _fmt_number(agg.get("total_opportunities", 0)), None, False),
            ("Cost / Opp", _fmt_currency(agg.get("blended_cpo", 0)), None, True),
        ]

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": 2}},
            self._set_bg(slide_id, LIGHT_GRAY),
            *self._add_text_box(
                slide_id, "kpi_title", "Cross-Platform KPIs",
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=DARK_BG,
            ),
            *self._add_shape(slide_id, "kpi_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=GREEN),
        ]

        # Create 5 KPI cards in a row
        card_w = 1.65
        card_gap = 0.1
        start_x = 0.5
        for i, (label, value, change, _invert) in enumerate(kpis):
            x = start_x + i * (card_w + card_gap)
            card_id = f"kpi_card_{i}"
            requests.extend(self._add_shape(
                slide_id, card_id, x=x, y=1.2, w=card_w, h=1.8,
                fill=WHITE,
            ))
            requests.extend(self._add_text_box(
                slide_id, f"kpi_label_{i}", label,
                x=x + 0.1, y=1.35, w=card_w - 0.2, h=0.35,
                font_size=10, color=ACCENT_GRAY,
            ))
            requests.extend(self._add_text_box(
                slide_id, f"kpi_value_{i}", value,
                x=x + 0.1, y=1.7, w=card_w - 0.2, h=0.5,
                font_size=22, bold=True, color=DARK_BG,
            ))

        return requests

    def _platform_slide(
        self, plat: Dict, name: str, accent: Dict
    ) -> List[Dict]:
        """Platform-specific breakdown slide."""
        slide_id = f"slide_{name.lower().replace(' ', '_')}"
        idx = 3 if "meta" in name.lower() else 4

        metrics = [
            ("Spend", _fmt_currency(plat.get("spend", 0)), plat.get("spend_change", 0), False),
            ("Leads", _fmt_number(plat.get("leads", 0)), plat.get("leads_change", 0), False),
            ("CPL", _fmt_currency(plat.get("cost_per_lead", 0)), plat.get("cpl_change", 0), True),
            ("Opportunities", _fmt_number(plat.get("opportunities", 0)), plat.get("opportunities_change", 0), False),
            ("Cost / Opp", _fmt_currency(plat.get("cost_per_opportunity", 0)), plat.get("cpo_change", 0), True),
        ]

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": idx}},
            self._set_bg(slide_id, WHITE),
            *self._add_text_box(
                slide_id, f"{slide_id}_title", name,
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=DARK_BG,
            ),
            *self._add_shape(slide_id, f"{slide_id}_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=accent),
        ]

        # Metric cards
        card_w = 1.65
        start_x = 0.5
        for i, (label, value, change, invert) in enumerate(metrics):
            x = start_x + i * (card_w + 0.1)
            cid = f"{slide_id}_m{i}"
            requests.extend(self._add_shape(
                slide_id, cid, x=x, y=1.1, w=card_w, h=1.4, fill=LIGHT_GRAY,
            ))
            requests.extend(self._add_text_box(
                slide_id, f"{cid}_l", label,
                x=x + 0.1, y=1.2, w=card_w - 0.2, h=0.3,
                font_size=9, color=ACCENT_GRAY,
            ))
            requests.extend(self._add_text_box(
                slide_id, f"{cid}_v", value,
                x=x + 0.1, y=1.5, w=card_w - 0.2, h=0.4,
                font_size=18, bold=True, color=DARK_BG,
            ))
            if change is not None and change != 0:
                requests.extend(self._add_text_box(
                    slide_id, f"{cid}_c", _fmt_pct(change),
                    x=x + 0.1, y=1.9, w=card_w - 0.2, h=0.3,
                    font_size=10, color=_change_color(change, invert),
                ))

        # Additional rows for Meta (remarketing/prospecting)
        if plat.get("remarketing_cpl"):
            requests.extend(self._add_text_box(
                slide_id, f"{slide_id}_rmkt",
                f"Remarketing CPL: {_fmt_currency(plat['remarketing_cpl'])}  ({_fmt_number(plat.get('remarketing_leads', 0))} leads)",
                x=0.6, y=2.8, w=4.0, h=0.3, font_size=11, color=DARK_BG,
            ))
        if plat.get("prospecting_cpl"):
            requests.extend(self._add_text_box(
                slide_id, f"{slide_id}_pros",
                f"Prospecting CPL: {_fmt_currency(plat['prospecting_cpl'])}  ({_fmt_number(plat.get('prospecting_leads', 0))} leads)",
                x=0.6, y=3.1, w=4.0, h=0.3, font_size=11, color=DARK_BG,
            ))

        # Engagement metrics row
        eng_text = (
            f"Impressions: {_fmt_number(plat.get('impressions', 0))}   |   "
            f"Clicks: {_fmt_number(plat.get('clicks', 0))}   |   "
            f"CTR: {plat.get('ctr', 0):.2f}%   |   "
            f"CPC: {_fmt_currency(plat.get('cpc', 0))}"
        )
        requests.extend(self._add_text_box(
            slide_id, f"{slide_id}_eng", eng_text,
            x=0.6, y=3.6, w=8.8, h=0.3, font_size=10, color=ACCENT_GRAY,
        ))

        return requests

    def _campaign_performance_slide(self, data: Dict) -> List[Dict]:
        """Top campaigns table slide."""
        slide_id = "slide_campaigns"
        idx = 5

        # Gather campaigns from both platforms
        all_campaigns = []
        for key, platform in [("meta", "Meta"), ("google", "Google")]:
            plat = data.get(key)
            if plat and plat.get("campaigns"):
                for c in plat["campaigns"][:5]:
                    all_campaigns.append({**c, "platform": platform})

        # Sort by spend descending, take top 10
        all_campaigns.sort(key=lambda x: x.get("spend", 0), reverse=True)
        all_campaigns = all_campaigns[:10]

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": idx}},
            self._set_bg(slide_id, WHITE),
            *self._add_text_box(
                slide_id, "camp_title", "Campaign Performance",
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=DARK_BG,
            ),
            *self._add_shape(slide_id, "camp_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=GREEN),
        ]

        # Build table as text lines
        header = f"{'Platform':<10} {'Campaign':<32} {'Spend':>10} {'Leads':>8} {'CPL':>10}"
        lines = [header, "─" * 74]
        for c in all_campaigns:
            name = c.get("name", "Unknown")[:30]
            lines.append(
                f"{c.get('platform', ''):10} {name:<32} "
                f"{_fmt_currency(c.get('spend', 0)):>10} "
                f"{_fmt_number(c.get('leads', 0)):>8} "
                f"{_fmt_currency(c.get('cost_per_lead', 0)):>10}"
            )

        table_text = "\n".join(lines)
        requests.extend(self._add_text_box(
            slide_id, "camp_table", table_text,
            x=0.4, y=1.1, w=9.2, h=3.8,
            font_size=9, color=DARK_BG, font_family="Roboto Mono",
        ))

        return requests

    def _recommendations_slide(self, insights: Dict) -> List[Dict]:
        """AI-generated recommendations slide."""
        slide_id = "slide_recs"
        idx = 6
        recs = insights.get("recommendations", [])

        recs_text = "\n\n".join(f"{i+1}.  {r}" for i, r in enumerate(recs)) if recs else "No recommendations generated."

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": idx}},
            self._set_bg(slide_id, WHITE),
            *self._add_text_box(
                slide_id, "recs_title", "Recommendations",
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=DARK_BG,
            ),
            *self._add_shape(slide_id, "recs_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=PURPLE),
            *self._add_text_box(
                slide_id, "recs_body", recs_text,
                x=0.6, y=1.1, w=8.8, h=3.8,
                font_size=12, color=DARK_BG,
            ),
        ]
        return requests

    def _next_steps_slide(self, insights: Dict) -> List[Dict]:
        """Next steps / testing & strategy slide."""
        slide_id = "slide_next"
        idx = 7
        steps = insights.get("next_steps", [])

        steps_text = "\n\n".join(f"→  {s}" for s in steps) if steps else "Next steps to be discussed."

        requests = [
            {"createSlide": {"objectId": slide_id, "insertionIndex": idx}},
            self._set_bg(slide_id, DARK_BG),
            *self._add_text_box(
                slide_id, "next_title", "Next Steps & Testing",
                x=0.6, y=0.3, w=8.8, h=0.5,
                font_size=24, bold=True, color=WHITE,
            ),
            *self._add_shape(slide_id, "next_line", x=0.6, y=0.85, w=1.5, h=0.02, fill=GREEN),
            *self._add_text_box(
                slide_id, "next_body", steps_text,
                x=0.6, y=1.2, w=8.8, h=3.5,
                font_size=13, color=LIGHT_GRAY,
            ),
            # Footer note
            *self._add_text_box(
                slide_id, "next_footer",
                "Collaborate with JARVIS to expand on these items.",
                x=0.6, y=4.8, w=8.8, h=0.3,
                font_size=9, color=ACCENT_GRAY,
            ),
        ]
        return requests

    # ── Low-level helpers ─────────────────────────────────────────

    def _set_bg(self, slide_id: str, color: Dict) -> Dict:
        return {
            "updatePageProperties": {
                "objectId": slide_id,
                "pageProperties": {
                    "pageBackgroundFill": {
                        "solidFill": {"color": {"rgbColor": color}}
                    }
                },
                "fields": "pageBackgroundFill",
            }
        }

    def _add_text_box(
        self,
        slide_id: str,
        element_id: str,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        font_size: int = 12,
        bold: bool = False,
        color: Dict = None,
        font_family: str = "Roboto",
    ) -> List[Dict]:
        if color is None:
            color = DARK_BG
        return [
            {
                "createShape": {
                    "objectId": element_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": _emu(w), "unit": "EMU"},
                            "height": {"magnitude": _emu(h), "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": _emu(x),
                            "translateY": _emu(y),
                            "unit": "EMU",
                        },
                    },
                }
            },
            {
                "insertText": {
                    "objectId": element_id,
                    "text": text,
                    "insertionIndex": 0,
                }
            },
            {
                "updateTextStyle": {
                    "objectId": element_id,
                    "style": {
                        "fontFamily": font_family,
                        "fontSize": {"magnitude": font_size, "unit": "PT"},
                        "bold": bold,
                        "foregroundColor": {"opaqueColor": {"rgbColor": color}},
                    },
                    "textRange": {"type": "ALL"},
                    "fields": "fontFamily,fontSize,bold,foregroundColor",
                }
            },
        ]

    def _add_shape(
        self,
        slide_id: str,
        element_id: str,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: Dict = None,
    ) -> List[Dict]:
        requests = [
            {
                "createShape": {
                    "objectId": element_id,
                    "shapeType": "RECTANGLE",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": _emu(w), "unit": "EMU"},
                            "height": {"magnitude": _emu(h), "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": _emu(x),
                            "translateY": _emu(y),
                            "unit": "EMU",
                        },
                    },
                }
            },
        ]
        if fill:
            requests.append({
                "updateShapeProperties": {
                    "objectId": element_id,
                    "shapeProperties": {
                        "shapeBackgroundFill": {
                            "solidFill": {"color": {"rgbColor": fill}}
                        },
                        "outline": {"propertyState": "NOT_RENDERED"},
                    },
                    "fields": "shapeBackgroundFill,outline",
                }
            })
        return requests
