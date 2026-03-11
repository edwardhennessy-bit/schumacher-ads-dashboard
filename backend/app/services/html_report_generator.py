"""
HTML Report Generator for Schumacher Homes Monthly Performance Reports.

Generates a beautiful, self-contained HTML file from MonthlySlidesResponse data.
The output is a single file with all CSS inline — no external dependencies required.
Suitable for browser viewing, email, print-to-PDF, and archiving.
"""

import html as _html
from typing import Any, Dict, List, Optional

# ── Brand palette ─────────────────────────────────────────────────────────────
ORANGE      = "#D4601A"
ORANGE_DARK = "#B54E12"
ORANGE_BG   = "#FBF0E8"
NAVY        = "#1a2744"
NAVY_LIGHT  = "#243564"
GREEN       = "#15803D"
GREEN_BG    = "#DCFCE7"
RED         = "#DC2626"
RED_BG      = "#FEE2E2"
AMBER       = "#B45309"
AMBER_BG    = "#FEF3C7"
GRAY_50     = "#F9FAFB"
GRAY_100    = "#F3F4F6"
GRAY_200    = "#E5E7EB"
GRAY_400    = "#9CA3AF"
GRAY_600    = "#4B5563"
GRAY_700    = "#374151"
GRAY_800    = "#1F2937"
WHITE       = "#FFFFFF"

GOOGLE_BLUE  = "#1a73e8"
META_BLUE    = "#1877F2"
MSFT_TEAL    = "#0078d4"


# ── Utility helpers ───────────────────────────────────────────────────────────

def e(text: Any) -> str:
    """HTML-escape a value."""
    return _html.escape(str(text)) if text is not None else ""


def fmt_currency(value: Any) -> str:
    try:
        v = float(value)
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v:,.0f}"
        return f"${v:,.2f}"
    except (ValueError, TypeError):
        return str(value) if value else "—"


def fmt_number(value: Any) -> str:
    try:
        v = float(value)
        if v >= 1_000:
            return f"{v:,.0f}"
        return f"{int(v)}"
    except (ValueError, TypeError):
        return str(value) if value else "—"


def fmt_pct(value: Any, positive_is_good: bool = True) -> str:
    """Format a percentage change with colored arrow."""
    try:
        v = float(value)
        if v > 0:
            color = GREEN if positive_is_good else RED
            return f'<span class="change-up" style="color:{color}">↑ +{abs(v):.1f}%</span>'
        elif v < 0:
            color = RED if positive_is_good else GREEN
            return f'<span class="change-down" style="color:{color}">↓ {v:.1f}%</span>'
        return f'<span style="color:{GRAY_400}">—</span>'
    except (ValueError, TypeError):
        return f'<span style="color:{GRAY_400}">—</span>'


def badge(status: str) -> str:
    """Colored status pill badge."""
    s = str(status).strip().lower()
    if s in ("on track", "healthy", "good", "stable", "completed"):
        bg, fg, dot = GREEN_BG, GREEN, "●"
    elif s in ("in progress", "mixed", "lagging"):
        bg, fg, dot = AMBER_BG, AMBER, "●"
    elif s in ("off track", "issues detected", "poor", "not started"):
        bg, fg, dot = RED_BG, RED, "●"
    else:
        bg, fg, dot = GRAY_100, GRAY_600, "●"
    return (
        f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:999px;'
        f'font-size:12px;font-weight:600;white-space:nowrap;display:inline-flex;'
        f'align-items:center;gap:5px">{dot} {e(status)}</span>'
    )


def section_header(title: str, subtitle: str = "") -> str:
    sub_html = f'<p style="color:{GRAY_600};font-size:14px;margin:4px 0 0">{e(subtitle)}</p>' if subtitle else ""
    return f"""
    <div style="margin-bottom:28px">
      <h2 style="font-size:26px;font-weight:700;color:{NAVY};margin:0;
                 border-bottom:2px dashed {ORANGE};padding-bottom:10px;display:inline-block">
        {e(title)}
      </h2>
      {sub_html}
    </div>"""


