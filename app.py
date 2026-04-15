"""
Vendor Master Governance — Excel Vendor Status Checker
Simple UI: upload Excel → see rows with issues (INACTIVE / PENDING).

Run with:  streamlit run app.py
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

import time

import pandas as pd
import streamlit as st

from pipelines.flow_b import run_excel_pipeline


def _recompute_result(df: pd.DataFrame, old_result):
    """Rebuild ExcelPipelineResult metrics and bytes from an updated DataFrame."""
    from collections import Counter
    from models.schemas import ExcelPipelineResult
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    counts = Counter(df["Status"].tolist())
    reason_counts = Counter(r for r in df["Reason"].tolist() if r)
    preview_df = df.head(50).where(pd.notnull(df), other=None)
    return ExcelPipelineResult(
        output_bytes=buf.getvalue(),
        total_rows=len(df),
        active_count=counts.get("ACTIVE", 0),
        inactive_count=counts.get("INACTIVE", 0),
        pending_count=counts.get("PENDING", 0),
        preview_records=preview_df.to_dict(orient="records"),
        reason_summary=dict(reason_counts),
    )


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Augmented Data Compliance Framework",
    page_icon="🛡️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* SAP blue header bar */
    [data-testid="stAppViewContainer"] > .main > .block-container {
        padding-top: 1.5rem;
    }
    .app-header {
        background: linear-gradient(90deg, #0a6ed1 0%, #0854a0 100%);
        padding: 1.2rem 1.8rem;
        border-radius: 8px;
        margin-bottom: 1.2rem;
    }
    .app-header h1 {
        color: white;
        font-size: 1.6rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: 0.01em;
    }
    .app-header p {
        color: #cce0f5;
        font-size: 0.85rem;
        margin: 0.3rem 0 0 0;
    }
    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f5f8fd;
        border: 1px solid #d1e3f8;
        border-radius: 8px;
        padding: 0.8rem 1rem;
    }
    /* Subheader accent */
    h2, h3 { color: #0854a0; }
    /* Chat input */
    [data-testid="stChatInput"] textarea {
        border: 1px solid #0a6ed1 !important;
    }
</style>
<div class="app-header">
    <h1>🛡️ AI Augmented Data Compliance Framework</h1>
    <p>Upload your vendor master file to analyse compliance status, query data, and apply updates via chat.</p>
</div>
""", unsafe_allow_html=True)

# ── File upload ───────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload vendor master (.xlsx / .csv)",
    type=["xlsx", "csv"],
    label_visibility="collapsed",
)

if uploaded is None:
    st.info("Upload an Excel or CSV file above to get started.", icon="⬆️")
    st.stop()

# ── Session-state init / file-change detection ────────────────────────────────
_file_key = f"{uploaded.name}:{uploaded.size}"
if st.session_state.get("_file_key") != _file_key:
    st.session_state["_file_key"]         = _file_key
    st.session_state["pipeline_result"]   = None
    st.session_state["vendor_df"]         = None
    st.session_state["chat_history"]      = []
    st.session_state["last_update_csv"]   = None

