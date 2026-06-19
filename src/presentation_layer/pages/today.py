"""Predictions page — broadcast-grade match cards with real model output."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.presentation_layer.theme import DARK, APP_NAME
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

_PREDICTIONS_PATH = Path("predictions.parquet")


@st.cache_data(ttl=60)
def _load_predictions() -> pd.DataFrame:
    if not _PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(_PREDICTIONS_PATH)
    df["top_factors"] = df["top_factors"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
    )
    return df


def _prob_bar_html(p_home: float, p_draw: float, p_away: float,
                   home: str, away: str) -> str:
    min_show = 0.09
    total = p_home + p_draw + p_away
    ph = p_home / total
    pd_ = p_draw / total
    pa = p_away / total
    h_lbl = f"{ph:.0%}" if ph >= min_show else ""
    d_lbl = f"{pd_:.0%}" if pd_ >= min_show else ""
    a_lbl = f"{pa:.0%}" if pa >= min_show else ""
    return f"""
<div class="prob-bar-track" role="img"
     aria-label="{home} {ph:.0%} win, Draw {pd_:.0%}, {away} {pa:.0%} win">
  <div class="prob-seg seg-home" style="flex:{ph:.4f}">{h_lbl}</div>
  <div class="prob-seg seg-draw" style="flex:{pd_:.4f}">{d_lbl}</div>
  <div class="prob-seg seg-away" style="flex:{pa:.4f}">{a_lbl}</div>
</div>
<div class="prob-bar-labels">
  <span class="prob-label">Home win</span>
  <span class="prob-label">Draw</span>
  <span class="prob-label">Away win</span>
</div>"""


def _favored_html(p_home: float, p_draw: float, p_away: float,
                  home: str, away: str, hf: str, af: str) -> str:
    best = max(p_home, p_draw, p_away)
    if best == p_home:
        label, flag, conf = home, hf, p_home
    elif best == p_away:
        label, flag, conf = away, af, p_away
    else:
        label, flag, conf = "Draw likely", "🤝", p_draw
    return (
        f'<div class="favored-chip">'
        f'<span class="favored-dot"></span>'
        f'Favored: <strong>{flag} {label}</strong>'
        f'<span style="opacity:0.7;margin-left:6px;">{conf:.0%}</span>'
        f"</div>"
    )


def _factors_html(factors: list[dict]) -> str:
    if not factors:
        return ""
    chips = "".join(
        f'<span class="factor-chip {"fpos" if f.get("direction","+")=="+"\
            else "fneg"}">{"↑" if f.get("direction","+")=="+"\
            else "↓"} {f.get("label","")}</span>'
        for f in factors[:3]
    )
    return f'<div class="factors-row">{chips}</div>'


def _match_card_html(row: pd.Series) -> str:
    home = row["home_team"]
    away = row["away_team"]
    p_h = float(row["p_home"])
    p_d = float(row["p_draw"])
    p_a = float(row["p_away"])
    hf = flag_img(get_flag_code(home), width=30, team_name=home)
    af = flag_img(get_flag_code(away), width=30, team_name=away)
    group = row.get("group_label", "WC26")
    kt = str(row.get("kickoff_time", ""))
    date_str = str(row.get("date", ""))

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = dt.strftime("%a %d %b")
    except Exception:
        date_label = date_str

    time_label = f" · {kt} UTC" if kt and kt not in ("00:00", "nan", "") else ""
    chip_text = f"WC26 · Grp {group} · {date_label}{time_label}"

    factors = row.get("top_factors", [])
    if isinstance(factors, str):
        try:
            factors = json.loads(factors)
        except Exception:
            factors = []

    return f"""
<div class="match-card">
  <div class="match-card-rail"></div>
  <div class="match-card-body">
    <div class="match-chip">{chip_text}</div>
    <div class="match-teams">
      <div class="team-block">
        <span class="team-flag">{hf}</span>
        <span class="team-name">{home}</span>
      </div>
      <span class="match-vs">VS</span>
      <div class="team-block away">
        <span class="team-flag">{af}</span>
        <span class="team-name">{away}</span>
      </div>
    </div>
    {_prob_bar_html(p_h, p_d, p_a, home, away)}
    {_favored_html(p_h, p_d, p_a, home, away, hf, af)}
    {_factors_html(factors)}
  </div>
</div>"""


def _group_donut(df: pd.DataFrame) -> go.Figure:
    """Donut showing predicted outcome distribution across all upcoming matches."""
    favored_home = (df["p_home"] > df["p_draw"]) & (df["p_home"] > df["p_away"])
    favored_draw = (df["p_draw"] >= df["p_home"]) & (df["p_draw"] >= df["p_away"])
    favored_away = (df["p_away"] > df["p_home"]) & (df["p_away"] > df["p_draw"])
    vals = [favored_home.sum(), favored_draw.sum(), favored_away.sum()]
    fig = go.Figure(go.Pie(
        labels=["Home favored", "Draw likely", "Away favored"],
        values=vals,
        hole=0.65,
        marker=dict(colors=["#1FB479", "#3E7BFA", "#E4564A"],
                    line=dict(color="#0B0B0D", width=2)),
        textfont=dict(family="'JetBrains Mono',monospace", size=11),
        hovertemplate="%{label}: <b>%{value}</b> matches<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#A7A39B", size=10),
                    orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        height=220,
        margin=dict(l=0, r=0, t=10, b=30),
        annotations=[dict(
            text=f"<b>{len(df)}</b><br><span style='font-size:10px'>matches</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color="#E8B84B", family="'JetBrains Mono',monospace"),
        )],
    )
    return fig


def _no_data_banner() -> None:
    st.markdown("""
