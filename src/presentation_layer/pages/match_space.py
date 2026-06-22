"""
Match Space — Scatterternary of upcoming group-stage matches in W/D/L space.

Desktop: click point → gold ring + detail panel reveals below.
Mobile:  text selectbox below chart (same session_state key, same detail panel).
§0.5: every chart must filter or reveal on interaction.
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
_SK = "ms_selected"   # session_state key

_REQUIRED_COLS = frozenset({
    "match_id", "date", "home_team", "away_team",
    "p_home", "p_draw", "p_away",
    "model_version", "created_at",
})


@st.cache_data(ttl=120)
def _load() -> pd.DataFrame:
    if not _PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(_PREDICTIONS_PATH)
        if not _REQUIRED_COLS.issubset(df.columns):
            return pd.DataFrame()
        df["top_factors"] = df["top_factors"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
        )
        return df
    except Exception:
        return pd.DataFrame()


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _fixture_card_html(row: pd.Series) -> str:
    home  = str(row["home_team"])
    away  = str(row["away_team"])
    group = str(row.get("group_label", "WC"))
    d     = str(row["date"])
    kick  = str(row.get("kickoff_time", ""))
    kick_str = f" · {kick} UTC" if kick else ""
    hf = flag_img(get_flag_code(home), width=44, team_name=home)
    af = flag_img(get_flag_code(away), width=44, team_name=away)
    return f"""
<div class="match-card" style="margin-bottom:1.1rem;">
  <div class="match-card-rail"></div>
  <div class="match-card-body" style="padding:1.1rem 1.4rem;">
    <div class="match-chip">WC26 · GRP {group} · {d}{kick_str}</div>
    <div class="match-teams">
      <div class="team-block">
        <span class="team-flag">{hf}</span>
        <span class="team-name" style="font-size:1.2rem;">{home}</span>
      </div>
      <span class="match-vs">VS</span>
      <div class="team-block away">
        <span class="team-flag">{af}</span>
        <span class="team-name" style="font-size:1.2rem;">{away}</span>
      </div>
    </div>
  </div>
</div>"""


def _prob_bar_html(p_h: float, p_d: float, p_a: float,
                   home: str, away: str) -> str:
    w_h, w_d, w_a = f"{p_h*100:.1f}%", f"{p_d*100:.1f}%", f"{p_a*100:.1f}%"
    ph, pd_, pa   = f"{p_h:.0%}", f"{p_d:.0%}", f"{p_a:.0%}"
    best = max(p_h, p_d, p_a)
    if best == p_h:
        fav = f"{flag_img(get_flag_code(home), width=16, team_name=home)} {home} {ph}"
    elif best == p_d:
        fav = f"Draw {pd_}"
    else:
        fav = f"{flag_img(get_flag_code(away), width=16, team_name=away)} {away} {pa}"
    return f"""
<div style="margin-bottom:0.75rem;">
  <div class="prob-bar-track" style="height:32px;"
       role="img" aria-label="{home} {ph} · Draw {pd_} · {away} {pa}">
    <div class="prob-seg seg-home" style="width:{w_h};">{ph}</div>
    <div class="prob-seg seg-draw" style="width:{w_d};">{pd_}</div>
    <div class="prob-seg seg-away" style="width:{w_a};">{pa}</div>
  </div>
  <div class="prob-bar-labels">
    <span class="prob-label">Home win</span>
    <span class="prob-label">Draw</span>
    <span class="prob-label">Away win</span>
  </div>