def stat_bar(stats: List[Dict]) -> str:
    """Orange full-width summary stat bar."""
    cells = ""
    for s in stats:
        cells += f"""
        <div style="text-align:center;padding:0 24px;border-right:1px solid rgba(255,255,255,0.25);
                    flex:1;min-width:130px">
          <div style="font-size:28px;font-weight:800;color:{WHITE};letter-spacing:-0.5px">{s['value']}</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:3px;text-transform:uppercase;
                      letter-spacing:0.5px">{e(s['label'])}</div>
        </div>"""
    return f"""
    <div style="background:linear-gradient(135deg,{ORANGE},{ORANGE_DARK});border-radius:12px;
                display:flex;align-items:center;padding:20px 0;margin-bottom:28px;
                box-shadow:0 4px 15px rgba(212,96,26,0.3)">
      {cells}
    </div>"""


def insights_panel(title: str, items: List[str], accent: str = ORANGE) -> str:
    """Right-side insights/callout panel."""
    lis = "".join(
        f'<li style="margin-bottom:10px;padding-left:4px">{e(item)}</li>'
        for item in items if item
    )
    return f"""
    <div style="background:{accent};border-radius:12px;padding:24px;height:100%;box-sizing:border-box">
      <h4 style="color:{WHITE};font-size:14px;font-weight:700;margin:0 0 14px;
                 text-transform:uppercase;letter-spacing:0.5px">{e(title)}</h4>
      <ul style="color:{WHITE};font-size:13.5px;line-height:1.6;margin:0;
                 padding-left:18px;list-style:disc">
        {lis}
      </ul>
    </div>"""


def two_col(left_html: str, right_html: str, left_pct: int = 60) -> str:
    right_pct = 100 - left_pct - 2
    return f"""
    <div style="display:grid;grid-template-columns:{left_pct}% {right_pct}%;gap:24px;align-items:start">
      <div>{left_html}</div>
      <div>{right_html}</div>
    </div>"""


def table_header_row(*cols: str, bg: str = NAVY) -> str:
    ths = "".join(
        f'<th style="padding:10px 14px;text-align:left;font-size:12px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap">{e(c)}</th>'
        for c in cols
    )
    return f'<tr style="background:{bg};color:{WHITE}">{ths}</tr>'


def table_subheader(label: str, bg: str = GRAY_100, colspan: int = 8) -> str:
    return (
        f'<tr style="background:{bg}">'
        f'<td colspan="{colspan}" style="padding:8px 14px;font-size:12px;font-weight:700;'
        f'color:{WHITE};background:{bg}">{e(label)}</td>'
        f'</tr>'
    )


# ── Section renderers ─────────────────────────────────────────────────────────

def render_cover(slide: Dict, report_month: str) -> str:
    content = slide.get("content", {})
    headline = content.get("headline", f"Performance Report — {report_month}")
    agenda = content.get("agenda", [])
    agenda_items = "".join(
        f"""<li style="display:flex;align-items:flex-start;gap:14px;margin-bottom:16px">
              <span style="background:{ORANGE};color:{WHITE};border-radius:50%;width:28px;height:28px;
                           display:flex;align-items:center;justify-content:center;font-weight:700;
                           font-size:13px;flex-shrink:0">{i+1}</span>
              <span style="font-size:16px;color:rgba(255,255,255,0.9);padding-top:4px">{e(item)}</span>
            </li>"""
        for i, item in enumerate(agenda)
    )
    return f"""
<section id="cover" class="page-section" style="background:{NAVY};min-height:420px;
  border-radius:16px;padding:60px;margin-bottom:40px;position:relative;overflow:hidden;
  box-shadow:0 8px 40px rgba(26,39,68,0.25)">
  <!-- Decorative circle -->
  <div style="position:absolute;right:-80px;bottom:-80px;width:320px;height:320px;
              border-radius:50%;background:rgba(212,96,26,0.12)"></div>
  <div style="position:absolute;right:40px;top:-60px;width:200px;height:200px;
              border-radius:50%;background:rgba(255,255,255,0.04)"></div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:48px;position:relative">
    <!-- Left -->
    <div>
      <div style="font-size:11px;font-weight:600;color:{ORANGE};text-transform:uppercase;
                  letter-spacing:1.5px;margin-bottom:12px">Single Grain × Schumacher Homes</div>
      <h1 style="font-size:42px;font-weight:800;color:{WHITE};line-height:1.15;margin:0 0 8px">
        {e(headline)}
      </h1>
      <div style="width:60px;height:4px;background:{ORANGE};border-radius:2px;margin:16px 0 24px"></div>
      <p style="color:rgba(255,255,255,0.55);font-size:13px">{e(report_month)}</p>
    </div>
    <!-- Right: Agenda -->
    <div style="padding-top:8px">
      <div style="font-size:11px;font-weight:600;color:{ORANGE};text-transform:uppercase;
                  letter-spacing:1.5px;margin-bottom:16px">Agenda</div>
      <ul style="list-style:none;margin:0;padding:0">{agenda_items}</ul>
    </div>
  </div>
</section>"""


