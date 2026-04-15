"""
Streamlit UI helper functions.
Renders risk badges, score bars, and decision callouts.
"""
from __future__ import annotations

import streamlit as st


def render_risk_badge(risk_level: str) -> None:
    """Display a color-coded risk level badge."""
    colors = {
        "LOW": ("#d4edda", "#155724", "🟢"),
        "MEDIUM": ("#fff3cd", "#856404", "🟡"),
        "HIGH": ("#f8d7da", "#721c24", "🔴"),
    }
    bg, fg, icon = colors.get(risk_level.upper(), ("#e2e3e5", "#383d41", "⚪"))
    st.markdown(
        f'<div style="display:inline-block;padding:6px 16px;border-radius:20px;'
        f'background:{bg};color:{fg};font-weight:700;font-size:1.1rem;">'
        f"{icon} {risk_level.upper()}</div>",
        unsafe_allow_html=True,
    )


def render_score_bar(label: str, score: float, max_val: float = 1.0) -> None:
    """Display a labeled progress bar for a sub-score."""
    normalized = min(1.0, max(0.0, score / max_val))
    st.write(f"**{label}:** `{score:.2f}` / `{max_val:.1f}`")
    st.progress(normalized)


def render_decision_callout(decision: str) -> None:
    """Display a Streamlit status message styled by decision type."""
    messages = {
        "APPROVE": ("✅ APPROVED", "success"),
        "REVIEW": ("⚠️ MANUAL REVIEW REQUIRED", "warning"),
        "ESCALATE": ("🚨 ESCALATED — COMPLIANCE TEAM NOTIFIED", "error"),
    }
    text, style = messages.get(decision.upper(), (f"Decision: {decision}", "info"))
    getattr(st, style)(text)
