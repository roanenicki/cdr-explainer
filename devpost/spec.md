---
doc: spec
status: approved
---

# CDR Explainer — Technical Spec

## How This Works, In Plain Language
CDR Explainer has two halves:

1. **The engine: plain Python, no Streamlit.** A small package, `cdr_explainer/`, that takes the bytes of a CSV file and returns a **report**: the counts, the score, the verdict and the anomaly rows. It reads the file with pandas, checks the columns, runs the 5 checks and writes the plain-language wording from templates. Because it doesn't know Streamlit exists, pytest can run it directly on the sample files and confirm the exact counts.
2. **The page: `app.py`, Streamlit.** It gets a file (an upload, or one of the two sample buttons), hands it to the engine and draws the report: banner, metric cards, check cards and table.

**Streamlit's one big idea:** `app.py` runs top to bottom on *every* click. A button is only "True" for the one rerun right after it's clicked. To remember which file is loaded, the page stores it in **`st.session_state`**, a small dictionary that survives reruns for that browser tab. Nothing is saved anywhere else.

**The sample files** are made once by a generator with a fixed random seed. They're committed to the repo, together with a file of expected counts. The buttons simply read them, so the samples behave the same locally and on the deployed site. A test re-runs the generator and fails if the committed files no longer match.

Why this shape: it's the smallest layout that keeps your proof ("finds every planted error, nothing else") testable without opening a browser, and it keeps Streamlit-specific code in one file.

## The Core Journey Through the System
PRD ref: `prd.md > The Core Journey`.

1. The tester opens the app → `app.py` runs and draws the header, the uploader and the two sample buttons. `session_state` has no file yet, so no report is shown (`prd.md > States and Boundaries`, first use).
2. They click **"Try a file with errors"** → the button's callback stores `{"name": "sample_dirty.csv", "data": <bytes of data/sample_dirty.csv>}` in `st.session_state["source"]`. Uploading a file does the same, with the uploaded bytes.
3. The script reruns → `app.py` sees a source and calls `analyze(data)` from `cdr_explainer/report.py`.
4. The engine runs: `loader.load_cdrs(data)` reads and validates the CSV (or raises a `FileProblem` with the user-facing message) → `checks.run_all(df)` runs the 5 checks with the skip rules → `report.build_report(...)` computes the score, status and verdict text (via `explain.py`) and the anomaly table.
5. `app.py` draws the result: the verdict banner (HTML from `ui_html.py`), 3 `st.metric` cards, the 5-card grid (HTML), then a check-type `st.selectbox` filter above `st.dataframe(anomalies)`.
6. Picking a filter reruns the script; the report is recomputed from the same `session_state` source (fast at 1,000 rows) and the table shows only that check's rows.
7. If the file is unusable, `app.py` catches `FileProblem` and shows `st.error(message)` (plus the expected-column list when relevant) instead of the report. A traceback is never shown.

## Stack
| Piece | Version | Why | Docs |
|---|---|---|---|
| Python | 3.13 locally (3.12+ fine on Cloud) | learner's language | https://docs.python.org/3/ |
| Streamlit | `==1.51.0` (pinned) | learner's choice for a fast data UI. Pinned because the custom HTML can break across versions | https://docs.streamlit.io |
| pandas | `==2.3.3` | learner's strength; vectorised checks | https://pandas.pydata.org/docs/ |
| pytest | `==9.0.2` | automated proof of exact counts | https://docs.pytest.org |

