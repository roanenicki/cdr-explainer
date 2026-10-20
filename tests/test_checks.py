"""Each check on small hand-built rows, plus the skip rules."""

import pandas as pd

from cdr_explainer.checks import run_all
from cdr_explainer.report import build_report
from cdr_explainer.schema import ALL_COLUMNS

GOOD = {
    "record_id": "R1",
    "calling_number": "+237612345678",
    "called_number": "+237698765432",
    "start_time": "2026-10-15 10:00:00",
    "end_time": "2026-10-15 10:01:00",
    "duration_sec": "60",
    "call_type": "MOC",
    "cell_id": "CM1234",
}


def frame(*overrides: dict) -> pd.DataFrame:
    # Each row gets its own called_number so rows aren't duplicates unless a test says so.
    rows = [
        {**GOOD, "record_id": f"R{i + 1}", "called_number": f"+2376987654{i:02d}", **o}
        for i, o in enumerate(overrides)
    ]
    df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    df.insert(0, "row_number", range(2, len(df) + 2))
    return df


def failures(df: pd.DataFrame) -> list[list[str]]:
    """For each row, the ids of the checks it fails."""
    results = run_all(df)
    return [[r.check_id for r in results if r.failed_mask.iloc[i]] for i in range(len(df))]


def test_valid_row_passes_everything():
    assert failures(frame({})) == [[]]


def test_missing_and_malformed_fields():
    df = frame(
        {"record_id": ""},
        {"start_time": "2026/10/15 10:00"},
        {"duration_sec": "12.5"},
        {"end_time": "2026-10-15 25:00:00"},
    )
    assert failures(df) == [["missing_or_malformed"]] * 4


def test_duplicate_flags_only_the_copy_and_names_original():
    same = {"called_number": GOOD["called_number"]}
    df = frame(same, {**same, "start_time": "2026-10-15 11:00:00", "end_time": "2026-10-15 11:01:00"}, same)
    assert failures(df) == [[], [], ["duplicates"]]
    duplicates = run_all(df)[1]
    assert duplicates.details.iloc[2] == "copy of record_id R1"


def test_duplicate_skips_rows_with_missing_key_field():
    same = {"calling_number": "", "called_number": GOOD["called_number"]}
    df = frame(same, same)
    assert failures(df) == [["missing_or_malformed"]] * 2


def test_end_before_start_is_not_also_a_duration_failure():
    df = frame({"end_time": "2026-10-15 09:59:00"})
    assert failures(df) == [["end_before_start"]]


def test_malformed_time_gets_no_time_check_failure():
    df = frame({"end_time": "not a time", "duration_sec": "-5"})
    assert failures(df) == [["missing_or_malformed"]]


def test_invalid_duration_breakdown():
    df = frame({"duration_sec": "0"}, {"duration_sec": "-60"}, {"duration_sec": "75"}, {"duration_sec": "61"})
    assert failures(df) == [["invalid_duration"]] * 3 + [[]]  # 61 s is within the 1 s tolerance
    duration = run_all(df)[3]
    assert duration.breakdown == {"negative_zero": 2, "mismatch": 1}
    assert duration.details.iloc[2] == "mismatch (expected 60 s)"


def test_invalid_phone_and_empty_phone_only_counts_as_missing():
    df = frame(
        {"calling_number": "+237 612345678"},
        {"called_number": "+2376ABC45678"},
        {"called_number": "12345"},
        {"calling_number": ""},
        {"calling_number": "237612345678"},  # "+" is optional
    )
    assert failures(df) == [
        ["invalid_phone"],
        ["invalid_phone"],
        ["invalid_phone"],
        ["missing_or_malformed"],
        [],
    ]


def test_row_failing_several_checks_counts_once():
    df = frame({}, {"record_id": "", "called_number": "bad"})
    report = build_report(df, run_all(df))
    assert report.error_rows == 1
    assert report.valid_rows == 1
    assert report.anomalies["checks_failed"].iloc[0] == "Missing or malformed fields, Invalid phone numbers"
