---
doc: prd
status: approved
---

# CDR Explainer — Product Requirements

A local web tool for telecom data testers and analysts. It checks a file of voice call detail records (CDRs) and says in seconds whether the file is safe to send downstream, what's wrong with it and why it matters for billing.
Source: `scope.md > The Unique Kernel`, `scope.md > Who It's For`.

## The Core Journey
Source: `scope.md > The Core Loop`, `scope.md > What "Working" Looks Like`.

1. The tester starts the app and it opens in the browser on a single page: the title **CDR Explainer**, one line explaining what it does, a CSV upload control and two sample buttons: **"Try a file with errors"** and **"Try a clean file"**.
2. They upload a CDR CSV or click one of the sample buttons.
3. In about a second, the report appears below on the same page:
   1. **Verdict banner:** a big health score and verdict text in green, orange or red.
   2. **Metric cards:** total rows, valid rows, rows with errors.
   3. **Check cards:** one per check, with the failed-row count and a one-sentence business impact.
   4. **Anomaly table:** the failing rows, filterable by check.
4. They filter the table to see exactly which rows to fix, then fix and re-check, or send the file back.
5. **Success:** the dirty sample shows exactly the planted errors, and the clean sample shows 100% green with "No issues found."

## Screens and Layout
One page, top to bottom:
1. **Header:** the title "CDR Explainer" (accent blue), one explanatory line, then the upload control and the "Try a file with errors" / "Try a clean file" buttons.
2. **Report** (only after a file is loaded): the verdict banner → a row of metric cards → a grid of 5 check cards → the anomaly table with a check-type filter.
3. **File error message** (replaces the report when the file is unusable). See `States and Boundaries`.

## Look and Feel
Source: `scope.md > Inspiration & Identity`.
- **Reference:** the Stripe dashboard. A sober, professional monitoring tool: clean, calm, lots of white space, nothing flashy. It should read as a real internal operator tool, not a toy or a generic AI demo.
- **Light mode.**
- **Color:** neutral greys and white throughout, with **one deep blue accent** for buttons and the title. **Green, orange and red are used only for status** (the verdict and check cards), so color always means something.
- **The verdict is the hero:** a big score number and verdict text in a colored banner, readable from across the room.
- **Check cards:** a simple grid. Each card has an icon, the check name, the failed-row count and the impact sentence. Passed checks show a green check mark and "0 issues."
- **Type:** a clean sans-serif (Streamlit's default is fine). Numbers large and bold, explanations small and grey.
- **Avoid:** emojis (except simple status icons), chatbot styling, AI sparkles, and Streamlit's own "Deploy" button and menu (it should look like a real tool, not a Streamlit demo).

## Features and Behavior

### Input File Format
Voice CDRs only. CSV with these columns:

| Column | Required | Meaning / format |
|---|---|---|
| `record_id` | yes | unique ID of the record |
| `calling_number` | yes | A-number (caller) |
| `called_number` | yes | B-number (receiver) |
| `start_time` | yes | `YYYY-MM-DD HH:MM:SS` |
| `end_time` | yes | `YYYY-MM-DD HH:MM:SS` |
| `duration_sec` | yes | integer seconds |
| `call_type` | no | MOC (outgoing) / MTC (incoming): shown, never checked |
| `cell_id` | no | cell/antenna: shown, never checked |

- Column names are matched ignoring upper/lower case and surrounding spaces.
- Extra unknown columns are allowed and ignored.

### Anomaly Checks
All checks are deterministic. A row can fail several checks: it appears under every check it fails but counts once in the health score.

1. **Missing or malformed fields:** a required field is empty, or `start_time`/`end_time` can't be parsed as `YYYY-MM-DD HH:MM:SS`, or `duration_sec` isn't an integer. A row with this problem fails only this check for that field; it gets no separate failure elsewhere.
   - Impact: *"These calls can't be rated: they will be rejected or billed with missing information."*
2. **Duplicate records:** the same `calling_number` + `called_number` + `start_time` as an earlier row, even if `record_id` differs. **Only the extra copies are flagged.** The first occurrence in file order stays valid. Each flagged copy shows the `record_id` of its original.
   - Impact: *"These calls were recorded twice: customers would be billed twice for the same call."*
3. **End time before start time:** `end_time` is earlier than `start_time`.
   - Impact: *"These calls have impossible times: their duration and price can't be trusted."*
4. **Invalid duration:** `duration_sec` ≤ 0, OR it differs from (end_time − start_time) by more than 1 second. The card shows the breakdown (negative/zero vs. mismatch).
   - Impact: *"These calls have a wrong duration: they would be billed for the wrong amount, or not at all."*
5. **Invalid phone numbers:** `calling_number` or `called_number` isn't E.164: an optional leading "+", then digits only, 10–15 digits, no spaces or letters.
   - Impact: *"These calls can't be matched to a customer account: the revenue would be lost."*

**Skip rules (one root problem, one check):**
- Checks 3 and 4 skip any row where `start_time`, `end_time` or `duration_sec` is missing or malformed.
- Check 4 skips any row that fails check 3.
- Check 5 skips a number that's empty or unreadable (it's already counted in check 1). It still runs normally on rows that have other malformed fields.

Acceptance:
- [ ] Each check flags exactly the rows defined above, and no others.
- [ ] A row failing several checks appears under each, but counts once as an error row.
- [ ] Duplicate copies show their original's `record_id`; the original isn't flagged.
- [ ] The Invalid duration card shows the negative/zero vs. mismatch breakdown.

