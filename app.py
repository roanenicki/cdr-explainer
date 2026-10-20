"""CDR Explainer page. Streamlit reruns this file top to bottom on every click;
the loaded file lives in st.session_state["source"] so it survives reruns."""

from pathlib import Path

import streamlit as st

from cdr_explainer.explain import format_score, issues
from cdr_explainer.report import analyze

DATA = Path(__file__).resolve().parent / "data"
ALL_CHECKS = "All checks"
FILTER_KEY = "check_filter"


def load_sample(filename: str) -> None:
    """Button callback: runs before the rerun, so the new source is ready."""
    st.session_state["source"] = {"name": filename, "data": (DATA / filename).read_bytes()}
    st.session_state[FILTER_KEY] = ALL_CHECKS  # a new file starts unfiltered


st.set_page_config(page_title="CDR Explainer", layout="centered")

st.title("CDR Explainer")
st.caption(
    "Check a file of voice call records in seconds: is it safe to send downstream, "
    "what's wrong with it, and why it matters for billing."
)

left, right = st.columns(2)
left.button("Try a file with errors", on_click=load_sample, args=("sample_dirty.csv",), width="stretch")
right.button("Try a clean file", on_click=load_sample, args=("sample_clean.csv",), width="stretch")

source = st.session_state.get("source")
if source:
    st.caption(f"File: {source['name']}")
    report = analyze(source["data"])

    st.subheader(f"{format_score(report.score_pct)} valid rows ({report.status})")
    st.write(report.verdict)

    total, valid, errors = st.columns(3)
    total.metric("Total rows", f"{report.total_rows:,}")
    valid.metric("Valid rows", f"{report.valid_rows:,}")
    errors.metric("Rows with errors", f"{report.error_rows:,}")

    for check in report.checks:
        st.markdown(f"**{check.name}: {issues(check.count)}**  \n{check.impact}")

    choice = st.selectbox("Show", [ALL_CHECKS, *(c.name for c in report.checks)], key=FILTER_KEY)
    rows = report.anomalies
    if choice != ALL_CHECKS:
        rows = rows[rows["checks_failed"].str.split(", ").apply(lambda names: choice in names)]
    st.dataframe(rows, hide_index=True)
