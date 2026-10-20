"""The 5 deterministic CDR checks and their skip rules.

Skip rules ("one root problem, one check"):
- duplicates skips rows whose key fields are missing or malformed;
- end_before_start and invalid_duration skip rows with a missing or
  malformed start_time, end_time or duration_sec;
- invalid_duration skips rows that fail end_before_start;
- invalid_phone skips empty numbers (already counted as missing).
"""

from dataclasses import dataclass, field

import pandas as pd

from .schema import (
    DURATION_TOLERANCE_SEC,
    INTEGER_PATTERN,
    PHONE_PATTERN,
    REQUIRED_COLUMNS,
    TIME_FORMAT,
)

CHECK_IDS = [
    "missing_or_malformed",
    "duplicates",
    "end_before_start",
    "invalid_duration",
    "invalid_phone",
]

DUPLICATE_KEY = ["calling_number", "called_number", "start_time"]


@dataclass
class CheckResult:
    check_id: str
    failed_mask: pd.Series  # True where the row fails this check
    details: pd.Series  # short per-row text, "" where the row passes
    breakdown: dict = field(default_factory=dict)

    @property
    def count(self) -> int:
        return int(self.failed_mask.sum())


@dataclass
class _Parsed:
    """Values parsed once and shared by the checks."""

    start: pd.Series
    end: pd.Series
    duration: pd.Series
    start_bad: pd.Series  # missing or malformed
    end_bad: pd.Series
    duration_bad: pd.Series


def _parse(df: pd.DataFrame) -> _Parsed:
    start = pd.to_datetime(df["start_time"], format=TIME_FORMAT, errors="coerce")
    end = pd.to_datetime(df["end_time"], format=TIME_FORMAT, errors="coerce")
    duration_ok = df["duration_sec"].str.fullmatch(INTEGER_PATTERN)
    duration = pd.to_numeric(df["duration_sec"].where(duration_ok), errors="coerce")
    return _Parsed(start, end, duration, start.isna(), end.isna(), ~duration_ok)


def _join_details(parts: list[pd.Series], index: pd.Index) -> pd.Series:
    """Join per-row detail fragments with "; ", skipping empty ones."""
    frame = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=index)
    return frame.apply(lambda row: "; ".join(p for p in row if p), axis=1).reindex(
        index, fill_value=""
    )


def check_missing_or_malformed(df: pd.DataFrame, p: _Parsed) -> CheckResult:
    parts = []
    for col in REQUIRED_COLUMNS:
        empty = df[col] == ""
        parts.append(pd.Series("", index=df.index).mask(empty, f"{col} missing"))
    malformed = {
        "start_time": p.start_bad,
        "end_time": p.end_bad,
        "duration_sec": p.duration_bad,
    }
    for col, bad in malformed.items():
        is_malformed = bad & (df[col] != "")
        parts.append(pd.Series("", index=df.index).mask(is_malformed, f"{col} malformed"))
    details = _join_details(parts, df.index)
    return CheckResult("missing_or_malformed", details != "", details)


def check_duplicates(df: pd.DataFrame, p: _Parsed) -> CheckResult:
    key_ok = (df["calling_number"] != "") & (df["called_number"] != "") & ~p.start_bad
    eligible = df[key_ok]
    is_copy = eligible.duplicated(subset=DUPLICATE_KEY, keep="first")
    original_id = eligible.groupby(DUPLICATE_KEY, sort=False)["record_id"].transform("first")
    failed = is_copy.reindex(df.index, fill_value=False)
    details = ("copy of record_id " + original_id[is_copy]).reindex(df.index, fill_value="")
    return CheckResult("duplicates", failed, details)


def _times_ok(p: _Parsed) -> pd.Series:
    return ~(p.start_bad | p.end_bad | p.duration_bad)


def check_end_before_start(df: pd.DataFrame, p: _Parsed) -> CheckResult:
    failed = _times_ok(p) & (p.end < p.start)
    details = pd.Series("", index=df.index).mask(failed, "end_time before start_time")
    return CheckResult("end_before_start", failed, details)


def check_invalid_duration(
    df: pd.DataFrame, p: _Parsed, end_before_start: CheckResult
) -> CheckResult:
    eligible = _times_ok(p) & ~end_before_start.failed_mask
    expected = (p.end - p.start).dt.total_seconds()
    non_positive = eligible & (p.duration <= 0)
    mismatch = (
        eligible
        & ~non_positive
        & ((p.duration - expected).abs() > DURATION_TOLERANCE_SEC)
    )
    details = pd.Series("", index=df.index).mask(non_positive, "negative/zero")
    mismatch_text = "mismatch (expected " + expected.round().astype("Int64").astype(str) + " s)"
    details = details.mask(mismatch, mismatch_text)
    breakdown = {"negative_zero": int(non_positive.sum()), "mismatch": int(mismatch.sum())}
    return CheckResult("invalid_duration", non_positive | mismatch, details, breakdown)


def check_invalid_phone(df: pd.DataFrame, p: _Parsed) -> CheckResult:
    parts = []
    for col in ["calling_number", "called_number"]:
        bad = (df[col] != "") & ~df[col].str.fullmatch(PHONE_PATTERN)
        parts.append(pd.Series("", index=df.index).mask(bad, f"{col} invalid"))
    details = _join_details(parts, df.index)
    return CheckResult("invalid_phone", details != "", details)


def run_all(df: pd.DataFrame) -> list[CheckResult]:
    """Run the 5 checks in PRD order."""
    p = _parse(df)
    end_before_start = check_end_before_start(df, p)
    return [
        check_missing_or_malformed(df, p),
        check_duplicates(df, p),
        end_before_start,
        check_invalid_duration(df, p, end_before_start),
        check_invalid_phone(df, p),
    ]