def render_paid_media(slide: Dict) -> str:
    content = slide.get("content", {})
    period = content.get("period", "")
    loc_count = content.get("locations_count", "")
    subtitle = f"Ad Platform Data | {period}" + (f" | {loc_count} Locations" if loc_count else "")

    # Summary stat bar
    sb = content.get("summary_bar", {})
    stats = []
    if sb.get("total_spend"):
        stats.append({"value": fmt_currency(sb["total_spend"]), "label": "Total Spend"})
    if sb.get("total_leads"):
        stats.append({"value": fmt_number(sb["total_leads"]), "label": "Leads"})
    if sb.get("blended_cpl"):
        stats.append({"value": fmt_currency(sb["blended_cpl"]), "label": "Avg CPL"})
    if sb.get("total_opportunities"):
        stats.append({"value": fmt_number(sb["total_opportunities"]), "label": "Quotes (Tracked)"})
    if sb.get("blended_cpo") and float(sb.get("blended_cpo", 0)) > 0:
        stats.append({"value": fmt_currency(sb["blended_cpo"]), "label": "Cost / Opp"})

    stat_bar_html = stat_bar(stats) if stats else ""

    # MoM table — group by platform
    mom_rows = content.get("mom_table", [])
    platform_colors = {
        "google": GOOGLE_BLUE,
        "meta": META_BLUE,
        "microsoft": MSFT_TEAL,
        "bing": MSFT_TEAL,
    }
    current_platform = None
    rows_html = ""
    row_idx = 0
    for row in mom_rows:
        platform = str(row.get("platform", "")).lower()
        display_platform = row.get("platform", "")
        if platform != current_platform:
            current_platform = platform
            color = platform_colors.get(platform, NAVY)
            rows_html += (
                f'<tr style="background:{color}">'
                f'<td colspan="5" style="padding:8px 14px;font-size:12px;font-weight:700;'
                f'color:{WHITE};text-transform:uppercase;letter-spacing:0.5px">'
                f'{e(display_platform)} Ads</td></tr>'
            )

        metric = e(row.get("metric", ""))
        is_curr = row.get("is_currency", False)
        curr_val = fmt_currency(row.get("current")) if is_curr else fmt_number(row.get("current"))
        prev_val = fmt_currency(row.get("previous")) if is_curr else fmt_number(row.get("previous"))
        change = row.get("change", 0)
        is_pos = row.get("is_positive", True)
        bg = WHITE if row_idx % 2 == 0 else GRAY_50
        row_idx += 1
        rows_html += f"""
        <tr style="background:{bg};border-bottom:1px solid {GRAY_200}">
          <td style="padding:10px 14px;font-size:13.5px;color:{GRAY_700}">{metric}</td>
          <td style="padding:10px 14px;font-size:13.5px;color:{GRAY_800};font-weight:600">{curr_val}</td>
          <td style="padding:10px 14px;font-size:13.5px;color:{GRAY_400}">{prev_val}</td>
          <td style="padding:10px 14px;font-size:13.5px">{fmt_pct(change, is_pos)}</td>
        </tr>"""

    table_html = f"""
    <div style="border-radius:10px;overflow:hidden;border:1px solid {GRAY_200};
                box-shadow:0 1px 4px rgba(0,0,0,0.06)">
      <table style="width:100%;border-collapse:collapse">
        <thead>
          {table_header_row("Metric", "Feb 2026", "Jan 2026", "MoM Change")}
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>""" if rows_html else ""

    # Insights panel
    takeaways = content.get("key_takeaways", [])
    next_steps = content.get("next_steps", [])
    insight_items = list(takeaways) + (["— Next Steps —"] if next_steps else []) + list(next_steps)
    right_html = insights_panel("Key Takeaways & Next Steps", insight_items)

    left_html = table_html
    main_content = two_col(left_html, right_html, 62)

    return f"""
<section id="paid-media" class="page-section">
  {section_header("Paid Media KPIs & MoM Analysis", subtitle)}
  {stat_bar_html}
  {main_content}
</section>"""


