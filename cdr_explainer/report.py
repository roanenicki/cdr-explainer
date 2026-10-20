"""Build the report the page draws: counts, score, verdict, check summaries, anomalies."""

from dataclasses import dataclass

import pandas as pd

from . import explain
from .checks import CheckResult, run_all
from .loader import load_cdrs
from .schema import ALL_COLUMNS

GREEN_MIN = 99.0
ORANGE_MIN = 90.0


@dataclass
class CheckSummary:
    check_id: str
    name: str
    count: int
    impact: str
    breakdown: dict


@dataclass
class Report:
    total_rows: int
    valid_rows: int
    error_rows: int
    score_pct: float  # one decimal, rounded down so errors never show as 100%
    status: str  # "green" | "orange" | "red"
    verdict: str
    checks: list[CheckSummary]
    anomalies: pd.DataFrame  # row_number, the 8 CDR columns, checks_failed, details


def analyze(data: bytes) -> Report:
    """The only function the page needs: file bytes in, report out."""
    df = load_cdrs(data)
    return build_report(df, run_all(df))


def status_for(score_pct: float) -> str:
    if score_pct >= GREEN_MIN:
        return "green"
    if score_pct >= ORANGE_MIN:
        return "orange"
    return "red"


def _join_non_empty(frame: pd.DataFrame, sep: str) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=str, index=frame.index)
    return frame.apply(lambda row: sep.join(v for v in row if v), axis=1)


def build_report(df: pd.DataFrame, results: list[CheckResult]) -> Report:
    failed = pd.concat({r.check_id: r.failed_mask for r in results}, axis=1)
    any_failed = failed.any(axis=1)
    total = len(df)
    error_rows = int(any_failed.sum())
    valid = total - error_rows
    score_pct = (valid * 1000 // total) / 10 if total else 0.0
    status = status_for(score_pct)

    checks = [
        CheckSummary(
            check_id=r.check_id,
            name=explain.CHECK_NAMES[r.check_id],
            count=r.count,
            impact=explain.CHECK_IMPACTS[r.check_id],
            breakdown=r.breakdown,
        )
        for r in results
    ]

    names = pd.DataFrame(
        {r.check_id: r.failed_mask.map({True: explain.CHECK_NAMES[r.check_id], False: ""})
         for r in results}
    )
    details = pd.concat([r.details for r in results], axis=1)
    anomalies = df.loc[any_failed, ["row_number", *ALL_COLUMNS]].copy()
    anomalies["checks_failed"] = _join_non_empty(names[any_failed], ", ")
    anomalies["details"] = _join_non_empty(details[any_failed], "; ")

    return Report(
        total_rows=total,
        valid_rows=valid,
        error_rows=error_rows,
        score_pct=score_pct,
        status=status,
        verdict=explain.verdict_text(status, score_pct, error_rows),
        checks=checks,
        anomalies=anomalies.reset_index(drop=True),
    )
