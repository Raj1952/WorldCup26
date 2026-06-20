"""
Match Space — Page 4 per §5.

Scatterternary of all upcoming group-stage matches. Clicking a point
filters the match list below to that fixture and shows its prediction
detail inline.

§0.5 interaction rule: every chart must *filter* or *reveal* on click.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from src.presentation_layer.theme import DARK
from src.presentation_layer.charts.ternary import ternary_scatter
from src.presentation_layer.charts.waterfall import prediction_waterfall
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

_PREDICTIONS_PATH = Path("predictions.parquet")


@st.cache_data(ttl=120)
def _load() -> pd.DataFrame:
    if not _PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(_PREDICTIONS_PATH)
    df["top_factors"] = df["top_factors"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
    )
    return df


def _match_label(row: pd.Series) -> str:
    return f"{row['home_team']} vs {row['away_team']} ({row['date']})"


def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Match Space</h1>"
        '<p class="subtitle">Win / Draw / Loss probability space · click a point to inspect</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    df = _load()
    if df.empty:
        st.markdown(
            '<div class="no-data"><h3>No predictions</h3>'
            "<p>Run <code>python pipelines/refresh.py</code> first.</p></div>",
            unsafe_allow_html=True,
        )
        return

    today = str(date.today())
    upcoming = df[df["date"] >= today].copy().sort_values("date")
    upcoming = upcoming[
        upcoming["group_label"].str.match(r"^[A-L]$", na=False)
    ].reset_index(drop=True)

    if upcoming.empty:
        st.info("No upcoming group-stage matches with known teams.")
        return

    # ── Ternary ───────────────────────────────────────────────────────────────
    selected_pos: int | None = st.session_state.get("ternary_selected_pos")

    fig = ternary_scatter(upcoming, selected_idx=selected_pos)
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="ternary_chart",
    )

    # Parse click — Streamlit returns point_index relative to the trace
    if event and event.selection and event.selection.points:
        pt = event.selection.points[0]
        new_pos = pt.get("point_index")
        if new_pos != st.session_state.get("ternary_selected_pos"):
            st.session_state["ternary_selected_pos"] = new_pos
            st.rerun()

    # ── Divider + clear button ────────────────────────────────────────────────
    col_info, col_clear = st.columns([4, 1])
    with col_clear:
        if selected_pos is not None:
            if st.button("Clear selection", use_container_width=True):
                st.session_state["ternary_selected_pos"] = None
                st.rerun()

    st.markdown('<hr style="border-color:var(--border);margin:0.5rem 0 1rem;">', unsafe_allow_html=True)

    # ── Match detail panel ────────────────────────────────────────────────────
    if selected_pos is not None and 0 <= selected_pos < len(upcoming):
        row = upcoming.iloc[selected_pos]
        _render_detail(row)
    else:
        with col_info:
            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.85rem;padding-top:0.4rem;">'
                "Click any point in the ternary above to inspect that match prediction.</p>",
                unsafe_allow_html=True,
            )
        st.markdown('<div class="sec-heading">All upcoming matches</div>', unsafe_allow_html=True)
        _render_table(upcoming)


def _render_detail(row: pd.Series) -> None:
    """Show flag header + prob bar + waterfall for the selected match."""
    home = row["home_team"]
    away = row["away_team"]
    p_h  = float(row["p_home"])
    p_d  = float(row["p_draw"])
    p_a  = float(row["p_away"])
    hf   = flag_img(get_flag_code(home), width=48, team_name=home)
    af   = flag_img(get_flag_code(away), width=48, team_name=away)
    group = row.get("group_label", "WC")
    date_ = str(row["date"])

    st.markdown(f"""
<div class="match-card" style="margin-bottom:1.2rem;">
  <div class="match-card-rail"></div>
  <div class="match-card-body">
    <div class="match-chip">WC26 · Grp {group} · {date_}</div>
    <div class="match-teams">
      <div class="team-block">{hf}
        <span class="team-name" style="font-size:1.25rem;">{home}</span>
      </div>
      <span class="match-vs">VS</span>
      <div class="team-block away">{af}
        <span class="team-name" style="font-size:1.25rem;">{away}</span>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    col_wf, col_prob = st.columns([3, 1])
    with col_wf:
        st.markdown('<div class="sec-heading">Home-win prediction waterfall</div>', unsafe_allow_html=True)
        fig = prediction_waterfall(row)
        st.plotly_chart(fig, use_container_width=True, key=f"wf_{row.get('match_id','x')}")

    with col_prob:
        st.markdown('<div class="sec-heading">Probabilities</div>', unsafe_allow_html=True)
        for label, prob, color in [
            (f"{home} win", p_h, "var(--win)"),
            ("Draw",        p_d, "var(--draw)"),
            (f"{away} win", p_a, "var(--loss)"),
        ]:
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:0.5rem 0.75rem;margin-bottom:4px;border-radius:8px;
            border:1px solid var(--border);background:var(--surface);">
  <span style="color:{color};font-weight:600;font-size:0.82rem;">{label}</span>
  <span style="font-family:var(--ff-mono);font-size:1rem;
               font-weight:700;color:{color};">{prob:.1%}</span>
</div>""", unsafe_allow_html=True)


def _render_table(df: pd.DataFrame) -> None:
    """Compact table of all matches with prob bars."""
    for _, row in df.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        p_h  = float(row["p_home"])
        p_d  = float(row["p_draw"])
        p_a  = float(row["p_away"])
        group = row.get("group_label", "")
        date_ = str(row["date"])
        best = max(p_h, p_d, p_a)
        if best == p_h:
            verdict_color = "var(--win)"
            verdict = f"{home} favoured"
        elif best == p_d:
            verdict_color = "var(--draw)"
            verdict = "Draw likely"
        else:
            verdict_color = "var(--loss)"
            verdict = f"{away} favoured"
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;padding:0.45rem 0.75rem;
            border-bottom:1px solid var(--border);">
  <span style="font-family:var(--ff-mono);font-size:0.75rem;
               color:var(--text-muted);min-width:75px;">{date_}</span>
  <span style="font-size:0.78rem;color:var(--text-muted);min-width:28px;">{group}</span>
  <span style="font-size:0.9rem;font-weight:600;flex:1;">{home} <span style="color:var(--text-muted)">vs</span> {away}</span>
  <span style="font-family:var(--ff-mono);font-size:0.82rem;
               color:{verdict_color};min-width:150px;text-align:right;">{verdict}</span>
  <span style="font-family:var(--ff-mono);font-size:0.82rem;
               color:var(--gold);min-width:45px;text-align:right;">{best:.0%}</span>
</div>""", unsafe_allow_html=True)