def render_scorecard(slide: Dict) -> str:
    content = slide.get("content", {})
    period = content.get("period", "")
    loc_count = content.get("locations_count", "")
    subtitle = "HubSpot Data + Actualized Billing | " + (period or "") + \
               (f" | {loc_count} Locations" if loc_count else "")

    # Stat bar
    sb = content.get("summary_bar", {})
    stats = []
    if sb.get("total_spend"):
        stats.append({"value": fmt_currency(sb["total_spend"]), "label": "Total Spend"})
    if sb.get("total_leads"):
        stats.append({"value": fmt_number(sb["total_leads"]), "label": "Leads"})
    if sb.get("blended_cpl"):
        stats.append({"value": fmt_currency(sb["blended_cpl"]), "label": "Avg CPL"})
    if sb.get("total_visits") or sb.get("visits"):
        v = sb.get("total_visits") or sb.get("visits")
        stats.append({"value": fmt_number(v), "label": "Visits"})
    if sb.get("total_quotes") or sb.get("quotes"):
        q = sb.get("total_quotes") or sb.get("quotes")
        stats.append({"value": fmt_number(q), "label": "Quotes"})

    stat_bar_html = stat_bar(stats) if stats else ""

    def location_table(rows: List[Dict], header_color: str, title: str) -> str:
        if not rows:
            return ""
        row_htmls = ""
        for i, row in enumerate(rows):
            bg = WHITE if i % 2 == 0 else GRAY_50
            cpl_val = float(row.get("cpl", 0) or 0)
            # Color the CPL cell based on threshold
            cpl_style = f"color:{GREEN};font-weight:700" if cpl_val < 50 else (
                f"color:{RED};font-weight:700" if cpl_val > 120 else f"color:{GRAY_800}"
            )
            row_htmls += f"""
            <tr style="background:{bg};border-bottom:1px solid {GRAY_200}">
              <td style="padding:9px 14px;font-size:13px;font-weight:500;color:{NAVY}">{e(row.get("location",""))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right;font-weight:600;color:{GRAY_800}">{fmt_number(row.get("leads",0))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right">{fmt_number(row.get("visits",0))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right">{fmt_number(row.get("quotes",0))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right">{fmt_currency(row.get("spend",0))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right;{cpl_style}">{fmt_currency(cpl_val)}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right;color:{GRAY_600}">{fmt_currency(row.get("cpv",0) or row.get("cost_per_visit",0))}</td>
              <td style="padding:9px 14px;font-size:13px;text-align:right;color:{GRAY_600}">{fmt_currency(row.get("cpq",0) or row.get("cost_per_quote",0))}</td>
            </tr>"""
        return f"""
        <div style="margin-bottom:24px">
          <div style="background:{header_color};color:{WHITE};padding:10px 16px;border-radius:8px 8px 0 0;
                      font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">
            {e(title)}
          </div>
          <div style="border:1px solid {GRAY_200};border-top:none;border-radius:0 0 8px 8px;overflow:hidden">
            <table style="width:100%;border-collapse:collapse">
              <thead>
                <tr style="background:{GRAY_50};border-bottom:1px solid {GRAY_200}">
                  {"".join(f'<th style="padding:8px 14px;font-size:11px;font-weight:600;color:{GRAY_600};text-transform:uppercase;text-align:{"left" if h=="Location" else "right"}">{h}</th>'
                           for h in ["Location","Leads","Visits","Quotes","Spend","CPL","CPV","CPQ"])}
                </tr>
              </thead>
              <tbody>{row_htmls}</tbody>
            </table>
          </div>
        </div>"""

    top_html = location_table(content.get("top_performers", []), GREEN, "🏆 Top Performers — Leads & Visits")
    attn_html = location_table(content.get("needs_attention", []), RED, "⚠ Needs Attention — Low Volume or High CPL")

    left_html = top_html + attn_html

    # Insights
    insights = content.get("key_insights", [])
    focus = content.get("focus_areas", [])
    if isinstance(insights, str):
        insights = [insights]
    if isinstance(focus, str):
        focus = [f for f in focus.split("\n") if f.strip()]
    panel_items = list(insights) + (["— Focus Areas —"] if focus else []) + list(focus)
    right_html = insights_panel("Key Insights & Focus Areas", panel_items)

    return f"""
<section id="scorecard" class="page-section">
  {section_header("Design Center Scorecard", subtitle)}
  {stat_bar_html}
  {two_col(left_html, right_html, 65)}
</section>"""


