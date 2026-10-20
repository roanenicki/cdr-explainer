"""HTML snippets for the page header, verdict banner, metric and check cards.

Pure functions returning strings (no Streamlit), so tests can check them.
Every piece of text inserted into the HTML goes through html.escape.
"""

import base64
from html import escape

from . import explain
from .report import Report

ACCENT = "#1E40AF"
BORDER = "#E5E7EB"
MUTED = "#6B7280"
SECONDARY = "#4B5563"  # darker grey for body text that must read well on video
TEXT = "#1F2937"

# status -> (text/border color, background color)
STATUS_COLORS = {
    "green": ("#15803D", "#ECFDF3"),
    "orange": ("#B45309", "#FFF7ED"),
    "red": ("#B91C1C", "#FEF2F2"),
}

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)
_ICON_BODIES = {
    "check": '<circle cx="10" cy="10" r="8.5"/><path d="M6.5 10.2l2.4 2.4 4.6-4.9"/>',
    "warning": '<path d="M10 2.5l8 14.5H2z"/><path d="M10 8v4"/><path d="M10 14.6v.1"/>',
    "cross": '<circle cx="10" cy="10" r="8.5"/><path d="M7 7l6 6M13 7l-6 6"/>',
}

STYLE = f"""<style>
[data-testid="stMainBlockContainer"] {{ max-width: 1100px; padding-top: 4.5rem; }}
.cdr-header h1 {{ color: {ACCENT}; font-size: 2.2rem; font-weight: 700; margin: 0; padding: 0; }}
.cdr-header p {{ color: {MUTED}; font-size: 1.05rem; margin: .35rem 0 0 0; }}
.cdr-file {{ color: {SECONDARY}; font-size: .95rem; }}
.cdr-banner {{ border-radius: 8px; border-left: 6px solid; padding: 1.4rem 1.6rem; }}
.cdr-banner .score {{ font-size: 56px; font-weight: 700; line-height: 1.05; }}
.cdr-banner .score small {{ font-size: 18px; font-weight: 500; color: {MUTED}; margin-left: .5rem; }}
.cdr-banner .verdict {{ font-size: 20px; font-weight: 600; margin-top: .4rem; color: {TEXT}; }}
.cdr-banner .main-issues {{ font-size: 1rem; margin-top: .3rem; color: {SECONDARY}; }}
.cdr-metrics {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.cdr-metric {{ border: 1px solid {BORDER}; border-radius: 8px; padding: .9rem 1rem; }}
.cdr-metric .label {{ font-size: .92rem; color: {SECONDARY}; }}
.cdr-metric .value {{ font-size: 2rem; font-weight: 600; color: {TEXT}; line-height: 1.2; margin-top: .2rem; }}
/* Check cards: 3 + 2 on a 6-column grid, every card the same height. */
.cdr-cards {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); grid-auto-rows: 1fr; gap: 12px; }}
.cdr-card {{ grid-column: span 2; display: flex; flex-direction: column; background: #FFFFFF;
  border: 1px solid {BORDER}; border-radius: 8px; padding: 1rem 1.1rem; }}
.cdr-card:nth-child(n+4) {{ grid-column: span 3; }}
.cdr-card .name {{ display: flex; align-items: center; gap: .5rem; font-weight: 600; color: {TEXT};
  font-size: .98rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.cdr-card .count {{ font-size: 1.6rem; font-weight: 700; line-height: 1.2; margin: .45rem 0 .3rem 0; }}
.cdr-card .impact {{ font-size: .95rem; color: {SECONDARY}; line-height: 1.4; }}
.cdr-card .breakdown {{ font-size: .9rem; color: {TEXT}; margin-top: auto; padding-top: .5rem; }}
.cdr-clean {{ border-radius: 8px; padding: .9rem 1.1rem; font-weight: 600; }}
@media (max-width: 900px) {{
  .cdr-cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .cdr-card, .cdr-card:nth-child(n+4) {{ grid-column: span 1; }}
  .cdr-card:nth-child(5) {{ grid-column: span 2; }}
  .cdr-card .name {{ white-space: normal; }}
}}
@media (max-width: 560px) {{
  .cdr-cards, .cdr-metrics {{ grid-template-columns: 1fr; }}
  .cdr-card:nth-child(5) {{ grid-column: span 1; }}
}}
</style>"""


def icon(kind: str, color: str) -> str:
    """An <img> with the SVG as a data URI: st.html strips inline <svg> tags."""
    svg = _SVG.format(color=color, body=_ICON_BODIES[kind])
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img src="{uri}" width="20" height="20" alt="{kind}">'


def page_header(title: str, subtitle: str) -> str:
    return f'<div class="cdr-header"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>'


def file_line(name: str) -> str:
    return f'<div class="cdr-file">File: {escape(name)}</div>'


def verdict_banner(report: Report) -> str:
    color, background = STATUS_COLORS[report.status]
    main_issues = ""
    if report.main_issues:
        main_issues = f'<div class="main-issues">{escape(report.main_issues)}</div>'
    return (
        f'<div class="cdr-banner" style="background:{background};border-color:{color}">'
        f'<div class="score" style="color:{color}">{escape(explain.format_score(report.score_pct))}'
        f"<small>valid rows</small></div>"
        f'<div class="verdict">{escape(report.verdict)}</div>'
        f"{main_issues}"
        "</div>"
    )


def metric_cards(report: Report) -> str:
    """Total / valid / error rows; the error count takes the status color when above 0."""
    error_color = STATUS_COLORS[report.status][0] if report.error_rows else TEXT
    metrics = [
        ("Total rows", report.total_rows, TEXT),
        ("Valid rows", report.valid_rows, TEXT),
        ("Rows with errors", report.error_rows, error_color),
    ]
    cards = "".join(
        f'<div class="cdr-metric"><div class="label">{escape(label)}</div>'
        f'<div class="value" style="color:{color}">{value:,}</div></div>'
        for label, value, color in metrics
    )
    return f'<div class="cdr-metrics">{cards}</div>'


def clean_message() -> str:
    color, background = STATUS_COLORS["green"]
    return (
        f'<div class="cdr-clean" style="color:{color};background:{background}">'
        f"{escape(explain.CLEAN_TABLE_MESSAGE)}</div>"
    )


def _failed_look(status: str) -> tuple[str, str]:
    """Icon and color for a failed check: red files get a cross, others a warning."""
    if status == "red":
        return "cross", STATUS_COLORS["red"][0]
    return "warning", STATUS_COLORS["orange"][0]


def check_cards(report: Report) -> str:
    cards = []
    for check in report.checks:
        if check.count == 0:
            kind, color = "check", STATUS_COLORS["green"][0]
        else:
            kind, color = _failed_look(report.status)
        breakdown = ""
        if check.breakdown:
            breakdown = f'<div class="breakdown">{escape(explain.duration_breakdown(check.breakdown))}</div>'
        cards.append(
            '<div class="cdr-card">'
            f'<div class="name">{icon(kind, color)}<span>{escape(check.name)}</span></div>'
            f'<div class="count" style="color:{color}">{escape(explain.issues(check.count))}</div>'
            f'<div class="impact">{escape(check.impact)}</div>'
            f"{breakdown}"  # pinned to the card's bottom so it can't shift the rows above
            "</div>"
        )
    return f'<div class="cdr-cards">{"".join(cards)}</div>'
