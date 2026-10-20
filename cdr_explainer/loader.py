"""Turn the bytes of an uploaded file into a clean DataFrame of CDRs, or raise
FileProblem with the message the user should see."""

import warnings
from io import StringIO

import pandas as pd

from .schema import ALL_COLUMNS, OPTIONAL_COLUMNS, REQUIRED_COLUMNS

CANT_READ = "This file can't be read as a CSV. Please upload a comma-separated file."
NO_RECORDS = "This file has no call records to check."


class FileProblem(Exception):
    """A file the tool can't check, with a message meant for the user.

    is_warning: True when the file is readable but has nothing to check (empty or
    headers only): not a failure, so the page shows it in amber rather than red.
    """

    def __init__(self, message: str, missing_columns: list[str] | None = None, is_warning: bool = False):
        super().__init__(message)
        self.message = message
        self.missing_columns = missing_columns or []
        self.is_warning = is_warning

    @property
    def show_expected_columns(self) -> bool:
        return bool(self.missing_columns)

    def markdown(self) -> str:
        """The message for the page: column names in code style, expected columns as a list."""
        if not self.missing_columns:
            return self.message
        return (
            f"This file is missing required columns: {_code(self.missing_columns)}.\n\n"
            "Expected columns:\n"
            f"- Required: {_code(REQUIRED_COLUMNS)}\n"
            f"- Optional: {_code(OPTIONAL_COLUMNS)}"
        )


def _code(columns: list[str]) -> str:
    return ", ".join(f"`{c}`" for c in columns)


def _decode(data: bytes) -> str:
    """UTF-8 (with or without BOM) first, then Latin-1 for older exports."""
    if b"\x00" in data:  # binary files (images, spreadsheets) are never CSV text
        raise FileProblem(CANT_READ)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def load_cdrs(data: bytes) -> pd.DataFrame:
    """Read a CDR CSV. Every cell stays text; empty cells stay ""."""
    text = _decode(data)
    if not text.strip():
        raise FileProblem(NO_RECORDS, is_warning=True)
    try:
        with warnings.catch_warnings():
            # Rows with more cells than the header: pandas only warns; treat it as unreadable
            # rather than silently shifting columns (index_col=False stops it using them as an index).
            warnings.simplefilter("error", pd.errors.ParserWarning)
            df = pd.read_csv(StringIO(text), dtype=str, keep_default_na=False, index_col=False)
    except pd.errors.EmptyDataError:
        raise FileProblem(NO_RECORDS, is_warning=True) from None
    except (pd.errors.ParserError, pd.errors.ParserWarning, ValueError):
        raise FileProblem(CANT_READ) from None

    df = df.fillna("")  # short rows: pandas leaves the missing trailing cells as NaN
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]  # "Record_ID" and "record_id": keep the first
    if len(df.columns) == 1 and any(sep in df.columns[0] for sep in ";\t|"):
        raise FileProblem(CANT_READ)  # another separator: not comma-separated
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise FileProblem(
            f"This file is missing required columns: {', '.join(missing)}.",
            missing_columns=missing,
        )
    if df.empty:
        raise FileProblem(NO_RECORDS, is_warning=True)

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[ALL_COLUMNS].apply(lambda s: s.str.strip())
    # File line number: the header is line 1, so the first record is line 2.
    df.insert(0, "row_number", range(2, len(df) + 2))
    return df.reset_index(drop=True)