def render_attribution(slide: Dict) -> str:
    content = slide.get("content", {})

    # Sync status row
    sync_items = [
        ("Google", content.get("google_sync_status", "—")),
        ("Meta", content.get("meta_sync_status", "—")),
        ("Microsoft", content.get("microsoft_sync_status", "—")),
        ("PMax", content.get("pmax_status", "—")),
        ("Meta Pixel", content.get("meta_pixel_status", "—")),
        ("Lead Scoring", content.get("lead_scoring_status", "—")),
    ]
    sync_cards = "".join(f"""
      <div style="background:{GRAY_50};border:1px solid {GRAY_200};border-radius:10px;padding:16px;
                  display:flex;flex-direction:column;gap:8px">
        <div style="font-size:12px;font-weight:600;color:{GRAY_400};text-transform:uppercase;
                    letter-spacing:0.5px">{e(label)}</div>
        <div>{badge(status)}</div>
      </div>""" for label, status in sync_items)

    sync_grid = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px">
      {sync_cards}
    </div>"""

    # Accuracy table
    acc = content.get("accuracy_table", {})
    accuracy_table = ""
    if acc:
        lead_acc = float(acc.get("lead_accuracy", 0) or 0)
        quote_acc = float(acc.get("quote_accuracy", 0) or 0)
        lead_acc_color = GREEN if lead_acc >= 85 else RED
        quote_acc_color = GREEN if quote_acc >= 85 else RED
        target_label = "Target: 85%"

        accuracy_table = f"""
        <div style="border-radius:10px;overflow:hidden;border:1px solid {GRAY_200};margin-bottom:24px">
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr style="background:{NAVY};color:{WHITE}">
                <th style="padding:10px 16px;text-align:left;font-size:12px;font-weight:600;
                           text-transform:uppercase;letter-spacing:0.5px">Metric</th>
                <th style="padding:10px 16px;text-align:right;font-size:12px;font-weight:600">In-Platform</th>
                <th style="padding:10px 16px;text-align:right;font-size:12px;font-weight:600">HubSpot</th>
                <th style="padding:10px 16px;text-align:right;font-size:12px;font-weight:600">Variance</th>
                <th style="padding:10px 16px;text-align:right;font-size:12px;font-weight:600">Accuracy</th>
                <th style="padding:10px 16px;text-align:center;font-size:12px;font-weight:600">{target_label}</th>
              </tr>
            </thead>
            <tbody>
              <tr style="background:{WHITE};border-bottom:1px solid {GRAY_200}">
                <td style="padding:10px 16px;font-size:13.5px;font-weight:500">Leads</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right">{fmt_number(acc.get("platform_leads",0))}</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right">{fmt_number(acc.get("hubspot_leads",0))}</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right;color:{GRAY_600}">+{fmt_number(abs(float(acc.get("lead_variance",0) or 0)))} ({abs(float(acc.get("lead_variance",0) or 0)):.1f}%)</td>
                <td style="padding:10px 16px;font-size:14px;text-align:right;font-weight:700;color:{lead_acc_color}">{lead_acc:.1f}%</td>
                <td style="padding:10px 16px;text-align:center;font-size:18px">{"✅" if lead_acc >= 85 else "❌"}</td>
              </tr>
              <tr style="background:{GRAY_50}">
                <td style="padding:10px 16px;font-size:13.5px;font-weight:500">Quotes / Opps</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right">{fmt_number(acc.get("platform_quotes",0))}</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right">{fmt_number(acc.get("hubspot_quotes",0))}</td>
                <td style="padding:10px 16px;font-size:13.5px;text-align:right;color:{GRAY_600}">+{fmt_number(abs(float(acc.get("quote_variance",0) or 0)))} ({abs(float(acc.get("quote_variance",0) or 0)):.1f}%)</td>
                <td style="padding:10px 16px;font-size:14px;text-align:right;font-weight:700;color:{quote_acc_color}">{quote_acc:.1f}%</td>
                <td style="padding:10px 16px;text-align:center;font-size:18px">{"✅" if quote_acc >= 85 else "❌"}</td>
              </tr>
            </tbody>
          </table>
        </div>"""

    # Action items panel
    action_items = content.get("action_items", [])
    if isinstance(action_items, str):
        action_items = [a.strip() for a in action_items.split("\n") if a.strip()]
    right_html = insights_panel("Action Items", action_items)

    left_html = sync_grid + accuracy_table

    return f"""
