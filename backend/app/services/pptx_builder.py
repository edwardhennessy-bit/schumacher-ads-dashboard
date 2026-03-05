"""
pptx_builder.py — Generates a Schumacher Homes Monthly Report PPTX
matching the dark-navy brand style from the January 2026 PowerPoint template.

All 7 slides:
  1. Title & Agenda
  2. Paid Media KPIs & MoM Analysis
  3. Design Center Scorecard
  4. Attribution & Data Integrity
  5. Ad Development & Testing (Top Meta Creatives)
  6. Current Initiatives & Priority Updates
  7. Strategic Recommendations
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# ── Brand palette ──────────────────────────────────────────────────────────
NAVY      = RGBColor(0x1A, 0x27, 0x44)   # Primary background
NAVY_MID  = RGBColor(0x22, 0x35, 0x5C)   # Cards / header strip
NAVY_CARD = RGBColor(0x1E, 0x2E, 0x52)   # Slightly lighter card bg
GOLD      = RGBColor(0xC8, 0x9A, 0x28)   # Accent / branding
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
ROW_EVEN  = RGBColor(0xEB, 0xEF, 0xF9)   # Light row (even)
ROW_ODD   = RGBColor(0xF5, 0xF7, 0xFF)   # Light row (odd)
GREEN     = RGBColor(0x1E, 0xA7, 0x52)
RED       = RGBColor(0xDC, 0x3A, 0x2E)
GRAY      = RGBColor(0x94, 0xA3, 0xB8)
AMBER     = RGBColor(0xF5, 0x9E, 0x0B)
DARK_TEXT = RGBColor(0x1E, 0x29, 0x3C)
BLUE_ACC  = RGBColor(0x3B, 0x82, 0xF6)

# ── Slide dimensions: widescreen 16:9 ─────────────────────────────────────
SW = Inches(13.333)
SH = Inches(7.5)
M  = Inches(0.42)          # Side margin
HH = Inches(1.0)           # Header strip height
GH = Inches(0.05)          # Gold accent line under header
CT = HH + GH + Inches(0.18)  # Content area top
CH = SH - CT - Inches(0.22)  # Content area height
CW = SW - 2 * M              # Content area width

FONT = "Calibri"


# ── Low-level helpers ──────────────────────────────────────────────────────

def _rgb_hex(color: RGBColor) -> str:
    return f"{color.r:02X}{color.g:02X}{color.b:02X}"


def _blank_slide(prs: Presentation):
    """Add a blank slide with the navy background."""
    blank = None
    for layout in prs.slide_layouts:
        if "blank" in layout.name.lower():
            blank = layout
            break
    if blank is None:
        blank = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank)
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    return slide


def _box(slide, l, t, w, h, fill: RGBColor, alpha=None):
    """Add a filled rectangle with no border."""
    shape = slide.shapes.add_shape(1, l, t, w, h)   # 1 = Rectangle
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()  # no border
    return shape


def _txtbox(slide, text: str, l, t, w, h,
            size: int = 11, bold: bool = False,
            color: RGBColor = WHITE, align=PP_ALIGN.LEFT,
            italic: bool = False, wrap: bool = True):
    """Add a text box with a single paragraph."""
    txb = slide.shapes.add_textbox(l, t, w, h)
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = FONT
    return txb


def _multi_txtbox(slide, lines: List[str], l, t, w, h,
                  size: int = 10, bold: bool = False,
                  color: RGBColor = WHITE, align=PP_ALIGN.LEFT,
                  bullet: bool = False, line_spacing_pt: float = 2.0):
    """Add a text box with one paragraph per line."""
    txb = slide.shapes.add_textbox(l, t, w, h)
    tf = txb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_before = Pt(line_spacing_pt)
        run = p.add_run()
        run.text = ("• " if bullet else "") + str(line)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = FONT
    return txb


def _cell_fill(cell, color: RGBColor):
    """Set a table cell's solid fill via XML."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for tag in (qn("a:solidFill"), qn("a:noFill"), qn("a:gradFill"), qn("a:pattFill")):
        for el in tcPr.findall(tag):
            tcPr.remove(el)
    sf = etree.SubElement(tcPr, qn("a:solidFill"))
    etree.SubElement(sf, qn("a:srgbClr"), val=_rgb_hex(color))
    # Set cell margins
    tcPr.set("marT", str(int(Pt(2.5))))
    tcPr.set("marB", str(int(Pt(2.5))))
    tcPr.set("marL", str(int(Pt(4))))
    tcPr.set("marR", str(int(Pt(4))))


