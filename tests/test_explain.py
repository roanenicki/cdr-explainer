"""Verdict wording and score thresholds."""

from cdr_explainer.explain import format_score, verdict_text
from cdr_explainer.report import status_for


def test_verdict_clean_file():
    assert verdict_text("green", 100.0, 0) == "No issues found."


def test_verdict_green_with_minor_issues():
    assert verdict_text("green", 99.5, 5) == "Safe to send downstream: 5 rows have minor issues."


def test_verdict_orange():
    assert verdict_text("orange", 94.9, 51) == "Review before sending: 51 rows have issues."


def test_verdict_red_includes_count():
    assert verdict_text("red", 80.0, 200) == (
        "Do not send downstream: send the file back to the source. 200 rows have issues."
    )


def test_verdict_one_row_grammar():
    assert verdict_text("green", 99.9, 1) == "Safe to send downstream: 1 row has minor issues."


def test_status_thresholds():
    assert status_for(100.0) == "green"
    assert status_for(99.0) == "green"
    assert status_for(98.9) == "orange"
    assert status_for(90.0) == "orange"
    assert status_for(89.9) == "red"


def test_format_score():
    assert format_score(100.0) == "100%"
    assert format_score(94.9) == "94.9%"
    assert format_score(99.0) == "99.0%"
