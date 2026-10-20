"""CDR Explainer page. Streamlit reruns this file top to bottom on every click;
the loaded file lives in st.session_state["source"] so it survives reruns."""

import logging
from pathlib import Path

import streamlit as st

from cdr_explainer import ui_html
from cdr_explainer.loader import FileProblem
from cdr_explainer.report import Report, analyze

DATA = Path(__file__).resolve().parent / "data"
ALL_CHECKS = "All checks"
FILTER_KEY = "check_filter"
UPLOAD_VERSION = "upload_version"  # bumped to give the uploader a fresh, empty widget


def set_source(name: str, data: bytes) -> None:
    """The most recent upload or sample click wins; a new file starts unfiltered."""
    st.session_state["source"] = {"name": name, "data": data}
    st.session_state[FILTER_KEY] = ALL_CHECKS


def upload_key() -> str:
    return f"upload_{st.session_state.get(UPLOAD_VERSION, 0)}"


def load_sample(filename: str) -> None:
    """Button callback: runs before the rerun, so the new source is ready.
    A new uploader key clears any uploaded file, so only one file is ever active."""
    set_source(filename, (DATA / filename).read_bytes())
    st.session_state[UPLOAD_VERSION] = st.session_state.get(UPLOAD_VERSION, 0) + 1


def load_upload() -> None:
    """Uploader callback. Removing the upload keeps whatever is on screen."""
    uploaded = st.session_state[upload_key()]
    if uploaded is not None:
        set_source(uploaded.name, uploaded.getvalue())


def draw_report(report: Report) -> None:
    st.html(ui_html.verdict_banner(report))
    st.html(ui_html.metric_cards(report))
    st.html(ui_html.check_cards(report))

    st.subheader("Anomalous rows")
    if report.anomalies.empty:
        st.html(ui_html.clean_message())
        return
    choice = st.selectbox("Show", [ALL_CHECKS, *(c.name for c in report.checks)], key=FILTER_KEY)
    rows = report.anomalies
    if choice != ALL_CHECKS:
        rows = rows[rows["checks_failed"].str.split(", ").apply(lambda names: choice in names)]
    # What's wrong comes first; the original CDR columns follow.
    first = ["row_number", "checks_failed", "details"]
    st.dataframe(rows, hide_index=True, column_order=[*first, *(c for c in rows.columns if c not in first)])


st.set_page_config(page_title="CDR Explainer", layout="wide")

st.html(ui_html.STYLE)
st.html(
    ui_html.page_header(
        "CDR Explainer",
        "Check a file of voice call records in seconds: is it safe to send downstream, "
        "what's wrong with it, and why it matters for billing.",
    )
)

st.file_uploader("Upload a CDR file (CSV)", type=["csv"], key=upload_key(), on_change=load_upload)
left, right = st.columns(2)
left.button("Try a file with errors", on_click=load_sample, args=("sample_dirty.csv",), width="stretch")
right.button("Try a clean file", on_click=load_sample, args=("sample_clean.csv",), width="stretch")

source = st.session_state.get("source")
if source:
    st.html(ui_html.file_line(source["name"]))
    try:
        report = analyze(source["data"])
    except FileProblem as problem:
        show = st.warning if problem.is_warning else st.error
        show(problem.markdown())
    except Exception:
        logging.exception("Unexpected error analyzing %s", source["name"])
        st.error("Something went wrong reading this file.")
    else:
        draw_report(report)
