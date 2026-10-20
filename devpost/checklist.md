---
doc: checklist
status: approved
---

# Build Checklist

Build mode: learn

## Slices

- [x] **1. Click "Try a file with errors" and get the right verdict and counts**
  Becomes usable: `streamlit run app.py` opens a plain page with the title, the explanatory line and the two sample buttons. Clicking "Try a file with errors" shows 94.9%, orange, "Review before sending: 51 rows have issues.", the 3 metrics, the 5 check counts (15 / 8 / 6 / 12 / 10) with their impact sentences, and the anomaly table with a working check filter. "Try a clean file" shows 100%, green, "No issues found." Styling is plain Streamlit for now.
  Why now: This is the unique kernel (CDR-aware checks + business-impact wording) and the proof ("finds every planted error, nothing else"). It also exercises the one unfamiliar piece, Streamlit's rerun model and `st.session_state`, on the very first slice. Bootstrapping (venv, pinned requirements, `.gitignore`, `.gitattributes`) lives here.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Anomaly Checks`, `prd.md > Health Score and Verdict`, `prd.md > Anomaly Table`, `prd.md > Sample Files`
  Spec ref: `spec.md > Stack`, `spec.md > Components` (Schema, Loader basic path, Checks, Report, Explanations, Sample generator, Page, Tests), `spec.md > Data Model`, `spec.md > File Structure`
  Build: Create `.venv` and pinned `requirements.txt`; add `.gitattributes`. Write `schema.py`, `loader.py` (happy path: read as text, normalize headers, add `row_number`), `checks.py` (5 checks + skip rules), `explain.py`, `report.py` (`analyze()`), `samples.py` + `scripts/generate_samples.py`, then generate and commit `data/`. Write `app.py` with the header, two sample buttons using `on_click` callbacks into `st.session_state["source"]`, plain verdict text, 3 `st.metric`, check counts + impact as plain text, and `st.selectbox` + `st.dataframe`. Tests: `test_samples.py` (exact counts + drift test), `test_checks.py` (each check + skip rules), `test_explain.py`.
  Verify (mechanical): A fresh `.venv` installs `requirements.txt` cleanly; `pytest` passes; a Streamlit `AppTest` script clicks "Try a file with errors" and confirms 94.9% / 51 / 15-8-6-12-10, changes the filter and confirms the report is still there with the right row count, then clicks "Try a clean file" and confirms 100% / "No issues found."; `streamlit run app.py` starts with no errors.
  Learner check: Run `streamlit run app.py`, click "Try a file with errors" and compare the numbers to the planted errors (51 rows, 15/8/6/12/10). Change the table filter to "Duplicate records": you should see 8 rows, each naming its original `record_id`, and the report should stay on screen. Then click "Try a clean file": 100%, "No issues found."
  Commit: `Analyze sample CDR files with the 5 checks and show the report`

- [x] **2. The report looks like a real operator tool**
  Becomes usable: The same report, now in the Stripe-like look: deep-blue title, the big colored verdict banner, metric cards, a grid of 5 check cards with check/warning/cross icons, "0 issues" in green for passed checks, and the "negative/zero: N · mismatch: M" line on the Invalid duration card.
  Why now: The numbers are proven, so styling can't hide a wrong count. The look is what judges see first in a 2-minute video, and it's the learner's second learning goal (a polished Streamlit interface), so it comes before the less visible upload edge cases.
  PRD ref: `prd.md > Screens and Layout`, `prd.md > Look and Feel`, `prd.md > Check Cards`
  Spec ref: `spec.md > Look and Feel`, `spec.md > Components` (UI HTML snippets, Page)
  Build: Add `.streamlit/config.toml` (light theme, deep-blue accent). Write `ui_html.py` (`verdict_banner`, `check_cards`, inline-SVG icons, all text escaped). Replace the plain verdict and check text in `app.py` with the HTML banner and card grid; pick centered vs. max-width wide layout. Show the current file name in small grey.
  Verify (mechanical): `pytest` still passes; a quick script confirms `verdict_banner()` contains "94.9%" and the orange colors for the dirty sample and `check_cards()` contains all 5 names in order plus the duration breakdown; `AppTest` runs `app.py` with no exceptions for both samples.
  Learner check: Open the app, click both sample buttons and look at the page as if you were a judge seeing it for 5 seconds. Is the verdict readable at a glance? Do the cards feel calm and professional? Try narrowing the browser window: the cards should wrap.
  Commit: `Style the report: verdict banner, check cards and theme`