</div>
<div class="favored-chip"><span class="favored-dot"></span>Favored: {fav}</div>"""


def _factor_chips_html(factors: list[dict]) -> str:
    if not factors:
        return ""
    chips = "".join(
        f'<span class="factor-chip {"fpos" if f.get("direction","+")=="+" else "fneg"}">'
        f'{"↑" if f.get("direction","+")=="+" else "↓"} {f["label"]}</span>'
        for f in factors[:4]
    )
    return f'<div class="factors-row" style="margin-top:0.5rem;">{chips}</div>'


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail(row: pd.Series) -> None:
    home   = str(row["home_team"])
    away   = str(row["away_team"])
    p_h    = float(row["p_home"])
    p_d    = float(row["p_draw"])
    p_a    = float(row["p_away"])
    factors = row.get("top_factors", [])

    st.markdown(_fixture_card_html(row), unsafe_allow_html=True)

    st.markdown(
        '<div class="sec-heading">Calibrated outcome probabilities</div>',
        unsafe_allow_html=True,
    )
    st.markdown(_prob_bar_html(p_h, p_d, p_a, home, away), unsafe_allow_html=True)
    if factors:
        st.markdown(_factor_chips_html(factors), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-heading">Prediction waterfall — base rate → calibrated output</div>',
        unsafe_allow_html=True,
    )
    if factors:
        st.plotly_chart(
            prediction_waterfall(row),
            width="stretch",
            key=f"wf_ms_{row.get('match_id', hash(home+away))}",
        )
    else:
        st.markdown(
            '<p style="color:var(--text-muted);font-size:0.82rem;">'
            "Factor data not available — re-run <code>python pipelines/refresh.py</code>.</p>",
            unsafe_allow_html=True,
        )


# ── Page ──────────────────────────────────────────────────────────────────────

def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Match Space</h1>"
        '<p class="subtitle">'
        "Win / Draw / Loss probability space · use the selector below to inspect a match"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    df = _load()
    if df.empty:
        if _PREDICTIONS_PATH.exists():
            st.markdown(
                '<div class="no-data"><h3>Predictions file is missing or corrupted</h3>'
                "<p>Last refresh may have failed — re-run "
                "<code>python pipelines/refresh.py</code>.</p></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="no-data"><h3>No predictions</h3>'
                "<p>Run <code>python pipelines/refresh.py</code> first.</p></div>",
                unsafe_allow_html=True,
            )
        return

    today    = str(date.today())
    upcoming = (
        df[df["date"] >= today]
        .copy()
        .pipe(lambda d: d[d["group_label"].str.match(r"^[A-L]$", na=False)])
        .sort_values(["date", "kickoff_time"])
        .reset_index(drop=True)
    )

    if upcoming.empty:
        st.info("No upcoming group-stage matches with known teams.")
        return

    selected: int | None = st.session_state.get(_SK)

    # ── Ternary ───────────────────────────────────────────────────────────────
    fig   = ternary_scatter(upcoming, selected_idx=selected)
    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        key="ternary_chart",
    )

    # Resolve click → update session_state.
    # Plotly ternary doesn't support dragmode="select", so point_index may be
    # None; fall back to point_number then customdata (which holds the row index).
    if event and event.selection and event.selection.points:
        pt      = event.selection.points[0]
        new_pos = pt.get("point_index")
        if new_pos is None:
            new_pos = pt.get("point_number")
        if new_pos is None:
            cd = pt.get("customdata")
            if isinstance(cd, (list, tuple)) and cd:
                new_pos = int(cd[0])
            elif cd is not None:
                try:
                    new_pos = int(cd)
                except (TypeError, ValueError):
                    new_pos = None
        if new_pos is not None and new_pos != selected:
            st.session_state[_SK] = new_pos
            st.rerun()

    # ── Mobile / keyboard selector ────────────────────────────────────────────
    labels = [
        f"{r['home_team']} vs {r['away_team']}  ·  {r['date']}"
        for _, r in upcoming.iterrows()
    ]
    # "None" sentinel at index 0 — lets user explicitly deselect
    sel_options = ["— select a match —"] + labels
    cur_sel_label = labels[selected] if (selected is not None and selected < len(labels)) else sel_options[0]
    chosen = st.selectbox(
        "Select match",
        sel_options,
        index=sel_options.index(cur_sel_label) if cur_sel_label in sel_options else 0,
        label_visibility="collapsed",
        key="ms_selectbox",
    )
    if chosen != sel_options[0]:
        new_pos = labels.index(chosen)
        if new_pos != selected:
            st.session_state[_SK] = new_pos
            st.rerun()
    elif chosen == sel_options[0] and selected is not None:
        # User picked the blank option → clear
        st.session_state[_SK] = None
        st.rerun()

    # ── Detail panel / hint ───────────────────────────────────────────────────
    st.markdown('<hr style="border-color:var(--border);margin:0.75rem 0 1rem;">', unsafe_allow_html=True)

    if selected is not None and 0 <= selected < len(upcoming):
        row = upcoming.iloc[selected]
        _render_detail(row)
    else:
        st.markdown(
            '<p style="color:var(--text-muted);font-size:0.85rem;padding:0.2rem 0 1rem;">'
            "Click a point above or use the selector — prediction detail reveals here.</p>",
            unsafe_allow_html=True,
        )

    # ── Data stamp — §7e ──────────────────────────────────────────────────────
    try:
        pred_ts = pd.read_parquet(_PREDICTIONS_PATH, columns=["created_at"])["created_at"].max()
        ts_str  = pd.to_datetime(pred_ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        ts_str = "unknown"
    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.5rem;">'
        f"Data as of <code>{ts_str}</code> · Updates daily via batch</p>",
        unsafe_allow_html=True,
    )