Key Streamlit APIs: `st.session_state` (https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state), `st.file_uploader`, `st.button(on_click=...)`, `st.metric`, `st.dataframe`, `st.selectbox`, theming (https://docs.streamlit.io/develop/concepts/configuration/theming).

The versions shown are the ones installed on this machine. Verify early in the build that a fresh `.venv` installs them cleanly.

## Where It Runs and How Someone Tries It
**Local (always works, and the fallback):**
```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
streamlit run app.py            # opens http://localhost:8501
pytest                          # runs all tests
python scripts/generate_samples.py   # only when changing the samples
```
No API key is needed.

**Deployed (learner's choice): Streamlit Community Cloud.** Connect the public GitHub repo, set the main file to `app.py`, and pick Python 3.12 or 3.13 in the advanced settings. Cloud installs from `requirements.txt`. It's free and needs a Streamlit account linked to GitHub. Docs: https://docs.streamlit.io/deploy/streamlit-community-cloud. **Deployment must never block submission.** If it fails, ship with local + video. Done at `6-ship`.

**Demo recording:** start locally (or use the live link) → "Try a file with errors" (94.9%, orange, 15/8/6/12/10) → filter the table by one check → "Try a clean file" (100% green) → one real upload.

## Look and Feel
From `prd.md > Look and Feel` (Stripe-like, sober, light, status colors only for status).

- **Theme** (`.streamlit/config.toml`): `client.toolbarMode="minimal"` (hides Deploy and the menu), `base="light"`, `primaryColor="#1E40AF"` (deep blue: buttons, focus), `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#F6F8FA"`, `textColor="#1F2937"`. Default sans-serif font.
- **Status palette (used only in the banner and check cards):** green `#15803D` on `#ECFDF3`, orange `#B45309` on `#FFF7ED`, red `#B91C1C` on `#FEF2F2`. Neutral border `#E5E7EB`, secondary text `#6B7280`.
- **Title:** "CDR Explainer" in the accent blue, with one grey explanatory line below.
- **Verdict banner:** full width, status background, a thin left border in the status color, the score number at about 56px bold and the verdict text at about 20px semibold.
- **Verdict banner extra line:** "Main issues: …" (top 2 checks by count, from `explain.main_issues`), hidden when clean.
- **Metric cards:** custom HTML (`ui_html.metric_cards`), because `st.metric` can't color its value. "Rows with errors" takes the status color when above 0.
- **Check cards:** a 6-column CSS grid laid out 3 + 2 (top cards span 2, bottom cards span 3), equal heights (`grid-auto-rows: 1fr`); 2 columns under 900px with the 5th card full width, 1 column under 560px. White with a neutral border and 8px radius. Each card has a status icon (an SVG check, warning or cross as an `<img>` data URI, no emoji), the one-line check name, a large bold count ("0 issues" in green when passed) and the impact sentence in dark grey (`#4B5563`). The Invalid duration card adds a "negative/zero: N · mismatch: M" line pinned to the card's bottom.
- **Clean table state:** "No anomalous rows: ready to send downstream." in a green box instead of the filter and table.
- Generous white space, `layout="wide"` capped at 1100px (decided in the build).
- **Copy tone:** plain, factual, operator language. No exclamation marks, no AI wording.

## Components

### Schema (`cdr_explainer/schema.py`)
The constants: `REQUIRED_COLUMNS` (in order: record_id, calling_number, called_number, start_time, end_time, duration_sec), `OPTIONAL_COLUMNS` (call_type, cell_id), `TIME_FORMAT = "%Y-%m-%d %H:%M:%S"`, `PHONE_PATTERN = r"^\+?\d{10,15}$"` and `DURATION_TOLERANCE_SEC = 1`.
PRD ref: `prd.md > Input File Format`.

### Loader (`cdr_explainer/loader.py`)
`load_cdrs(data: bytes) -> pd.DataFrame`, which raises `FileProblem(message, show_expected_columns: bool)`.
- `pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)`, so every cell stays as text and empty cells stay `""` (nothing is guessed). Values are stripped of whitespace.
- A decode or parse error → "This file can't be read as a CSV. Please upload a comma-separated file."
- Headers are normalized (`strip().lower()`) before matching. Extra columns are dropped. Missing optional columns are added empty.
- Missing required columns → "This file is missing required columns: [list]." (`show_expected_columns=True`).
- Zero data rows, or no bytes at all → "This file has no call records to check."
- It keeps the file order and adds `row_number` (= file line number, where the header is line 1), so testers can find rows.
PRD ref: `prd.md > Input File Format`, `prd.md > States and Boundaries`.

### Checks (`cdr_explainer/checks.py`)
Each check is a function `df -> CheckResult` with fields `check_id`, `name`, `failed_mask` (a boolean Series), `details` (a Series of short per-row text) and an optional `breakdown` dict. `run_all(df)` runs them in PRD order and applies the skip rules:
1. `missing_or_malformed`: any required field equals `""`, or `start_time`/`end_time` fails `pd.to_datetime(format=TIME_FORMAT, errors="coerce")`, or `duration_sec` doesn't match `^-?\d+$`. Detail: which field(s), e.g. "start_time malformed".
2. `duplicates`: `df.duplicated(subset=[calling_number, called_number, start_time], keep="first")`. Detail: "copy of record_id X" (the first occurrence's ID). *Derived rule:* rows where any of those three key fields is missing or malformed are excluded from this check, under the same "one root problem, one check" principle.
3. `end_before_start`: parsed end < parsed start. Skips rows where start, end or duration is missing or malformed.
4. `invalid_duration`: duration ≤ 0 → "negative/zero". Otherwise |duration − (end − start)| > 1 s → "mismatch (expected N s)". Skips rows with malformed time fields and rows failing check 3. Breakdown: the two counts.
5. `invalid_phone`: a non-empty `calling_number` or `called_number` doesn't match `PHONE_PATTERN`. Empty numbers are skipped (they're already in check 1). Detail: which number.
PRD ref: `prd.md > Anomaly Checks`.

### Report (`cdr_explainer/report.py`)
`analyze(data: bytes) -> Report` (the only function `app.py` needs) and `build_report(df, results) -> Report`.
`Report` (a dataclass) holds `total_rows`, `valid_rows`, `error_rows`, `score_pct` (one decimal), `status` (`"green"|"orange"|"red"`), `verdict`, `checks` (a list of check summaries with name, count, impact and breakdown) and `anomalies` (a DataFrame with row_number, all 8 CDR columns, `checks_failed` joined with ", ", and `details`).
- A valid row fails zero checks. `score = valid / total`.
- Status: ≥ 99 → green, ≥ 90 → orange, otherwise red.
PRD ref: `prd.md > Health Score and Verdict`, `prd.md > Anomaly Table`.

### Explanations (`cdr_explainer/explain.py`)
This is the **only place user-facing wording is written.** It holds the 5 check names and impact sentences (verbatim from the PRD) and `verdict_text(status, score_pct, error_rows)`:
- 100% → "No issues found."
- green → "Safe to send downstream: X rows have minor issues."
- orange → "Review before sending: X rows have issues."
- red → "Do not send downstream: send the file back to the source." followed by the count (e.g. "X rows have issues.")
- "1 row has" vs. "X rows have" is handled for correct grammar.

**AI hook:** a future `ai_summary.py` would take the `Report` and return a paragraph. If no key is present, the app skips it. Nothing is built for it now. Only this boundary is reserved.
PRD ref: `prd.md > Anomaly Checks` (impact sentences), `prd.md > Health Score and Verdict`, `prd.md > Deferred From the POC`.

### UI HTML snippets (`cdr_explainer/ui_html.py`)
Pure functions that return HTML strings: `verdict_banner(report)`, `check_cards(report)` and the inline-SVG icons. They contain no Streamlit, so tests can assert things like "contains 94.9%". All text inserted into the HTML is escaped with `html.escape`.
PRD ref: `prd.md > Screens and Layout`, `prd.md > Look and Feel`, `prd.md > Check Cards`.

### Page (`app.py`)
- `st.set_page_config(page_title="CDR Explainer", layout=...)`, then the header.
- The uploader (`type=["csv"]`, `on_change` callback) and two buttons (`on_click` callbacks) all write `st.session_state["source"]`. The most recent action wins.
- If a source is present: the current file name is shown in small grey, then `try: report = analyze(...)`, and on `except FileProblem` the error is shown (plus the expected-column list).
- It draws the banner (`st.markdown(..., unsafe_allow_html=True)`), 3 `st.metric` columns and the cards, then `st.selectbox("Show", ["All checks", *check names])` and `st.dataframe(filtered, hide_index=True)`.
PRD ref: `prd.md > The Core Journey`, `prd.md > Screens and Layout`.

### Sample generator (`cdr_explainer/samples.py` + `scripts/generate_samples.py`)
`generate(seed=42) -> (dirty_df, clean_df, expected: dict)`. The script writes `data/sample_dirty.csv`, `data/sample_clean.csv` and `data/expected_counts.json`, with UTF-8 and `\n` line endings.
- **Clean:** 1,000 valid voice CDRs. The numbers are `+2376` + 8 digits, start times fall within one day, `duration_sec` is exactly end − start (1–3,600 s), `call_type` is MOC/MTC and `cell_id` is a short code.
- **Dirty:** 992 valid base rows plus 8 duplicate copies inserted after their originals (1,000 total). On 43 *other* distinct base rows, each one gets exactly **one** planted fault:
  - 15 missing/malformed, a mix of empty fields and bad formats (e.g. `2026/10/20 9:05`, `12.5`)
  - 6 end-before-start, with the duration kept positive
  - 12 invalid duration, a mix of ≤ 0 values and mismatches > 1 s, with valid times
  - 10 invalid phone numbers, e.g. spaces, letters or too few digits, with non-empty values
- The originals of the duplicates stay valid. Each fault row must trip only its intended check. The generator asserts this by running `checks.run_all` on its own output.
- `expected_counts.json` contains `{total, valid, error_rows, score_pct, status, checks: {id: count}}` for both files.
PRD ref: `prd.md > Sample Files`.

### Tests (`tests/`)
- `test_samples.py`: (a) for each sample, `analyze()` matches `expected_counts.json` exactly (dirty: 1000 / 949 / 51, 94.9, orange, 15/8/6/12/10; clean: 100, green, all zeros). (b) **Drift test:** `generate(seed=42)` serialized to text equals the committed files byte for byte.
- `test_checks.py`: a small hand-built DataFrame per check, plus the skip rules (malformed time → no time-check failure; end-before-start → no duration failure; empty phone → only check 1; a multi-failure row counted once).
- `test_loader.py`: not a CSV, empty file, headers only, missing columns (message lists them), mixed-case or spaced headers accepted, extra columns ignored.
- `test_explain.py`: verdict text for 100%, green < 100, orange, red, and 1 row vs. many.
PRD ref: every "Acceptance" list in `prd.md > Features and Behavior`.

## Data Model
| Data | Where it lives | How it updates | On leaving/returning |
|---|---|---|---|
| Current file (`name`, `bytes`) | `st.session_state["source"]` | set by the uploader or button callbacks | lost when the tab closes. Fine: nothing persists (`prd.md > States and Boundaries`) |
| Report | recomputed on every rerun from the source | `analyze()` | not stored |
| Table filter | the widget's own state | the user picks | reset with the session |
| Sample files + expected counts | `data/` in the repo | only via `scripts/generate_samples.py` + commit | permanent |

## File Structure
```
cdr-explainer/
├── app.py                      # Streamlit page: input, session_state, drawing only
├── cdr_explainer/              # the engine, with no Streamlit imports
│   ├── __init__.py
│   ├── schema.py               # column names, formats, phone pattern, tolerance
│   ├── loader.py               # bytes → clean DataFrame, or FileProblem
│   ├── checks.py               # the 5 checks + skip rules
│   ├── report.py               # Report dataclass, analyze(), score/status/anomalies
│   ├── explain.py              # all user-facing wording (AI summary hook point)
│   ├── ui_html.py              # banner + check-card HTML strings, icons
│   └── samples.py              # deterministic synthetic CDR generator
├── scripts/
│   └── generate_samples.py     # writes data/ from samples.generate()
├── data/
│   ├── sample_dirty.csv        # 1,000 rows, 51 planted errors (synthetic)
│   ├── sample_clean.csv        # 1,000 rows, 0 errors (synthetic)
│   └── expected_counts.json    # what the report must show for each
├── tests/
│   ├── test_samples.py         # exact counts + drift test
│   ├── test_checks.py
│   ├── test_loader.py
│   └── test_explain.py
├── .streamlit/
│   └── config.toml             # light theme, deep-blue accent
├── requirements.txt            # pinned: streamlit, pandas, pytest
├── .gitattributes              # *.csv text eol=lf, so the drift test is stable on Windows
├── .gitignore                  # .venv, __pycache__, .env, learner profile
├── README.md                   # what it is, run, test, deploy, Next steps (AI summary)
└── devpost/                    # planning docs
```

## External Services and Dependencies
- **Streamlit Community Cloud** (optional deploy): free, needs a GitHub-linked account, and reads `requirements.txt`. https://docs.streamlit.io/deploy/streamlit-community-cloud
- **No external APIs in the PoC.** Gemini is deferred and gets no key or calls now.

## Important Failure Modes
- **Unusable upload** → a `FileProblem` message from the PRD in `st.error`. Never a traceback. As a last guard, `app.py` wraps `analyze()` in a generic `except Exception` that shows "Something went wrong reading this file." and logs the error.
- **Odd encodings** (e.g. a Latin-1 export) → the loader tries UTF-8 (with BOM handling), then Latin-1, before giving up with the can't-read message.
- **Custom HTML renders badly after a Streamlit change** → the version is pinned. Plain `st.metric`/`st.dataframe` still convey every number if the styling degrades.
- **Deploy fails** → local + video (`Where It Runs and How Someone Tries It`).
- **Line-ending drift on Windows** → `.gitattributes` + the generator writes `\n`.

## What Was Simplified and Why
- **Recompute on every rerun** instead of caching. At 1,000 rows it's instant. Caching (`st.cache_data`) is easy to add later if large files matter.
- **Committed sample files** instead of generating at startup. They're instant, identical everywhere, and guarded by the drift test.
- **Custom HTML for only two elements** (banner, cards). Everything else uses built-in widgets to limit fragility.
- **No AI summary module.** Only the `explain.py` boundary is reserved (deferred until 2026-10-23, per `prd.md > Deferred From the POC`).

## Decisions and Open Issues
**Learner decisions:**
- Python + Streamlit + pandas + pytest (carried from scope/PRD).
- The engine is plain Python with no Streamlit and fully tested. `app.py` only loads and draws.
- Deploy to Streamlit Community Cloud. Local + video is the fallback, and deployment never blocks submission.
- Sample files committed, with a **drift test** that fails if they differ from the generator output.
- Theme file + minimal custom HTML. Streamlit pinned.
- `.venv` + pinned `requirements.txt`.

**Implementation details proposed by the agent and confirmed by the learner at review:**
- The duplicate check excludes rows with a missing or malformed key field (follows "one root problem, one check").
- The red verdict also states the count ("…source. X rows have issues."), satisfying "always includes the real number."
- The anomaly table adds `row_number` (file line) so testers can find rows.
- Encoding fallback: UTF-8 first, then Latin-1.
- The uploader uses `type=["csv"]`, so Streamlit itself rejects other file extensions. Content that still can't be parsed gets the PRD message.

**The useful unknown:** Streamlit's rerun model, a new tool and the learner's stated learning goal. Clarified in the conversation: the script reruns on every click, buttons are True for only one rerun, and `st.session_state` holds the loaded file. To check during the build: click a sample button, then change the table filter, and confirm the report stays (the session_state is working).

**Open:** none blocking `5-build`. Verify early that the pinned versions install in a fresh `.venv`.
