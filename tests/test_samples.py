"""The proof: each sample's report matches the planted errors exactly, and the
committed sample files match the generator byte for byte."""

import json
from pathlib import Path

import pytest

from cdr_explainer.report import analyze
from cdr_explainer.samples import expected_json_bytes, generate, to_csv_bytes

DATA = Path(__file__).resolve().parent.parent / "data"
EXPECTED = json.loads((DATA / "expected_counts.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["sample_dirty.csv", "sample_clean.csv"])
def test_report_matches_expected_counts(name):
    want = EXPECTED[name]
    report = analyze((DATA / name).read_bytes())
    assert report.total_rows == want["total"]
    assert report.valid_rows == want["valid"]
    assert report.error_rows == want["error_rows"]
    assert report.score_pct == want["score_pct"]
    assert report.status == want["status"]
    assert {c.check_id: c.count for c in report.checks} == want["checks"]
    assert len(report.anomalies) == want["error_rows"]


def test_dirty_sample_headline():
    report = analyze((DATA / "sample_dirty.csv").read_bytes())
    assert report.score_pct == 94.9
    assert report.verdict == "Review before sending: 51 rows have issues."
    assert [c.count for c in report.checks] == [15, 8, 6, 12, 10]
    assert report.checks[3].breakdown == {"negative_zero": 6, "mismatch": 6}


def test_clean_sample_headline():
    report = analyze((DATA / "sample_clean.csv").read_bytes())
    assert report.score_pct == 100.0
    assert report.status == "green"
    assert report.verdict == "No issues found."
    assert report.anomalies.empty


def test_duplicate_copies_name_their_original():
    report = analyze((DATA / "sample_dirty.csv").read_bytes())
    dupes = report.anomalies[report.anomalies["checks_failed"] == "Duplicate records"]
    assert len(dupes) == 8
    assert dupes["details"].str.fullmatch(r"copy of record_id CDR\d{6}").all()


def test_committed_samples_match_generator():
    """Drift test: re-running the generator must reproduce data/ exactly."""
    dirty, clean, expected = generate(seed=42)
    assert (DATA / "sample_dirty.csv").read_bytes() == to_csv_bytes(dirty)
    assert (DATA / "sample_clean.csv").read_bytes() == to_csv_bytes(clean)
    assert (DATA / "expected_counts.json").read_bytes() == expected_json_bytes(expected)