<section id="attribution" class="page-section">
  {section_header("Attribution & Data Integrity")}
  {two_col(left_html, right_html, 63)}
</section>"""


def render_creatives(slide: Dict) -> str:
    content = slide.get("content", {})
    creatives = content.get("creatives", [])

    if not creatives:
        placeholder = f"""
        <div style="text-align:center;padding:48px;color:{GRAY_400};background:{GRAY_50};
                    border-radius:12px;border:2px dashed {GRAY_200}">
          <div style="font-size:32px;margin-bottom:8px">🖼</div>
          <p style="font-size:14px;margin:0">No creative data available for this period</p>
        </div>"""
        return f"""
<section id="creatives" class="page-section">
  {section_header("Ad Development & Testing", "Meta | Top Performing Creative")}
  {placeholder}
</section>"""

    cards = ""
    for i, c in enumerate(creatives[:6]):
        rank = i + 1
        thumb = c.get("thumbnail_url") or c.get("image_url") or ""
        img_html = (
            f'<img src="{e(thumb)}" alt="{e(c.get("ad_name",""))}" '
            f'style="width:100%;height:100%;object-fit:cover">'
            if thumb else
            f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;'
            f'font-size:36px;color:{GRAY_200}">🖼</div>'
        )
        cpl_display = fmt_currency(c.get("cpl")) if c.get("cpl") else "—"
        ctr_val = c.get("ctr", 0)
        ctr_display = f"{float(ctr_val):.2f}%" if ctr_val else "—"

        cards += f"""
        <div style="border-radius:12px;overflow:hidden;border:1px solid {GRAY_200};
                    background:{WHITE};box-shadow:0 2px 8px rgba(0,0,0,0.07)">
          <div style="position:relative;height:160px;background:{GRAY_100}">
            {img_html}
            <div style="position:absolute;top:10px;left:10px;background:{NAVY};color:{WHITE};
                        font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px">
              #{rank}
            </div>
          </div>
          <div style="padding:14px">
            <p style="font-size:13px;font-weight:600;color:{GRAY_800};margin:0 0 4px;
                      line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;
                      -webkit-box-orient:vertical;overflow:hidden">
              {e(c.get("ad_name","Unknown Ad"))}
            </p>
            <p style="font-size:11px;color:{GRAY_400};margin:0 0 10px;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              {e(c.get("campaign_name",""))}
            </p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
              <div style="background:{GRAY_50};border-radius:6px;padding:6px 8px;text-align:center">
                <div style="font-size:15px;font-weight:700;color:{NAVY}">{fmt_number(c.get("leads",0))}</div>
                <div style="font-size:10px;color:{GRAY_400};text-transform:uppercase;letter-spacing:0.3px">Leads</div>
              </div>
              <div style="background:{GRAY_50};border-radius:6px;padding:6px 8px;text-align:center">
                <div style="font-size:15px;font-weight:700;color:{NAVY}">{cpl_display}</div>
                <div style="font-size:10px;color:{GRAY_400};text-transform:uppercase;letter-spacing:0.3px">CPL</div>
              </div>
              <div style="background:{GRAY_50};border-radius:6px;padding:6px 8px;text-align:center">
                <div style="font-size:15px;font-weight:700;color:{GRAY_700}">{fmt_currency(c.get("spend",0))}</div>
                <div style="font-size:10px;color:{GRAY_400};text-transform:uppercase;letter-spacing:0.3px">Spend</div>
              </div>
              <div style="background:{GRAY_50};border-radius:6px;padding:6px 8px;text-align:center">
                <div style="font-size:15px;font-weight:700;color:{GRAY_700}">{ctr_display}</div>
                <div style="font-size:10px;color:{GRAY_400};text-transform:uppercase;letter-spacing:0.3px">CTR</div>
              </div>
            </div>
          </div>
        </div>"""

    cards_grid = f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:28px">
      {cards}
    </div>"""

    takeaways = content.get("key_takeaways", [])
    next_steps = content.get("next_steps", [])
    panel_items = list(takeaways) + (["— Next Steps —"] if next_steps else []) + list(next_steps)

    right_panel = insights_panel("Key Takeaways", panel_items) if panel_items else ""
    main = f"""
    <div>
      {cards_grid}
      {f'<div style="max-width:500px">{right_panel}</div>' if right_panel else ""}
    </div>"""

    return f"""
<section id="creatives" class="page-section">
  {section_header("Ad Development & Testing", "Meta | Top Performing Creative")}
  {main}
</section>"""


