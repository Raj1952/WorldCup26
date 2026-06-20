"""Match Detail page — fixture header, calibrated prob bar, prediction waterfall."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.presentation_layer.theme import DARK
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img
from src.presentation_layer.charts.waterfall import prediction_waterfall


_PREDICTIONS_PATH = Path("predictions.parquet")

_REQUIRED_COLS = frozenset({
    "match_id", "date", "home_team", "away_team",
    "p_home", "p_draw", "p_away", "is_projected",
    "model_version", "created_at",
})


@st.cache_data(ttl=120)
def _load_predictions() -> pd.DataFrame:
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
    except Exception as exc:
        return pd.DataFrame()


def _fixture_header_html(row: pd.Series) -> str:
    """Full-width fixture header card — hero size (48px flags, 1.3rem names)."""
    home = str(row["home_team"])
    away = str(row["away_team"])
    group = str(row.get("group_label", "WC"))
    date  = str(row["date"])
    kick  = str(row.get("kickoff_time", ""))
    kick_str = f" · {kick} UTC" if kick else ""

    hf = flag_img(get_flag_code(home), width=48, team_name=home)
    af = flag_img(get_flag_code(away), width=48, team_name=away)

    return f"""
<div class="match-card hero-card">
  <div class="match-card-rail"></div>
  <div class="match-card-body">
    <div class="match-chip">WC26 · GRP {group} · {date}{kick_str}</div>
    <div class="match-teams">
      <div class="team-block">
        <span class="team-flag">{hf}</span>
        <span class="team-name hero-team-name">{home}</span>
      </div>
      <span class="match-vs">VS</span>
      <div class="team-block away">
        <span class="team-flag">{af}</span>
        <span class="team-name hero-team-name">{away}</span>
      </div>
    </div>
  </div>
</div>"""


def _prob_bar_html(p_h: float, p_d: float, p_a: float,
                   home: str, away: str) -> str:
    """Full-width calibrated probability bar — hero height (36px)."""
    w_h = f"{p_h * 100:.1f}%"
    w_d = f"{p_d * 100:.1f}%"
    w_a = f"{p_a * 100:.1f}%"
    pct_h = f"{p_h:.0%}"
    pct_d = f"{p_d:.0%}"
    pct_a = f"{p_a:.0%}"

    # Determine favored team/outcome
    best = max(p_h, p_d, p_a)
    if best == p_h:
        fav_label = home
        fav_flag  = flag_img(get_flag_code(home), width=18, team_name=home)
        fav_pct   = pct_h
    elif best == p_d:
        fav_label = "Draw"
        fav_flag  = ""
        fav_pct   = pct_d
    else:
        fav_label = away
        fav_flag  = flag_img(get_flag_code(away), width=18, team_name=away)
        fav_pct   = pct_a

    fav_inner = f"{fav_flag} {fav_label}" if fav_flag else fav_label

    return f"""
<div style="margin-bottom:0.85rem;">
  <div class="prob-bar-track" style="height:36px;"
       role="img" aria-label="{home} {pct_h} · Draw {pct_d} · {away} {pct_a}">
    <div class="prob-seg seg-home" style="width:{w_h};">{pct_h}</div>
    <div class="prob-seg seg-draw" style="width:{w_d};">{pct_d}</div>
    <div class="prob-seg seg-away" style="width:{w_a};">{pct_a}</div>
  </div>
  <div class="prob-bar-labels">
    <span class="prob-label">Home win</span>
    <span class="prob-label">Draw</span>
    <span class="prob-label">Away win</span>
  </div>
</div>
<div class="favored-chip">
  <span class="favored-dot"></span>
  Favored: {fav_inner} {fav_pct}
</div>"""


def _factor_chips_html(factors: list[dict]) -> str:
    if not factors:
        return ""
    chips = ""
    for f in factors[:5]:
        cls = "fpos" if f.get("direction", "+") == "+" else "fneg"
        arrow = "↑" if f.get("direction", "+") == "+" else "↓"
        chips += f'<span class="factor-chip {cls}">{arrow} {f["label"]}</span>'
    return f'<div class="factors-row" style="margin-top:0.6rem;">{chips}</div>'


def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Match Detail</h1>"
        '<p class="subtitle">Fixture breakdown, calibrated probabilities, and prediction drivers</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    df = _load_predictions()

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
                '<div class="no-data"><h3>No predictions available</h3>'
                "<p>Run <code>python pipelines/refresh.py</code> first.</p></div>",
                unsafe_allow_html=True,
            )
        return

    # ── Match selector ────────────────────────────────────────────────────────
    # Filter to known-team matches (group A-L) and sort by date
    known = df[df["group_label"].str.match(r"^[A-L]$", na=False)].copy()
    known = known.sort_values(["date", "kickoff_time"]).reset_index(drop=True)

    options = [
        f"{row['home_team']} vs {row['away_team']}  ·  {row['date']}"
        for _, row in known.iterrows()
    ]
    sel = st.selectbox("Choose a match", options, label_visibility="collapsed")
    sel_idx = options.index(sel)
    row = known.iloc[sel_idx]

    home  = str(row["home_team"])
    away  = str(row["away_team"])
    p_h   = float(row["p_home"])
    p_d   = float(row["p_draw"])
    p_a   = float(row["p_away"])
    facts = row.get("top_factors", [])

    # ── Fixture header card ───────────────────────────────────────────────────
    st.markdown(_fixture_header_html(row), unsafe_allow_html=True)

    # ── Calibrated probability bar ────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Calibrated outcome probabilities</div>',
        unsafe_allow_html=True,
    )
    st.markdown(_prob_bar_html(p_h, p_d, p_a, home, away), unsafe_allow_html=True)

    # ── Factor chips ──────────────────────────────────────────────────────────
    if facts:
        st.markdown(_factor_chips_html(facts), unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)

    # ── Waterfall ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Prediction waterfall — base rate → calibrated output</div>',
        unsafe_allow_html=True,
    )
    if facts:
        fig = prediction_waterfall(row)
        st.plotly_chart(fig, use_container_width=True,
                        key=f"wf_{row.get('match_id', sel_idx)}")
    else:
        st.markdown(
            '<div class="no-data" style="padding:2rem;">'
            "<h3>Factor data not available</h3>"
            "<p>Re-run <code>python pipelines/refresh.py</code> to generate prediction drivers.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Prediction metadata ───────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-heading">Prediction metadata</div>', unsafe_allow_html=True)
    meta_cols = st.columns(3)
    with meta_cols[0]:
        ver = str(row.get("model_version", "—"))[:20]
        st.metric("Model version", ver)
    with meta_cols[1]:
        best_p = max(p_h, p_d, p_a)
        st.metric("Confidence", f"{best_p:.1%}")
    with meta_cols[2]:
        created = str(row.get("created_at", "—"))[:19]
        st.metric("Generated", created)

    # ── Data stamp ────────────────────────────────────────────────────────────
    try:
        ts = pd.to_datetime(row.get("created_at", "")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        ts = str(row.get("created_at", "—"))[:19]
    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.25rem;">'
        f"Data as of <code>{ts}</code> · Updates daily via batch</p>",
        unsafe_allow_html=True,
    )