### Health Score and Verdict
- **Score** = valid rows / total rows, where a valid row has zero failures.
- **Green**, ≥ 99%: exactly 100% → "No issues found." Otherwise → "Safe to send downstream: X rows have minor issues."
- **Orange**, 90% to < 99%: "Review before sending: X rows have issues."
- **Red**, < 90%: "Do not send downstream: send the file back to the source." Includes the real problem-row count.
- The verdict text always includes the real number of problem rows (except "No issues found," where that number is 0).
- Below the verdict, a **"Main issues"** line names the top 2 failing checks by row count (ties in card order), e.g. "Main issues: 15 missing or malformed fields · 12 invalid durations". Hidden for a 100% clean file.
- Metric cards: total rows, valid rows, rows with errors. The "Rows with errors" number takes the status color when it's above 0.

Acceptance:
- [ ] The dirty sample shows **94.9%**, orange, "Review before sending: 51 rows have issues."
- [ ] The clean sample shows **100%**, green, "No issues found."

### Check Cards
- Grid of 5 cards, always in the order above. Each card shows an icon, the name, the failed-row count and the impact sentence.
- On desktop the cards sit 3 + 2 with the bottom row filling the width. All cards have the same height and internal layout, so counts and sentences line up; the duration breakdown sits at the bottom of its card.
- A passed check shows a green check mark and "0 issues." A failed check uses status color.

Acceptance:
- [ ] Dirty sample cards: 15 / 8 / 6 / 12 / 10.
- [ ] Clean sample: all 5 cards show "0 issues" with a green check mark.

### Anomaly Table
- Lists every failing row: the original columns (including the optional ones), the check(s) failed, and a short detail (for example the original `record_id` for a duplicate, or "mismatch" vs. "negative/zero" for duration).
- A filter by check type. The default shows all anomalies, and loading a new file resets the filter to "All checks."
- The columns that say what's wrong (row number, check(s) failed, detail) come first.
- A clean file shows "No anomalous rows: ready to send downstream." in green instead of an empty table.

Acceptance:
- [ ] Filtering by a check shows exactly that check's count of rows.
- [ ] Each duplicate row shows its original's `record_id`.

### Sample Files
- A script with a fixed random seed generates identical samples every time:
  - **Dirty:** 1,000 rows, with 51 planted errors, each on a different row: 15 missing/malformed, 8 duplicate copies, 6 end-before-start, 12 invalid durations, 10 invalid phone numbers. The numbers are Cameroon-style (`+2376XXXXXXXX`).
  - **Clean:** 1,000 rows, zero errors.
- The generator also writes the **expected counts**, so tests can compare the report to the planted errors automatically.
- "Try a file with errors" loads the dirty sample. "Try a clean file" loads the clean sample.

Acceptance:
- [ ] Re-running the generator produces identical files.
- [ ] Automated tests confirm the report's counts match the expected counts for both samples.

## States and Boundaries
- **First use / nothing loaded:** the header, upload control and the two sample buttons only. No report.
- **Report shown:** after a valid file is loaded. Loading another file replaces the report.
- **Unusable file:** a clear message instead of the report, never a crash or a Python traceback:
  - Not a CSV or unreadable → "This file can't be read as a CSV. Please upload a comma-separated file."
  - Empty or headers only → "This file has no call records to check."
  - Missing required columns → "This file is missing required columns: [list]." followed by the full list of expected columns.
- **Persistence:** none. Nothing is saved between sessions.
- **No API key needed:** all wording comes from templates.

## Product Decisions
- **Deterministic checks, template wording, no AI in the PoC.** Results are reliable and repeatable, and the app works with no key (`scope.md > The POC Boundary`).
- **Merged "Invalid duration"** covers negative/zero and mismatch, with a breakdown on the card. Keeps exactly 5 checks.
- **"Missing or malformed"** absorbs bad formats, so one root problem is counted once.
- **Skip rules** (time checks skip malformed rows, duration skips end-before-start, phone skips empty numbers): "one root problem, one check."
- **Duplicates flag only extra copies:** one call really happened. Only the copies cause double billing.
- **E.164 phone rule:** international, so it works anywhere. The sample uses Cameroon-style numbers.
- **Duplicate key:** calling + called + start_time, ignoring `record_id`, because it's the same call recorded twice.
- **Thresholds 99 / 90**, and the verdict always shows the real problem-row count.
- **Forgiving column matching** (case and spaces), and extra columns ignored.
- **Two sample buttons (errors / clean)**, plus upload: a smooth demo, and judges can test both cases in one click. The video also shows one real upload.
- **Stripe-like sober look**, with status colors used only for status.
- **Anomaly table contents** (original columns + check(s) failed + detail) are confirmed by the learner. The exact detail wording is for the build to settle.

## What We're Building
- The single-page Streamlit app described above: header, upload + two sample buttons, verdict banner, metric cards, 5 check cards, filterable anomaly table and file error messages.
- The 5 deterministic checks with skip rules.
- The synthetic data generator (dirty + clean, fixed seed, expected counts).
- Automated tests comparing the report to the expected counts.
- A structure that leaves a clear place for a future AI summary.

## Deferred From the POC
- **Gemini AI summary:** stretch goal, only if the core, samples and tests are done by **2026-10-23**. Otherwise it goes in the README under "Next steps." Optional, with templates as the fallback.

## Possible Later Enhancements
- More telecom checks (e.g. data/SMS CDRs, cell_id validation, call_type rules).
- Export/download the report.
- Handling very large files (millions of rows) efficiently.

## Non-Goals
- User accounts: not needed for a single-tester local tool.
- Database or saved history: each file is analyzed in memory.
- Real-time streams: the tool works on uploaded files.
- Connection to real mediation systems: out of reach for the timeline.
- Real customer data: synthetic only.
- Data or SMS CDRs: voice only for this version.

## Open Questions
- None blocking `4-spec`.