<div class="no-data">
  <h3>No predictions yet</h3>
  <p>Run the refresh pipeline to fetch data and generate predictions:</p>
  <p><code>python pipelines/refresh.py</code></p>
  <p style="margin-top:1rem;font-size:0.8rem;color:var(--text-muted);">
    This downloads historical match data, trains the XGBoost model, and writes predictions.parquet.
  </p>
</div>""", unsafe_allow_html=True)


def render(theme=DARK) -> None:
    # ── Page header ──────────────────────────────────────────────────────
    st.markdown('<div class="accent-rail"></div>', unsafe_allow_html=True)

    col_title, col_badge = st.columns([3, 1])
    with col_title:
        st.markdown(
            f'<div class="page-header">'
            f'<h1>⚽ {APP_NAME}</h1>'
            f'<p class="subtitle">FIFA World Cup 2026 · AI-powered match predictions</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_badge:
        st.markdown(
            '<div style="padding-top:1.4rem;text-align:right;">'
            '<span style="font-size:0.7rem;color:var(--text-muted);font-family:var(--ff-mono);">'
            'Updates daily via batch</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    df = _load_predictions()

    if df.empty:
        _no_data_banner()
        return

    today = str(date.today())
    upcoming = df[df["date"] >= today].copy().sort_values("date")
    # Known-team matches only — per §0.5/§3: hide placeholder knockout rows until Monte Carlo (R6)
    upcoming = upcoming[upcoming["group_label"].str.match(r"^[A-L]$", na=False)].copy()

    # ── Summary metrics row ───────────────────────────────────────────────
    today_matches = upcoming[upcoming["date"] == today]
    avg_conf = float(upcoming[["p_home", "p_draw", "p_away"]].max(axis=1).mean()) if not upcoming.empty else 0
    model_v = str(df["model_version"].iloc[0])[:18] if not df.empty else "—"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Today's Matches", len(today_matches))
    with c2:
        st.metric("Upcoming Matches", len(upcoming))
    with c3:
        st.metric("Avg Confidence", f"{avg_conf:.0%}")
    with c4:
        st.metric("Model", model_v.split("_")[0].upper() if "_" in model_v else model_v[:10])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sidebar-style filters + donut ─────────────────────────────────────
    col_filters, col_cards = st.columns([1, 3])

    with col_filters:
        st.markdown('<div class="sec-heading">Filters</div>', unsafe_allow_html=True)

        all_groups = sorted(upcoming["group_label"].dropna().unique().tolist())
        sel_groups = st.multiselect("Group / Stage", all_groups, default=all_groups,
                                    label_visibility="collapsed",
                                    placeholder="All groups")
        if not sel_groups:
            sel_groups = all_groups

        date_options = sorted(upcoming["date"].unique().tolist())
        date_labels = []
        for d in date_options:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d")
                prefix = "🔴 " if d == today else ""
                date_labels.append(f"{prefix}{dt.strftime('%a %d %b')}")
            except Exception:
                date_labels.append(d)

        date_map = dict(zip(date_labels, date_options))
        sel_date_labels = st.multiselect("Date", date_labels,
                                          default=date_labels[:3] if len(date_labels) > 3 else date_labels,
                                          label_visibility="collapsed",
                                          placeholder="All dates")
        sel_dates = [date_map[l] for l in sel_date_labels] if sel_date_labels else date_options

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-heading">Outlook</div>', unsafe_allow_html=True)
        if not upcoming.empty:
            st.plotly_chart(_group_donut(upcoming), use_container_width=True)

    with col_cards:
        filtered = upcoming[
            upcoming["group_label"].isin(sel_groups) &
            upcoming["date"].isin(sel_dates)
        ]

        if filtered.empty:
            st.markdown(
                '<p style="color:var(--text-muted);padding:1rem 0;">No matches match the selected filters.</p>',
                unsafe_allow_html=True,
            )
        else:
            # Group by date
            for match_date, group_df in filtered.groupby("date"):
                try:
                    dt = datetime.strptime(str(match_date), "%Y-%m-%d")
                    is_today = str(match_date) == today
                    day_lbl = ("🔴 Today — " if is_today else "") + dt.strftime("%A, %d %B %Y")
                except Exception:
                    day_lbl = str(match_date)

                st.markdown(
                    f'<div class="sec-heading">{day_lbl}</div>',
                    unsafe_allow_html=True,
                )
                cols = st.columns(min(2, len(group_df)))
                for i, (_, row) in enumerate(group_df.iterrows()):
                    with cols[i % len(cols)]:
                        st.markdown(_match_card_html(row), unsafe_allow_html=True)

    # ── Data stamp ────────────────────────────────────────────────────────
    if not df.empty:
        try:
            created = pd.to_datetime(df["created_at"].iloc[0]).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            created = str(df["created_at"].iloc[0])[:19]
        st.markdown(
            f'<p class="data-stamp" style="margin-top:1rem;">Data as of {created} · '
            f'Refresh: <code>python pipelines/refresh.py</code></p>',
            unsafe_allow_html=True,
        )
