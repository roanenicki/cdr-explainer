"""Reading uploads: forgiving headers, and a clear FileProblem for unusable files."""

import pytest

from cdr_explainer.loader import CANT_READ, NO_RECORDS, FileProblem, load_cdrs
from cdr_explainer.report import analyze

HEADER = "record_id,calling_number,called_number,start_time,end_time,duration_sec,call_type,cell_id"
ROW = "R1,+237612345678,+237698765432,2026-10-15 10:00:00,2026-10-15 10:01:00,60,MOC,CM1234"


def problem(data: bytes) -> FileProblem:
    with pytest.raises(FileProblem) as info:
        load_cdrs(data)
    return info.value


def test_binary_file_is_not_a_csv():
    p = problem(b"\x89PNG\r\n\x1a\n\x00\x00\x00IHDR")
    assert p.message == CANT_READ and not p.is_warning


def test_other_separator_is_not_a_csv():
    assert problem(f"{HEADER}\n{ROW}\n".replace(",", ";").encode()).message == CANT_READ


def test_malformed_rows_are_not_a_csv():
    assert problem(f"{HEADER}\n{ROW},extra,cells,here\n".encode()).message == CANT_READ


@pytest.mark.parametrize("data", [b"", b"   \n\n", f"{HEADER}\n".encode()])
def test_empty_or_headers_only(data):
    p = problem(data)
    assert p.message == NO_RECORDS
    assert p.is_warning  # nothing to check is not a failure: amber, not red


def test_missing_columns_are_listed():
    header = HEADER.replace("start_time,", "").replace("duration_sec,", "")
    row = "R1,+237612345678,+237698765432,2026-10-15 10:01:00,MOC,CM1234"
    p = problem(f"{header}\n{row}\n".encode())
    assert p.message == "This file is missing required columns: start_time, duration_sec."
    assert p.show_expected_columns and not p.is_warning
    assert p.markdown() == (
        "This file is missing required columns: `start_time`, `duration_sec`.\n\n"
        "Expected columns:\n"
        "- Required: `record_id`, `calling_number`, `called_number`, `start_time`, `end_time`, `duration_sec`\n"
        "- Optional: `call_type`, `cell_id`"
    )


def test_mixed_case_and_spaced_headers_are_accepted():
    header = " Record_ID , CALLING_NUMBER,Called_Number,start_time ,END_TIME,Duration_Sec"
    df = load_cdrs(f"{header}\n{ROW.rsplit(',', 2)[0]}\n".encode())
    assert df.loc[0, "record_id"] == "R1"
    assert df.loc[0, "call_type"] == ""  # missing optional columns are added empty


def test_extra_columns_are_ignored():
    df = load_cdrs(f"{HEADER},operator_note\n{ROW},hello\n".encode())
    assert "operator_note" not in df.columns
    assert analyze(f"{HEADER},operator_note\n{ROW},hello\n".encode()).score_pct == 100.0


def test_utf8_bom_and_latin1_exports_load():
    assert load_cdrs(f"﻿{HEADER}\n{ROW}\n".encode("utf-8")).loc[0, "record_id"] == "R1"
    latin1 = f"{HEADER}\n{ROW.replace('CM1234', 'Yaoundé')}\n".encode("latin-1")
    assert load_cdrs(latin1).loc[0, "cell_id"] == "Yaoundé"


def test_row_numbers_are_file_lines():
    df = load_cdrs(f"{HEADER}\n{ROW}\n{ROW.replace('R1', 'R2')}\n".encode())
    assert list(df["row_number"]) == [2, 3]


def test_short_row_counts_as_missing_fields():
    short = ROW.rsplit(",", 3)[0]  # stops after end_time: duration_sec missing
    report = analyze(f"{HEADER}\n{short}\n".encode())
    assert [c.count for c in report.checks] == [1, 0, 0, 0, 0]
    assert report.anomalies.loc[0, "details"] == "duration_sec missing"
