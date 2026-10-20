"""All user-facing wording: check names, impact sentences and the verdict.

AI hook: a future `ai_summary.py` would take a Report and return a paragraph,
shown only when a key is present. These templates stay the fallback.
"""

CHECK_NAMES = {
    "missing_or_malformed": "Missing or malformed fields",
    "duplicates": "Duplicate records",
    "end_before_start": "End time before start time",
    "invalid_duration": "Invalid duration",
    "invalid_phone": "Invalid phone numbers",
}

CHECK_IMPACTS = {
    "missing_or_malformed": (
        "These calls can't be rated: they will be rejected or billed with missing information."
    ),
    "duplicates": (
        "These calls were recorded twice: customers would be billed twice for the same call."
    ),
    "end_before_start": (
        "These calls have impossible times: their duration and price can't be trusted."
    ),
    "invalid_duration": (
        "These calls have a wrong duration: they would be billed for the wrong amount, or not at all."
    ),
    "invalid_phone": (
        "These calls can't be matched to a customer account: the revenue would be lost."
    ),
}


def rows_have(n: int) -> str:
    return "1 row has" if n == 1 else f"{n:,} rows have"


def issues(n: int) -> str:
    return "1 issue" if n == 1 else f"{n:,} issues"


def duration_breakdown(breakdown: dict) -> str:
    return f"negative/zero: {breakdown['negative_zero']} · mismatch: {breakdown['mismatch']}"


def verdict_text(status: str, score_pct: float, error_rows: int) -> str:
    if error_rows == 0:
        return "No issues found."
    if status == "green":
        return f"Safe to send downstream: {rows_have(error_rows)} minor issues."
    if status == "orange":
        return f"Review before sending: {rows_have(error_rows)} issues."
    return f"Do not send downstream: send the file back to the source. {rows_have(error_rows)} issues."


def format_score(score_pct: float) -> str:
    """"100%" for a perfect file, otherwise one decimal ("94.9%")."""
    return "100%" if score_pct == 100 else f"{score_pct:.1f}%"