def render_initiatives(slide: Dict) -> str:
    content = slide.get("content", {})
    initiatives = content.get("initiatives", [])
    if isinstance(initiatives, str):
        initiatives = [i.strip() for i in initiatives.split("\n") if i.strip()]

    items_html = ""
    for i, item in enumerate(initiatives):
        # Split "Title: Body" if colon present
        if ":" in item:
            parts = item.split(":", 1)
            title_part = parts[0].strip()
            body_part = parts[1].strip()
            items_html += f"""
            <div style="display:flex;gap:16px;padding:18px 20px;background:{WHITE};
                        border:1px solid {GRAY_200};border-radius:10px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.05)">
              <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;
                          background:{ORANGE};color:{WHITE};font-weight:700;font-size:14px;
                          display:flex;align-items:center;justify-content:center">{i+1}</div>
              <div>
                <div style="font-size:14px;font-weight:600;color:{NAVY};margin-bottom:3px">{e(title_part)}</div>
                <div style="font-size:13.5px;color:{GRAY_600};line-height:1.5">{e(body_part)}</div>
              </div>
            </div>"""
        else:
            items_html += f"""
            <div style="display:flex;gap:16px;padding:18px 20px;background:{WHITE};
                        border:1px solid {GRAY_200};border-radius:10px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.05)">
              <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;
                          background:{ORANGE};color:{WHITE};font-weight:700;font-size:14px;
                          display:flex;align-items:center;justify-content:center">{i+1}</div>
              <div style="font-size:14px;color:{GRAY_700};line-height:1.5;padding-top:5px">{e(item)}</div>
            </div>"""

    list_html = f'<div style="display:flex;flex-direction:column;gap:12px">{items_html}</div>'

    return f"""
<section id="initiatives" class="page-section">
  {section_header("Current Initiatives & Priority Updates")}
  {list_html}
</section>"""


def render_recommendations(slide: Dict) -> str:
    content = slide.get("content", {})
    recs = content.get("recommendations", [])
    whats_next = content.get("whats_next", [])

    rec_cards = ""
    for i, rec in enumerate(recs):
        if isinstance(rec, dict):
            title = rec.get("title", "")
            body = rec.get("body", rec.get("description", ""))
        else:
            parts = str(rec).split(":", 1)
            title = parts[0].strip() if len(parts) > 1 else f"Recommendation {i+1}"
            body = parts[1].strip() if len(parts) > 1 else str(rec)

        rec_cards += f"""
        <div style="background:{WHITE};border:1px solid {GRAY_200};border-radius:12px;padding:24px;
                    border-left:4px solid {ORANGE};box-shadow:0 2px 8px rgba(0,0,0,0.05)">
          <div style="display:flex;align-items:flex-start;gap:14px">
            <div style="flex-shrink:0;width:36px;height:36px;border-radius:50%;
                        background:{ORANGE_BG};color:{ORANGE};font-weight:800;font-size:16px;
                        display:flex;align-items:center;justify-content:center">{i+1}</div>
            <div>
              <h4 style="font-size:15px;font-weight:700;color:{NAVY};margin:0 0 8px">{e(title)}</h4>
              <p style="font-size:13.5px;color:{GRAY_600};line-height:1.6;margin:0">{e(body)}</p>
            </div>
          </div>
        </div>"""

    if isinstance(whats_next, str):
        whats_next = [w.strip() for w in whats_next.split("\n") if w.strip()]

    right_panel = insights_panel("What's Next", whats_next) if whats_next else ""

    left_html = f'<div style="display:flex;flex-direction:column;gap:16px">{rec_cards}</div>'

    return f"""
<section id="recommendations" class="page-section">
  {section_header("Strategic Recommendations")}
  {two_col(left_html, right_panel, 62) if right_panel else left_html}
</section>"""