def _cell_text(cell, text: str, font_size: int = 9, bold: bool = False,
               color: RGBColor = DARK_TEXT, align=PP_ALIGN.LEFT):
    """Set table cell text with styling."""
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    # Remove any existing runs
    for r in list(p.runs):
        p._p.remove(r._r)
    if str(text):
        run = p.add_run()
        run.text = str(text)
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.name = FONT
        run.font.color.rgb = color


def _header(slide, title: str, subtitle: str = ""):
    """Standard slide header: navy strip → gold line → white title."""
    _box(slide, 0, 0, SW, HH, NAVY_MID)
    _box(slide, 0, HH, SW, GH, GOLD)
    # Schumacher branding (top-left small text)
    _txtbox(slide, "SCHUMACHER HOMES",
            M, Inches(0.12), Inches(5), Inches(0.28),
            size=8, bold=True, color=GOLD)
    # Main title
    _txtbox(slide, title,
            M, Inches(0.4), SW - 2 * M, Inches(0.52),
            size=22, bold=True, color=WHITE)
    # Subtitle
    if subtitle:
        _txtbox(slide, subtitle,
                M, Inches(0.76), SW - 2 * M, Inches(0.26),
                size=8, color=GRAY)


def _stat_card(slide, label: str, value: str, l, t, w, h=Inches(0.72)):
    """Small metric stat card."""
    _box(slide, l, t, w, h, NAVY_CARD)
    _txtbox(slide, value,
            l + Inches(0.08), t + Inches(0.05),
            w - Inches(0.16), h * 0.55,
            size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    _txtbox(slide, label,
            l, t + h * 0.58,
            w, h * 0.38,
            size=7, color=GRAY, align=PP_ALIGN.CENTER)


# ── Slide 1: Title & Agenda ────────────────────────────────────────────────

def _slide1(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)

    # Top brand strip
    _box(slide, 0, 0, SW, Inches(0.5), NAVY_MID)
    _box(slide, 0, Inches(0.5), SW, Inches(0.05), GOLD)
    _txtbox(slide, "SCHUMACHER HOMES",
            M, Inches(0.1), Inches(7), Inches(0.32),
            size=10, bold=True, color=GOLD)
    _txtbox(slide, "MONTHLY PERFORMANCE REPORT",
            0, Inches(0.12), SW - M, Inches(0.28),
            size=9, color=GRAY, align=PP_ALIGN.RIGHT)

    # Main headline
    headline = content.get("headline", "Monthly Report")
    _txtbox(slide, headline,
            M, Inches(1.5), SW - 2 * M, Inches(1.5),
            size=42, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    # Gold divider
    _box(slide, M, Inches(3.2), SW - 2 * M, Inches(0.04), GOLD)

    # AGENDA label
    _txtbox(slide, "AGENDA",
            M, Inches(3.4), SW - 2 * M, Inches(0.38),
            size=11, bold=True, color=GOLD, align=PP_ALIGN.CENTER)

    # Agenda items
    agenda = content.get("agenda", [])
    item_h = Inches(0.56)
    for i, item in enumerate(agenda):
        iy = Inches(3.9) + i * item_h
        _box(slide, M, iy + Inches(0.04), Inches(0.36), Inches(0.36), GOLD)
        _txtbox(slide, str(i + 1),
                M + Inches(0.01), iy + Inches(0.02),
                Inches(0.34), Inches(0.4),
                size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        _txtbox(slide, item,
                M + Inches(0.48), iy + Inches(0.1),
                CW - Inches(0.48), Inches(0.38),
                size=13, color=WHITE)


# ── Slide 2: KPIs & MoM Analysis ──────────────────────────────────────────

def _slide2(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Paid Media KPIs & MoM Analysis",
            content.get("subtitle", ""))

    stats = content.get("summary_stats", {})
    curr_label = content.get("curr_month_label", "Current Month")
    prev_label = content.get("prev_month_label", "Prior Month")

    # Stat row
    stat_items = [
        ("Total Leads",  f"{stats.get('total_leads', 0):,}"),
        ("Blended CPL",  f"${stats.get('blended_cpl', 0):,.2f}"),
        ("Total Spend",  f"${stats.get('total_spend', 0):,.0f}"),
    ]
    sw3 = (CW - Inches(0.2)) / 3
    for i, (lbl, val) in enumerate(stat_items):
        _stat_card(slide, lbl, val,
                   M + i * (sw3 + Inches(0.1)), CT, sw3)

    # MoM table
    mom_rows = content.get("mom_table", [])
    tbl_top = CT + Inches(0.88)
    tbl_h = SH - tbl_top - Inches(1.5) - Inches(0.22)

    if mom_rows:
        headers = [" Metric", prev_label, curr_label, "Change", ""]
        col_ws = [Inches(3.2), Inches(2.0), Inches(2.1), Inches(1.6), Inches(0.5)]
        total_w = sum(col_ws)
        tbl = slide.shapes.add_table(
            len(mom_rows) + 1, len(headers),
            M, tbl_top, total_w, tbl_h
        ).table
        for ci, cw in enumerate(col_ws):
            tbl.columns[ci].width = cw

        # Header row
        for ci, hdr in enumerate(headers):
            cell = tbl.cell(0, ci)
            _cell_fill(cell, NAVY_MID)
            _cell_text(cell, hdr, 9, True, WHITE,
                       PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER)

        # Data rows
        for ri, row in enumerate(mom_rows):
            bg = ROW_EVEN if ri % 2 == 0 else ROW_ODD
            direction = row.get("direction", "")
            change = row.get("change", "N/A")
            invert = row.get("invert", False)
            # Positive direction: ▲ is good unless invert
            if direction == "▲":
                change_col = RED if invert else GREEN
            elif direction == "▼":
                change_col = GREEN if invert else RED
            else:
                change_col = DARK_TEXT

            row_data = [
                (f" {row.get('metric','')}", DARK_TEXT, PP_ALIGN.LEFT, False),
                (row.get("prev", ""),        DARK_TEXT, PP_ALIGN.CENTER, False),
                (row.get("curr", ""),        DARK_TEXT, PP_ALIGN.CENTER, True),
                (f"{direction} {change}",   change_col, PP_ALIGN.CENTER, True),
                ("",                         DARK_TEXT, PP_ALIGN.CENTER, False),
            ]
            for ci, (txt, col, al, bd) in enumerate(row_data):
                cell = tbl.cell(ri + 1, ci)
                _cell_fill(cell, bg)
                _cell_text(cell, txt, 8, bd, col, al)

    # Key takeaways strip
    takeaways = content.get("key_takeaways", "")
    if takeaways:
        ta_top = SH - Inches(1.42)
        _box(slide, M, ta_top, CW, Inches(1.18), NAVY_MID)
        _txtbox(slide, "KEY TAKEAWAYS",
                M + Inches(0.12), ta_top + Inches(0.08),
                Inches(2.5), Inches(0.24),
                size=8, bold=True, color=GOLD)
        lines = [l.strip().lstrip("- ") for l in takeaways.split("\n") if l.strip()][:3]
        _multi_txtbox(slide, lines,
                      M + Inches(0.12), ta_top + Inches(0.3),
                      CW - Inches(0.24), Inches(0.82),
                      size=8, color=WHITE, bullet=True, line_spacing_pt=1.5)


# ── Slide 3: Design Center Scorecard ──────────────────────────────────────

def _slide3(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Design Center Scorecard",
            content.get("subtitle", ""))

    stats = content.get("summary_stats", {})

    # 6-stat row
    stat_items = [
        ("Total Leads",   f"{stats.get('total_leads', 0):,}"),
        ("Avg CPL",       f"${stats.get('avg_cpl', 0):,.2f}"),
        ("Total Visits",  f"{stats.get('total_visits', 0):,}"),
        ("Quotes",        f"{stats.get('total_quotes', 0):,}"),
        ("Cost / Visit",  f"${stats.get('cost_per_visit', 0):,.2f}"),
        ("Total Spend",   f"${stats.get('total_spend', 0):,.0f}"),
    ]
    sw6 = (CW - Inches(0.25)) / 6
    for i, (lbl, val) in enumerate(stat_items):
        _stat_card(slide, lbl, val,
                   M + i * (sw6 + Inches(0.05)), CT, sw6,
                   h=Inches(0.65))

    # Location table
    all_locs = content.get("all_locations", [])
    tbl_top = CT + Inches(0.8)
    tbl_h = SH - tbl_top - Inches(0.22)

    # If we have key insights, shrink the table to make room
    insights = content.get("key_insights", "")
    if insights:
        tbl_h = SH - tbl_top - Inches(1.35) - Inches(0.22)

    if all_locs:
        rows_to_show = all_locs[:14]
        headers = [" Location", "Leads", "Visits", "CPL ($)", "Quotes", "Spend ($)"]
        col_ws = [Inches(3.6), Inches(1.35), Inches(1.35), Inches(1.55), Inches(1.3), Inches(1.8)]
        tbl = slide.shapes.add_table(
            len(rows_to_show) + 1, len(headers),
            M, tbl_top, sum(col_ws), tbl_h
        ).table
        for ci, cw in enumerate(col_ws):
            tbl.columns[ci].width = cw

        for ci, hdr in enumerate(headers):
            cell = tbl.cell(0, ci)
            _cell_fill(cell, NAVY_MID)
            _cell_text(cell, hdr, 9, True, WHITE,
                       PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER)

        for ri, loc in enumerate(rows_to_show):
            bg = ROW_EVEN if ri % 2 == 0 else ROW_ODD
            cpl = loc.get("cpl", 0)
            cpl_col = GREEN if cpl < 100 else (RED if cpl > 175 else DARK_TEXT)
            cells = [
                (f" {loc.get('location','')}", DARK_TEXT, PP_ALIGN.LEFT),
                (f"{loc.get('leads', 0):,}",   DARK_TEXT, PP_ALIGN.CENTER),
                (f"{loc.get('visits', 0):,}",  DARK_TEXT, PP_ALIGN.CENTER),
                (f"${cpl:,.2f}",                cpl_col,  PP_ALIGN.CENTER),
                (f"{loc.get('quotes', 0):,}",  DARK_TEXT, PP_ALIGN.CENTER),
                (f"${loc.get('spend', 0):,.0f}", DARK_TEXT, PP_ALIGN.CENTER),
            ]
            for ci, (txt, col, al) in enumerate(cells):
                cell = tbl.cell(ri + 1, ci)
                _cell_fill(cell, bg)
                _cell_text(cell, txt, 8, False, col, al)

    # Key insights strip
    if insights:
        ins_top = SH - Inches(1.32)
        _box(slide, M, ins_top, CW, Inches(1.1), NAVY_MID)
        _txtbox(slide, "KEY INSIGHTS",
                M + Inches(0.12), ins_top + Inches(0.08),
                Inches(2.5), Inches(0.24),
                size=8, bold=True, color=GOLD)
        lines = [l.strip().lstrip("- ") for l in insights.split("\n") if l.strip()][:3]
        _multi_txtbox(slide, lines,
                      M + Inches(0.12), ins_top + Inches(0.3),
                      CW - Inches(0.24), Inches(0.72),
                      size=8, color=WHITE, bullet=True, line_spacing_pt=1.5)


# ── Slide 4: Attribution & Data Integrity ─────────────────────────────────

def _slide4(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Attribution & Data Integrity",
            "HubSpot & Platform Sync Status")

    sync = content.get("hubspot_sync", {})
    status_colors = {
        "On Track":  GREEN,
        "In Progress": AMBER,
        "Off Track": RED,
        "N/A": GRAY,
    }

    # Platform sync pills
    _txtbox(slide, "HUBSPOT SYNC STATUS",
            M, CT + Inches(0.05), CW, Inches(0.28),
            size=9, bold=True, color=GOLD)

    platforms = [
        ("Google Ads → HubSpot",  sync.get("google_status",    "In Progress")),
        ("Meta → HubSpot",        sync.get("meta_status",      "In Progress")),
        ("Microsoft → HubSpot",   sync.get("microsoft_status", "In Progress")),
    ]
    pill_w = (CW - Inches(0.2)) / 3
    for i, (lbl, status) in enumerate(platforms):
        px = M + i * (pill_w + Inches(0.1))
        py = CT + Inches(0.35)
        _box(slide, px, py, pill_w, Inches(0.58), NAVY_CARD)
        _txtbox(slide, lbl,
                px + Inches(0.1), py + Inches(0.06),
                pill_w - Inches(0.2), Inches(0.24),
                size=8, color=WHITE)
        sc = status_colors.get(status, GRAY)
        _txtbox(slide, f"● {status}",
                px + Inches(0.1), py + Inches(0.3),
                pill_w - Inches(0.2), Inches(0.24),
                size=10, bold=True, color=sc)

    # Attribution accuracy table
    acc_rows = content.get("accuracy_table", [])
    if acc_rows:
        _txtbox(slide, "ATTRIBUTION ACCURACY",
                M, CT + Inches(1.15), CW, Inches(0.28),
                size=9, bold=True, color=GOLD)
        headers = ["Metric", "Platform", "HubSpot", "Variance", "Accuracy", "On Target"]
        col_ws = [Inches(2.0), Inches(1.8), Inches(1.8), Inches(2.5), Inches(1.5), Inches(1.5)]
        tbl = slide.shapes.add_table(
            len(acc_rows) + 1, len(headers),
            M, CT + Inches(1.45), sum(col_ws), Inches(0.88)
        ).table
        for ci, cw in enumerate(col_ws):
            tbl.columns[ci].width = cw
        for ci, hdr in enumerate(headers):
            cell = tbl.cell(0, ci)
            _cell_fill(cell, NAVY_MID)
            _cell_text(cell, hdr, 9, True, WHITE,
                       PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER)
        for ri, row in enumerate(acc_rows):
            bg = ROW_EVEN if ri % 2 == 0 else ROW_ODD
            on_target = row.get("on_target")
            tgt_txt = "✓" if on_target is True else ("✗" if on_target is False else "—")
            tgt_col = GREEN if on_target is True else (RED if on_target is False else GRAY)
            row_data = [
                (row.get("metric",""),    DARK_TEXT, PP_ALIGN.LEFT),
                (str(row.get("platform","—")), DARK_TEXT, PP_ALIGN.CENTER),
                (str(row.get("hubspot","—")),  DARK_TEXT, PP_ALIGN.CENTER),
                (str(row.get("variance","—")), DARK_TEXT, PP_ALIGN.CENTER),
                (str(row.get("accuracy","—")), DARK_TEXT, PP_ALIGN.CENTER),
                (tgt_txt,                 tgt_col,  PP_ALIGN.CENTER),
            ]
            for ci, (txt, col, al) in enumerate(row_data):
                cell = tbl.cell(ri + 1, ci)
                _cell_fill(cell, bg)
                _cell_text(cell, txt, 9, ci == 5, col, al)

    # Other tracking + action items (two-column)
    y2 = CT + Inches(2.5)
    left_w = CW * 0.45
    right_x = M + CW * 0.52

    # Other tracking
    _txtbox(slide, "OTHER TRACKING STATUS",
            M, y2, left_w, Inches(0.28),
            size=9, bold=True, color=GOLD)
    other = [
        ("PMax",         content.get("pmax_status",        "—")),
        ("Meta Pixel",   content.get("meta_pixel_status",  "Healthy")),
        ("Lead Scoring", content.get("lead_scoring_status","In Progress")),
    ]
    for i, (lbl, val) in enumerate(other):
        oy = y2 + Inches(0.32) + i * Inches(0.42)
        _box(slide, M, oy, left_w, Inches(0.38), NAVY_CARD)
        sc = status_colors.get(val, GRAY)
        _txtbox(slide, f"{lbl}:",
                M + Inches(0.1), oy + Inches(0.08),
                Inches(1.4), Inches(0.26),
                size=8, bold=True, color=GRAY)
        _txtbox(slide, val,
                M + Inches(1.5), oy + Inches(0.08),
                left_w - Inches(1.6), Inches(0.26),
                size=8, bold=True, color=sc)

    # Action items
    action_items = content.get("action_items", [])
    if action_items:
        _txtbox(slide, "ACTION ITEMS",
                right_x, y2, CW * 0.46, Inches(0.28),
                size=9, bold=True, color=GOLD)
        _multi_txtbox(slide, action_items[:6],
                      right_x, y2 + Inches(0.32),
                      CW * 0.46, Inches(1.8),
                      size=9, color=WHITE, bullet=True)


# ── Slide 5: Ad Development & Testing ─────────────────────────────────────

def _slide5(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Ad Development & Testing",
            content.get("subtitle", "Top Performing Meta Creatives"))

    creatives = content.get("creatives", [])[:6]
    if not creatives:
        _txtbox(slide, "No creative data available for this period.",
                M, CT + Inches(1.5), CW, Inches(0.4),
                size=13, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    cols = 3
    num_rows = (len(creatives) + cols - 1) // cols
    card_w = (CW - Inches(0.3)) / cols
    card_h = (CH - Inches(0.1)) / max(num_rows, 2)

    accent_colors = [GOLD, BLUE_ACC, GREEN, AMBER, RED, GRAY]

    for i, c in enumerate(creatives):
        col = i % cols
        row = i // cols
        cx = M + col * (card_w + Inches(0.15))
        cy = CT + Inches(0.1) + row * (card_h + Inches(0.12))
        acc = accent_colors[i % len(accent_colors)]

        # Card bg
        _box(slide, cx, cy, card_w, card_h, NAVY_CARD)
        # Top accent stripe
        _box(slide, cx, cy, card_w, Inches(0.06), acc)

        # Rank badge
        _box(slide, cx + Inches(0.12), cy + Inches(0.12),
             Inches(0.3), Inches(0.3), acc)
        _txtbox(slide, f"#{i+1}",
                cx + Inches(0.12), cy + Inches(0.09),
                Inches(0.3), Inches(0.34),
                size=9, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

        # Ad name
        ad_name = (c.get("ad_name") or "Unknown Ad")[:55]
        _txtbox(slide, ad_name,
                cx + Inches(0.5), cy + Inches(0.14),
                card_w - Inches(0.62), Inches(0.44),
                size=8, bold=True, color=WHITE, wrap=True)

        # Campaign name
        campaign = (c.get("campaign_name") or "")[:42]
        if campaign:
            _txtbox(slide, campaign,
                    cx + Inches(0.12), cy + Inches(0.6),
                    card_w - Inches(0.24), Inches(0.22),
                    size=7, color=GRAY, italic=True)

        # Metric grid
        leads = c.get("leads", 0)
        spend = c.get("spend", 0)
        cpl   = c.get("cpl")
        ctr   = c.get("ctr", 0)

        metrics = [
            ("Leads",  f"{leads:,}",                     GREEN),
            ("Spend",  f"${spend:,.0f}",                 WHITE),
            ("CPL",    f"${cpl:,.2f}" if cpl else "—",   WHITE),
            ("CTR",    f"{ctr}%",                         WHITE),
        ]
        mw = card_w / len(metrics)
        my = cy + card_h - Inches(0.78)
        for mi, (mlbl, mval, mcol) in enumerate(metrics):
            mx = cx + mi * mw
            _txtbox(slide, mval,
                    mx, my, mw, Inches(0.32),
                    size=10, bold=True, color=mcol, align=PP_ALIGN.CENTER)
            _txtbox(slide, mlbl,
                    mx, my + Inches(0.3), mw, Inches(0.22),
                    size=7, color=GRAY, align=PP_ALIGN.CENTER)

    return slide


# ── Slide 6: Current Initiatives ──────────────────────────────────────────

def _slide6(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Current Initiatives & Priority Updates")

    initiatives = content.get("initiatives", [])
    if not initiatives:
        _txtbox(slide, "No initiatives provided.",
                M, CT + Inches(1.5), CW, Inches(0.4),
                size=13, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    max_items = min(len(initiatives), 10)
    use_cols = max_items > 5
    col_count = 2 if use_cols else 1
    col_w = (CW - (Inches(0.2) if use_cols else 0)) / col_count
    item_h = Inches(0.65)

    for i, initiative in enumerate(initiatives[:max_items]):
        col = i % 2 if use_cols else 0
        row = i // 2 if use_cols else i
        ix = M + col * (col_w + Inches(0.2))
        iy = CT + Inches(0.12) + row * (item_h + Inches(0.08))

        _box(slide, ix, iy, col_w, item_h, NAVY_CARD)
        # Number box
        _box(slide, ix, iy, Inches(0.44), item_h, GOLD)
        _txtbox(slide, str(i + 1),
                ix + Inches(0.01), iy + Inches(0.15),
                Inches(0.42), Inches(0.38),
                size=15, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        # Text
        _txtbox(slide, initiative,
                ix + Inches(0.54), iy + Inches(0.14),
                col_w - Inches(0.64), item_h - Inches(0.24),
                size=10, color=WHITE, wrap=True)

    return slide


# ── Slide 7: Strategic Recommendations ────────────────────────────────────

def _slide7(prs: Presentation, content: Dict[str, Any]):
    slide = _blank_slide(prs)
    _header(slide, "Strategic Recommendations")

    recs = content.get("recommendations", [])
    whats_next = content.get("whats_next", "")

    rec_count = min(len(recs), 3)
    if rec_count == 0:
        _txtbox(slide, "No recommendations generated.",
                M, CT + Inches(1), CW, Inches(0.4),
                size=13, color=GRAY, align=PP_ALIGN.CENTER)
        return slide

    rec_w = (CW - Inches(0.3)) / 3
    rec_h = Inches(3.5)
    accents = [GOLD, BLUE_ACC, GREEN]

    for i, rec in enumerate(recs[:3]):
        rx = M + i * (rec_w + Inches(0.15))
        ry = CT + Inches(0.08)
        acc = accents[i % len(accents)]

        _box(slide, rx, ry, rec_w, rec_h, NAVY_CARD)
        _box(slide, rx, ry, rec_w, Inches(0.07), acc)

        # Number
        _txtbox(slide, f"0{i+1}",
                rx + Inches(0.14), ry + Inches(0.16),
                rec_w - Inches(0.22), Inches(0.52),
                size=30, bold=True, color=acc)

        # Title
        title = rec.get("title", "")
        _txtbox(slide, title,
                rx + Inches(0.14), ry + Inches(0.72),
                rec_w - Inches(0.22), Inches(0.64),
                size=12, bold=True, color=WHITE, wrap=True)

        # Body
        body = rec.get("body", "")
        _txtbox(slide, body,
                rx + Inches(0.14), ry + Inches(1.4),
                rec_w - Inches(0.22), rec_h - Inches(1.58),
                size=9, color=GRAY, wrap=True)

    # What's Next
    if whats_next:
        wn_top = CT + rec_h + Inches(0.22)
        _box(slide, M, wn_top, CW, Inches(1.05), NAVY_CARD)
        _txtbox(slide, "WHAT'S NEXT",
                M + Inches(0.14), wn_top + Inches(0.08),
                Inches(1.8), Inches(0.28),
                size=9, bold=True, color=GOLD)
        _txtbox(slide, whats_next,
                M + Inches(0.14), wn_top + Inches(0.36),
                CW - Inches(0.28), Inches(0.62),
                size=9, color=WHITE, wrap=True)

    return slide


# ── Public API ─────────────────────────────────────────────────────────────

_BUILDERS = {
    1: _slide1,
    2: _slide2,
    3: _slide3,
    4: _slide4,
    5: _slide5,
    6: _slide6,
    7: _slide7,
}


def build_pptx(report: Dict[str, Any]) -> bytes:
    """
    Build a Schumacher Homes Monthly Report PPTX from a MonthlySlidesResponse dict.
    Returns raw PPTX bytes ready for download or Drive upload.
    """
    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH

    for slide_data in report.get("slides", []):
        n = slide_data.get("slide_number", 0)
        content = slide_data.get("content", {})
        builder = _BUILDERS.get(n)
        if builder:
            builder(prs, content)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
