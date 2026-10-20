"""Turn the bytes of an uploaded file into a clean DataFrame of CDRs."""

from io import BytesIO

import pandas as pd

from .schema import ALL_COLUMNS, OPTIONAL_COLUMNS


def load_cdrs(data: bytes) -> pd.DataFrame:
    """Read a CDR CSV. Every cell stays text; empty cells stay ""."""
    df = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[ALL_COLUMNS].apply(lambda s: s.str.strip())
    # File line number: the header is line 1, so the first record is line 2.
    df.insert(0, "row_number", range(2, len(df) + 2))
    return df.reset_index(drop=True)
