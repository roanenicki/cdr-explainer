# CDR Explainer

Upload a file of voice call detail records (CDRs) and see in seconds whether it's safe to send downstream, what's wrong with it, and why it matters for billing.

Telecom testers still check by hand whether a received CDR file is complete and consistent. It's slow, and errors are easy to miss. CDR Explainer already knows what a CDR is: it runs telecom-specific checks out of the box and explains each failure as its billing impact, topped by a colored health verdict.

> **Schema:** this version uses a **built-in, simplified voice CDR schema** (the columns below). It doesn't read a data flow's own specification yet — see [Next steps](#next-steps).

## What it checks

Five deterministic checks, in plain Python (no AI): the same file always gives the same result.

| Check | Flags a row when… | Why it matters |
|---|---|---|
| Missing or malformed fields | a required field is empty, a time isn't `YYYY-MM-DD HH:MM:SS`, or the duration isn't an integer | the call can't be rated |
| Duplicate records | same caller + receiver + start time as an earlier row (only the extra copies) | the customer would be billed twice |
| End time before start time | `end_time` is earlier than `start_time` | duration and price can't be trusted |
| Invalid duration | `duration_sec` ≤ 0, or differs from end − start by more than 1 s | the call would be billed wrong, or not at all |
| Invalid phone numbers | a number isn't E.164-style: optional `+`, then 10–15 digits | the call can't be matched to an account |

A row counts once in the health score, however many checks it fails. To avoid counting one root problem twice, time checks skip rows with malformed times, the duration check skips end-before-start rows, and the phone check skips empty numbers.

**Health score** = valid rows / total rows. ≥ 99% green, 90–99% orange, < 90% red.

## Input format

A comma-separated file with a header row. Column names are matched ignoring case and surrounding spaces; extra columns are ignored.

| Column | Required | Format |
|---|---|---|
| `record_id` | yes | any ID |
| `calling_number` | yes | E.164-style, e.g. `+237612345678` |
| `called_number` | yes | E.164-style |
| `start_time` | yes | `YYYY-MM-DD HH:MM:SS` |
| `end_time` | yes | `YYYY-MM-DD HH:MM:SS` |
| `duration_sec` | yes | integer seconds |
| `call_type` | no | e.g. `MOC` / `MTC` (shown, not checked) |
| `cell_id` | no | shown, not checked |

UTF-8 and Latin-1 files are accepted. Unusable files get a clear message instead of a report.

## Run it locally

Requires Python 3.12 or 3.13. No API key needed.

```
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py              # opens http://localhost:8501
```

Click **Try a file with errors** or **Try a clean file**, or upload your own CSV.

## Tests

```
pytest
```

The tests prove the report finds exactly the planted errors in the sample file (1,000 rows, 51 errors: 15 / 8 / 6 / 12 / 10 → 94.9%, orange) and that the clean sample is 100% green. A drift test fails if the committed sample files no longer match the generator.

## Sample data

All data is **synthetic**: no real customer data. `data/` is generated with a fixed seed:

```
python scripts/generate_samples.py
```

It writes `sample_dirty.csv`, `sample_clean.csv` and `expected_counts.json`. Each planted fault sits on its own row, and the generator checks that every fault trips exactly its intended check.

## Deploy (optional)

On [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud): connect this GitHub repo, set the main file to `app.py`, and pick Python 3.12 or 3.13. It installs from `requirements.txt`.

## Project layout

```
app.py                  Streamlit page: input, session state, drawing
cdr_explainer/          the engine, no Streamlit
  schema.py             columns, formats, phone pattern, tolerance
  loader.py             bytes → clean table, or a clear file problem
  checks.py             the 5 checks and skip rules
  report.py             score, status, verdict, anomaly table
  explain.py            all user-facing wording
  ui_html.py            banner and card HTML
  samples.py            synthetic CDR generator
scripts/generate_samples.py
data/                   sample files + expected counts
tests/
```

## Next steps

1. **Configurable schema:** load each data flow's spec (fields, formats, rules) from a file, so the tool adapts to any mediation flow instead of the built-in simplified voice CDR schema.
2. **Optional AI summary** (e.g. Gemini): a short plain-language paragraph on top of the report when an API key is present, with the current templates as the fallback. `explain.py` is the place it plugs in.
3. More telecom checks (data and SMS CDRs, `cell_id` and `call_type` rules).
4. A dedicated report export (today the table's own download icon exports the filtered rows).
5. Efficient handling of very large files (millions of rows).