- [x] **3. Upload your own file, and bad files get a clear message**
  Becomes usable: Uploading a CSV replaces the current report (the most recent action wins). Unusable files show a clear message instead of a traceback: not a CSV, empty or headers only, or missing required columns (with the full expected-column list). Mixed-case or spaced headers and extra columns are accepted. A Latin-1 export still loads.
  Why now: The core journey already works end to end on the samples. This completes the "real upload" step of the journey and the error states, which depend on the loader already being in place.
  PRD ref: `prd.md > The Core Journey` (step 2), `prd.md > Input File Format`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Components` (Loader, Page), `spec.md > Important Failure Modes`
  Build: Finish `loader.py`: `FileProblem`, the PRD messages, UTF-8/BOM then Latin-1 fallback, empty/headers-only and missing-column handling. Add `st.file_uploader(type=["csv"], on_change=...)` to `app.py`, `st.error` for `FileProblem` plus the expected-column list, and the generic `except Exception` guard. Write `tests/test_loader.py`. Write `README.md` (what it is, run, test, deploy, Next steps: AI summary).
  Verify (mechanical): `pytest` passes, including `test_loader.py` (not a CSV, empty, headers only, missing columns, header case/spaces, extra columns, Latin-1); `AppTest` confirms an uploaded file's source replaces the sample and that a bad file shows the error message with no exception.
  Learner check: Upload a copy of `data/sample_dirty.csv` with a column deleted, then one with the headers in uppercase, then an empty `.csv` file. Each should either show the report or a clear one-line message, never a red Python error.
  Commit: `Support CSV uploads with clear file error messages`

## Hands-on Checkpoints

- [x] Early usable behavior explored — after slice 1: the numbers, the wording and the filter/rerun behavior, while the look is still open to change in slice 2
  Feedback: all three learner checks passed. Requested: reset the table filter to "All checks" when a new file loads; show a perfect score as "100%" (others keep one decimal). Both done and verified before the slice 1 commit.
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence:
Route and stops:
Edit outcome:
Reflection:
Activity mode:

## Revisions
- Banner, cards and header render with `st.html` instead of `st.markdown(unsafe_allow_html=True)`, and the card icons are SVG `<img>` data URIs — Streamlit 1.51's HTML sanitizer strips inline `<svg>` tags, found when checking the page in a real browser.
- Layout is `wide` capped at 1100px, with the 5 check cards on one row (2 columns under 900px, 1 under 560px) — the centered layout and auto-fit grid wrapped the cards 4+1.
- The anomaly table shows `row_number`, `checks_failed` and `details` first — with the original column order, the columns that say what's wrong were off-screen to the right.
- Slice 2 learner review added: hidden Streamlit toolbar, a "Main issues" line in the banner, 3 + 2 equal-height check cards with the breakdown pinned to the bottom, darker/larger secondary text, status-colored "Rows with errors", and a green message instead of an empty table for clean files — PRD (Look and Feel, Health Score and Verdict, Check Cards, Anomaly Table) and spec (Look and Feel) updated to match. Metric cards became custom HTML because `st.metric` can't color its value. A CSV download button was considered and declined: `st.dataframe`'s built-in download icon already exports the filtered rows, so export stays under Later.
- The loader also treats as "can't be read as a CSV": files containing NUL bytes (binary), single-column files whose header contains `;`, tab or `|`, and rows with more cells than the header (pandas otherwise silently shifted them into an index). Rows with fewer cells get "" for the missing cells, so they count as missing fields. Duplicate header names after normalizing keep the first — found while writing `test_loader.py`.
- README states the built-in simplified voice CDR schema, and lists "Configurable schema" first under Next steps (learner request); PRD's Possible Later Enhancements updated to match.
- Slice 3 learner review: a sample click now clears the uploader (versioned widget key) so only one file is ever active; empty/headers-only files show an amber warning instead of a red error; the missing-columns message uses code-style names and a bulleted expected-column list — PRD (States and Boundaries) and spec (Page) updated.
