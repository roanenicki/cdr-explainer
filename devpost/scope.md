---
doc: scope
status: approved
---

# CDR Explainer

Upload a CSV of call detail records (CDRs) and in seconds see whether the file is safe to send downstream, what's wrong with it, and why it matters for billing.

## The Unique Kernel
It **already knows what a CDR is** and **speaks in business consequences**. There's no schema or rules to write: it applies telecom-specific checks out of the box and explains each failure as billing impact ("12 calls have a negative duration: they would be billed wrong or not at all"), topped by an instant colored health verdict. Every judge has a phone bill.

The checks are plain, deterministic Python, so the results are reliable and repeatable. The plain-language wording comes from templates, not AI.

## Who It's For
A telecom data tester or analyst working on mediation flows (the learner tests flows on a telecom mediation platform). Operators receive files with millions of CDRs. Today, testers still check by hand whether a received file is complete and consistent. "It's slow and errors are easy to miss."

## The Core Loop
Open the app → upload a CDR file (or click "Try with a sample file") → read the health verdict → see which checks failed and why it matters → filter the anomalous rows to see exactly what to fix → fix and re-check, or send the file back. They come back with every new file they receive.

## Inspiration & Identity
Clean, calm and immediately readable, so even someone who doesn't know telecom gets it. One big colored verdict (green / orange / red), simple metric cards, then detail below. A one-line explanation under the title. Polished enough for a 2-minute demo.

## Why This Matters to the Learner
It's their own day-job pain. They also want to practice the full plan-first, spec-driven loop (scope → PRD → spec → working app) as a reusable habit before the Kiroween hackathon, learn to build a clean, polished Streamlit interface, and "win a prize."

## What "Working" Looks Like
1. `streamlit run app.py` opens a clean page: the title "CDR Explainer", one explanatory line, an upload option, and a **"Try with a sample file"** button.
2. One click, and the report appears in about a second.
3. At the top: the **file health score**, big and colored (for example "87% valid rows" in orange), with a verdict like "Do not send downstream: fix 3 issues first", and metric cards for total rows, valid rows and rows with errors.
4. **One card per check** with the failed-row count and its business impact in plain words.
5. A **table of anomalous rows**, filterable by check type.

**The proof:** the sample file has known planted errors, and the report finds every one of them with the right counts and nothing else. A clean file comes back 100% green.

## The POC Boundary
- Streamlit app, run locally. Upload a CSV, or use the built-in sample.
- Exactly **5 deterministic checks:**
  1. Missing required fields
  2. Duplicate records
  3. End time before start time
  4. Invalid duration (negative/zero, or a mismatch with end minus start; the card shows the breakdown)
  5. Invalid phone numbers
- Health score + verdict, metric cards, per-check cards with template-based business-impact wording, and a filterable anomaly table.
- A script that generates synthetic CDRs with errors planted on purpose (a dirty sample and a clean one).
- Tests proving the planted errors are found exactly.
- Code structured so an AI summary can be plugged in later.

## Later
- **Gemini AI summary** (stretch goal): only if the core app, sample data and tests are fully done by **2026-10-23**. It stays optional and needs a key, with the templates as the fallback. Otherwise it goes in the README under "Next steps."
- Other telecom checks, beyond the 5.
- Exporting or downloading the report.

## Explicitly Cut
- **User accounts:** not needed to prove the kernel.
- **Database:** single-file, in-memory analysis is enough.
- **Real-time streams:** a proof of concept works on uploaded files.
- **Connection to real mediation systems:** out of reach for the timeline, and it would involve real infrastructure.
- **Real customer data:** synthetic only, for privacy and safety.
