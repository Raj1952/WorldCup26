"""
Share Card page — one prediction, no dashboard chrome, PNG download.

§CLAUDE.md C6 checkpoint: match + exact numbers shown before export button.
PNG: 1200×630 (2× the 600px HTML preview width), crisp on Retina/LinkedIn.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.presentation_layer.theme import DARK
from src.presentation_layer.components.share_card import (
    share_card_css,
    share_html,
    share_png,
)

_PREDICTIONS_PATH = Path("predictions.parquet")


@st.cache_data(ttl=120)
def _load() -> pd.DataFrame:
    if not _PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(_PREDICTIONS_PATH)


def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Share Card</h1>"
        '<p class="subtitle">'
        "One prediction · no dashboard chrome · 1200×630 PNG for LinkedIn"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    df = _load()
    if df.empty:
        st.markdown(
            '<div class="no-data"><h3>No predictions available</h3>'
            "<p>Run <code>python pipelines/refresh.py</code> first.</p></div>",
            unsafe_allow_html=True,
        )
        return

    # Known group-stage matches only (§0.5/§3)
    matches = (
        df[df["group_label"].str.match(r"^[A-L]$", na=False)]
        .sort_values(["date", "kickoff_time"])
        .reset_index(drop=True)
    )
    if matches.empty:
        st.markdown(
            '<div class="no-data"><h3>No group-stage matches with known teams</h3></div>',
            unsafe_allow_html=True,
        )
        return

    # Match selector
    labels = [
        f"{r['home_team']} vs {r['away_team']}  ·  {r['date']}"
        for _, r in matches.iterrows()
    ]
    choice = st.selectbox(
        "Select match",
        labels,
        label_visibility="collapsed",
        key="sc_match_sel",
    )
    row = matches.iloc[labels.index(choice)]

    # ── C6: show exact numbers before the export button ───────────────────────
    home = str(row["home_team"])
    away = str(row["away_team"])
    p_h  = float(row["p_home"])
    p_d  = float(row["p_draw"])
    p_a  = float(row["p_away"])
    ts   = str(row.get("created_at", ""))[:16].replace("T", " ")
    mv   = str(row.get("model_version", ""))

    # ── HTML preview ──────────────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Preview — 600px · export is 2× this width</div>',
        unsafe_allow_html=True,
    )
    st.markdown(share_card_css(), unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;justify-content:flex-start;'
        f'margin:0.6rem 0 1.25rem;">'
        f"{share_html(row)}</div>",
        unsafe_allow_html=True,
    )

    # ── Numbers summary + download ────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Export — PNG 1200×630</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:var(--surface);border:1px solid var(--border);'
        f'border-radius:var(--radius-md);padding:0.8rem 1rem;margin-bottom:0.75rem;">'
        f'<span style="font-family:\'Archivo\',sans-serif;font-weight:800;'
        f'font-size:0.95rem;color:var(--text);">{home} vs {away}</span><br>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;">'
        f'Home <span style="color:var(--win);">{p_h:.1%}</span> · '
        f'Draw <span style="color:var(--draw);">{p_d:.1%}</span> · '
        f'Away <span style="color:var(--loss);">{p_a:.1%}</span></span><br>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;'
        f'color:var(--text-muted);">Model: {mv} · Data as of {ts}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    png = share_png(row)
    fname = (
        f"tempo_{home.lower().replace(' ','_')}"
        f"_vs_{away.lower().replace(' ','_')}.png"
    )
    st.download_button(
        label="Download PNG  (1200×630 · 2×)",
        data=png,
        file_name=fname,
        mime="image/png",
        type="primary",
        use_container_width=False,
    )

    # Data stamp
    try:
        pred_ts = pd.read_parquet(_PREDICTIONS_PATH, columns=["created_at"])["created_at"].max()
        ts_str  = pd.to_datetime(pred_ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        ts_str = "unknown"

    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.25rem;">'
        f"Predictions as of <code>{ts_str}</code> · Updates daily via batch</p>",
        unsafe_allow_html=True,
    )
