"""The banner and card HTML carry the right numbers, colors and order."""

from pathlib import Path

from cdr_explainer.report import analyze
from cdr_explainer.ui_html import check_cards, clean_message, metric_cards, verdict_banner

DATA = Path(__file__).resolve().parent.parent / "data"
DIRTY = analyze((DATA / "sample_dirty.csv").read_bytes())
CLEAN = analyze((DATA / "sample_clean.csv").read_bytes())


def test_dirty_banner_is_orange_with_score_and_verdict():
    html = verdict_banner(DIRTY)
    assert "94.9%" in html
    assert "#B45309" in html and "#FFF7ED" in html
    assert "Review before sending: 51 rows have issues." in html
    assert "Main issues: 15 missing or malformed fields · 12 invalid durations" in html


def test_clean_banner_is_green_100():
    html = verdict_banner(CLEAN)
    assert "100%" in html and "100.0%" not in html
    assert "#15803D" in html
    assert "No issues found." in html
    assert "Main issues" not in html


def test_cards_in_prd_order_with_counts_and_breakdown():
    html = check_cards(DIRTY)
    names = [
        "Missing or malformed fields",
        "Duplicate records",
        "End time before start time",
        "Invalid duration",
        "Invalid phone numbers",
    ]
    positions = [html.index(name) for name in names]
    assert positions == sorted(positions)
    for count in ["15 issues", "8 issues", "6 issues", "12 issues", "10 issues"]:
        assert count in html
    assert "negative/zero: 6 · mismatch: 6" in html


def test_clean_cards_all_pass():
    html = check_cards(CLEAN)
    assert html.count("0 issues") == 5
    assert "#B45309" not in html  # no warning color anywhere


def test_text_is_escaped():
    html = verdict_banner(DIRTY)
    assert "<script" not in html
    assert "can&#x27;t" in check_cards(DIRTY)


def test_error_metric_uses_status_color_only_when_above_zero():
    assert 'style="color:#B45309">51<' in metric_cards(DIRTY)
    clean = metric_cards(CLEAN)
    assert "#15803D" not in clean and "#B45309" not in clean


def test_breakdown_comes_after_the_impact_sentence():
    html = check_cards(DIRTY)
    duration_card = html[html.index("Invalid duration") :]
    assert duration_card.index("billed for the wrong amount") < duration_card.index("negative/zero: 6")


def test_clean_message():
    assert "No anomalous rows: ready to send downstream." in clean_message()