# ── CSS ────────────────────────────────────────────────────────────────────────

def get_css() -> str:
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    *, *::before, *::after {{ box-sizing: border-box; }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      background: #F1F3F7;
      color: {GRAY_800};
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}

    .topnav {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(26,39,68,0.97);
      backdrop-filter: blur(8px);
      padding: 0 40px;
      display: flex;
      align-items: center;
      gap: 4px;
      height: 52px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    }}

    .topnav a {{
      color: rgba(255,255,255,0.65);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 999px;
      transition: all 0.15s;
      white-space: nowrap;
      letter-spacing: 0.2px;
    }}

    .topnav a:hover {{
      background: {ORANGE};
      color: white;
    }}

    .topnav .nav-brand {{
      color: white;
      font-size: 13px;
      font-weight: 700;
      margin-right: 12px;
      padding-right: 16px;
      border-right: 1px solid rgba(255,255,255,0.2);
      letter-spacing: -0.3px;
    }}

    .report-wrapper {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 24px 60px;
    }}

    .page-section {{
      background: {WHITE};
      border-radius: 16px;
      padding: 40px;
      margin-bottom: 28px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.06);
      border: 1px solid {GRAY_200};
    }}

    .change-up {{ font-weight: 600; }}
    .change-down {{ font-weight: 600; }}

    table {{ font-size: 13.5px; }}
    th, td {{ vertical-align: middle; }}

    .footer {{
      text-align: center;
      padding: 32px 24px;
      color: {GRAY_400};
      font-size: 12px;
      border-top: 1px solid {GRAY_200};
      margin-top: 8px;
    }}

    @media print {{
      .topnav {{ display: none !important; }}
      body {{ background: white; }}
      .report-wrapper {{ padding: 0; max-width: none; }}
      .page-section {{
        border-radius: 0;
        box-shadow: none;
        border: none;
        margin-bottom: 0;
        page-break-before: always;
      }}
      #cover {{ page-break-before: avoid; }}
    }}

    @media (max-width: 768px) {{
      .report-wrapper {{ padding: 16px; }}
      .page-section {{ padding: 24px 16px; }}
    }}
    """


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_html_report(data: dict) -> str:
    """
    Generate a complete, self-contained HTML report from a MonthlySlidesResponse dict.
    Returns the full HTML string.
    """
    report_month = data.get("report_month", "")
    period_label = data.get("period_label", report_month)
    slides = {s["slide_number"]: s for s in data.get("slides", [])}

    # Render each section
    cover_html        = render_cover(slides.get(1, {}), period_label or report_month)
    paid_media_html   = render_paid_media(slides.get(2, {}))
    scorecard_html    = render_scorecard(slides.get(3, {}))
    attribution_html  = render_attribution(slides.get(4, {}))
    creatives_html    = render_creatives(slides.get(5, {}))
    initiatives_html  = render_initiatives(slides.get(6, {}))
    recs_html         = render_recommendations(slides.get(7, {}))

    nav_links = [
        ("#cover",           "Overview"),
        ("#paid-media",      "Paid Media KPIs"),
        ("#scorecard",       "Scorecard"),
        ("#attribution",     "Attribution"),
        ("#creatives",       "Ad Creative"),
        ("#initiatives",     "Initiatives"),
        ("#recommendations", "Recommendations"),
    ]
    nav_html = "".join(f'<a href="{href}">{label}</a>' for href, label in nav_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Schumacher Homes — {e(period_label or report_month)} Performance Report</title>
  <style>{get_css()}</style>
</head>
<body>

  <nav class="topnav">
    <span class="nav-brand">Schumacher Homes</span>
    {nav_html}
  </nav>

  <div class="report-wrapper">
    {cover_html}
    {paid_media_html}
    {scorecard_html}
    {attribution_html}
    {creatives_html}
    {initiatives_html}
    {recs_html}
  </div>

  <footer class="footer">
    <strong style="color:{GRAY_600}">Single Grain</strong> &nbsp;×&nbsp; Schumacher Homes
    &nbsp;&nbsp;|&nbsp;&nbsp;
    {e(period_label or report_month)} Performance Report
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <em>Proprietary &amp; Confidential</em>
  </footer>

</body>
</html>"""