# ── Process ───────────────────────────────────────────────────────────────────
with st.spinner("Agents Running..."):
    try:
        if st.session_state.get("pipeline_result") is None:
            result = run_excel_pipeline(uploaded)
            time.sleep(7)
            st.session_state["pipeline_result"]   = result
            st.session_state["vendor_df"]         = pd.read_excel(
                io.BytesIO(result.output_bytes), engine="openpyxl"
            )
        else:
            result = st.session_state["pipeline_result"]
    except ValueError as exc:
        st.error(f"**File error:** {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"**Unexpected error:** {exc}")
        st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total rows", result.total_rows)
m2.metric("✅ Active", result.active_count)
m3.metric("⏳ Pending", result.pending_count)
m4.metric("❌ Inactive", result.inactive_count)

st.divider()

# ── Status rules ──────────────────────────────────────────────────────────────
with st.expander("ℹ️ Status rules", expanded=False):
    st.markdown(
        """
| Status | Condition | Reason |
|--------|-----------|--------|
| ✅ **ACTIVE** | Both GDPR **and** ECCN present | — |
| ⏳ **PENDING** | One of GDPR / ECCN missing | Missing GDPR *or* Missing ECCN |
| ❌ **INACTIVE** | Both GDPR **and** ECCN missing | Both missing |

*A value is treated as missing if it is blank, whitespace-only, or null.*
        """
    )

# ── All vendors table ─────────────────────────────────────────────────────────
st.subheader(f"📋 Business Partner Data ({result.total_rows} records)")

df_full = st.session_state["vendor_df"]
df_display = df_full.copy()

# Highlight function
_STATUS_COLORS = {
    "INACTIVE": "background-color:#f8d7da;color:#721c24",
    "PENDING": "background-color:#fff3cd;color:#856404",
}

def _highlight_status(val: str) -> str:
    return _STATUS_COLORS.get(str(val).upper(), "")

def _highlight_missing(val) -> str:
    if pd.isna(val) or (isinstance(val, str) and val.strip() == ""):
        return "background-color:#ffeeba"
    return ""

styled = (
    df_display.style
    .map(_highlight_status, subset=["Status"])
    .map(_highlight_missing, subset=[c for c in ["GDPR", "ECCN"] if c in df_display.columns])
)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Reason breakdown ──────────────────────────────────────────────────────────
if result.reason_summary:
    st.markdown("**Reason breakdown:**")
    reason_df = (
        pd.DataFrame(list(result.reason_summary.items()), columns=["Reason", "Count"])
        .sort_values("Count", ascending=False)
    )
    st.dataframe(reason_df, use_container_width=False, hide_index=True)

st.divider()

# ── Download processed file ───────────────────────────────────────────────────
st.download_button(
    "⬇️ Download processed Excel (all rows with Status + Reason columns)",
    data=result.output_bytes,
    file_name="vendor_status_processed.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── Chat section ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("💬 Compliance Assistant")

from agents.chat_agent import ChatAgent  # noqa: E402 (lazy import after setup)

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Welcome message on first render (before any chat turns)
if not st.session_state["chat_history"]:
    flagged = result.pending_count + result.inactive_count
    with st.chat_message("assistant"):
        st.markdown(
            f"{result.total_rows} vendors loaded, **{flagged} flagged** for compliance review. "
            "Ask me anything — query data, check status, or apply updates."
        )

# Render conversation history
for idx, turn in enumerate(st.session_state["chat_history"]):
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
    # Show download button after the last assistant message if an update was made
    if (
        turn["role"] == "assistant"
        and idx == len(st.session_state["chat_history"]) - 1
        and st.session_state.get("last_update_csv") is not None
    ):
        st.download_button(
            "⬇️ Download updated CSV",
            data=st.session_state["last_update_csv"],
            file_name="vendor_data_updated.csv",
            mime="text/csv",
            key=f"dl_{idx}",
        )

# Input bar
user_input = st.chat_input("Ask a question about the vendors...")

if user_input and user_input.strip():
    user_input = user_input.strip()
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Thinking..."):
        chat_result = ChatAgent().run(
            user_message=user_input,
            conversation_history=st.session_state["chat_history"][:-1],
            df=st.session_state["vendor_df"],
        )

    reply = chat_result.reply

    # If a write occurred, sync updated df and recompute report metrics
    if chat_result.updated_df is not None:
        st.session_state["vendor_df"] = chat_result.updated_df
        st.session_state["pipeline_result"] = _recompute_result(
            chat_result.updated_df, st.session_state["pipeline_result"]
        )
        st.session_state["last_update_csv"] = chat_result.updated_df.to_csv(index=False).encode("utf-8")

    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state["chat_history"].append({"role": "assistant", "content": reply})

    # Rerun to refresh the report section with updated data
    if chat_result.updated_df is not None:
        st.rerun()
