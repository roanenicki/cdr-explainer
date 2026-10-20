"""Deterministic synthetic CDR generator: a clean sample and one with planted errors.

Each planted fault sits on its own row and must trip exactly its intended check.
`generate()` verifies that by running the real checks on its own output.
"""

import json
import random
from datetime import datetime, timedelta

import pandas as pd

from .checks import CHECK_IDS, run_all
from .loader import load_cdrs
from .schema import ALL_COLUMNS, TIME_FORMAT

ROWS = 1000
DAY = datetime(2026, 10, 15)

# How many rows of each fault the dirty sample gets.
PLANTED = {
    "missing_or_malformed": 15,
    "duplicates": 8,
    "end_before_start": 6,
    "invalid_duration": 12,
    "invalid_phone": 10,
}

# (column, bad value) pairs for missing/malformed rows, used in order.
MISSING_OR_MALFORMED = [
    ("record_id", ""),
    ("calling_number", ""),
    ("called_number", ""),
    ("start_time", ""),
    ("end_time", ""),
    ("duration_sec", ""),
    ("start_time", "2026/10/15 9:05"),
    ("end_time", "2026-10-15T10:00:00"),
    ("duration_sec", "12.5"),
    ("duration_sec", "abc"),
    ("start_time", "15-10-2026 09:05:00"),
    ("end_time", "2026-10-15 25:00:00"),
    ("record_id", ""),
    ("calling_number", ""),
    ("duration_sec", ""),
]


def _phone(rng: random.Random) -> str:
    return "+2376" + "".join(rng.choice("0123456789") for _ in range(8))


def _record(rng: random.Random, n: int) -> dict:
    start = DAY + timedelta(seconds=rng.randint(0, 23 * 3600))
    duration = rng.randint(1, 3600)
    calling = _phone(rng)
    called = _phone(rng)
    while called == calling:
        called = _phone(rng)
    return {
        "record_id": f"CDR{n:06d}",
        "calling_number": calling,
        "called_number": called,
        "start_time": start.strftime(TIME_FORMAT),
        "end_time": (start + timedelta(seconds=duration)).strftime(TIME_FORMAT),
        "duration_sec": str(duration),
        "call_type": rng.choice(["MOC", "MTC"]),
        "cell_id": f"CM{rng.randint(1000, 9999)}",
    }


def _unique_records(rng: random.Random, count: int) -> list[dict]:
    """Valid records with no two sharing the duplicate key."""
    records, keys = [], set()
    while len(records) < count:
        rec = _record(rng, len(records) + 1)
        key = (rec["calling_number"], rec["called_number"], rec["start_time"])
        if key not in keys:
            keys.add(key)
            records.append(rec)
    return records


def _plant_end_before_start(rec: dict) -> None:
    start = datetime.strptime(rec["start_time"], TIME_FORMAT)
    rec["end_time"] = (start - timedelta(seconds=int(rec["duration_sec"]))).strftime(TIME_FORMAT)


def _plant_invalid_duration(rec: dict, i: int) -> None:
    duration = int(rec["duration_sec"])
    if i % 2 == 0:
        rec["duration_sec"] = "0" if i % 4 == 0 else str(-duration)
    else:
        rec["duration_sec"] = str(duration + 5 + 37 * i)


def _plant_invalid_phone(rec: dict, i: int) -> None:
    col = "calling_number" if i % 2 == 0 else "called_number"
    number = rec[col]
    variants = [
        number[:4] + " " + number[4:],  # space
        number[:6] + "AB" + number[8:],  # letters
        number[:9],  # too few digits
        number + "123456",  # too many digits
        number.replace("+", "00+"),  # "+" in the middle
    ]
    rec[col] = variants[i % len(variants)]


def generate(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (dirty_df, clean_df, expected counts for both)."""
    rng = random.Random(seed)
    clean = _unique_records(rng, ROWS)

    base = _unique_records(rng, ROWS - PLANTED["duplicates"])
    # Distinct base rows: first the originals of the duplicates, then one row per fault.
    picked = rng.sample(range(len(base)), sum(PLANTED.values()))
    originals = set(picked[: PLANTED["duplicates"]])
    fault_rows = iter(picked[PLANTED["duplicates"] :])

    intended = {}  # base index -> check_id
    for col, value in MISSING_OR_MALFORMED:
        idx = next(fault_rows)
        base[idx][col] = value
        intended[idx] = "missing_or_malformed"
    for _ in range(PLANTED["end_before_start"]):
        idx = next(fault_rows)
        _plant_end_before_start(base[idx])
        intended[idx] = "end_before_start"
    for i in range(PLANTED["invalid_duration"]):
        idx = next(fault_rows)
        _plant_invalid_duration(base[idx], i)
        intended[idx] = "invalid_duration"
    for i in range(PLANTED["invalid_phone"]):
        idx = next(fault_rows)
        _plant_invalid_phone(base[idx], i)
        intended[idx] = "invalid_phone"

    dirty, labels = [], []
    next_id = len(base) + 1
    for idx, rec in enumerate(base):
        dirty.append(rec)
        labels.append(intended.get(idx))
        if idx in originals:
            dirty.append({**rec, "record_id": f"CDR{next_id:06d}"})
            labels.append("duplicates")
            next_id += 1

    dirty_df = pd.DataFrame(dirty, columns=ALL_COLUMNS)
    clean_df = pd.DataFrame(clean, columns=ALL_COLUMNS)
    _assert_planted(dirty_df, labels)
    _assert_planted(clean_df, [None] * len(clean_df))

    error_rows = sum(PLANTED.values())
    expected = {
        "sample_dirty.csv": _expected(ROWS, error_rows, "orange", PLANTED),
        "sample_clean.csv": _expected(ROWS, 0, "green", dict.fromkeys(CHECK_IDS, 0)),
    }
    return dirty_df, clean_df, expected


def _expected(total: int, error_rows: int, status: str, checks: dict) -> dict:
    valid = total - error_rows
    return {
        "total": total,
        "valid": valid,
        "error_rows": error_rows,
        "score_pct": (valid * 1000 // total) / 10,
        "status": status,
        "checks": {check_id: checks[check_id] for check_id in CHECK_IDS},
    }


def _assert_planted(df: pd.DataFrame, labels: list) -> None:
    """Every row must fail exactly its intended check (or none)."""
    results = run_all(load_cdrs(to_csv_bytes(df)))
    for row, label in enumerate(labels):
        failed = [r.check_id for r in results if r.failed_mask.iloc[row]]
        want = [label] if label else []
        assert failed == want, f"row {row}: planted {want}, checks found {failed}"


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8")


def expected_json_bytes(expected: dict) -> bytes:
    return (json.dumps(expected, indent=2) + "\n").encode("utf-8")
