"""Predictions page — First Answer rule, One Hero, chip filters, fixture tickets."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.presentation_layer.theme import DARK
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

_PREDICTIONS_PATH = Path("predictions.parquet")

_REQUIRED_COLS = frozenset({
    "match_id", "date", "home_team", "away_team",
    "p_home", "p_draw", "p_away",
    "model_version", "created_at",
})


@st.cache_data(ttl=60)
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
    except Exception:
        return pd.DataFrame()


def _prob_bar_html(p_home: float, p_draw: float, p_away: float,
                   home: str, away: str) -> str:
    total = p_home + p_draw + p_away
    ph = p_home / total
    pd_ = p_draw / total
    pa = p_away / total
    MIN_SHOW = 0.09
    h_lbl = f"{ph:.0%}" if ph >= MIN_SHOW else ""
    d_lbl = f"{pd_:.0%}" if pd_ >= MIN_SHOW else ""
    a_lbl = f"{pa:.0%}" if pa >= MIN_SHOW else ""
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
        label, flag, conf = "Draw likely", "", p_draw
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
        f'<span class="factor-chip '
        f'{"fpos" if f.get("direction", "+") == "+" else "fneg"}">'
        f'{"↑" if f.get("direction", "+") == "+" else "↓"} {f.get("label", "")}'
        f'</span>'
        for f in factors[:3]
    )
    return f'<div class="factors-row">{chips}</div>'


def _hero_card_html(row: pd.Series) -> str:
    """Full-width hero card — next fixture, large team names, taller prob bar."""
    home = row["home_team"]
    away = row["away_team"]
    p_h = float(row["p_home"])
    p_d = float(row["p_draw"])
    p_a = float(row["p_away"])
    hf = flag_img(get_flag_code(home), width=44, team_name=home)
    af = flag_img(get_flag_code(away), width=44, team_name=away)
    group = row.get("group_label", "WC26")
    kt = str(row.get("kickoff_time", ""))
    date_str = str(row.get("date", ""))

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        is_today = date_str == str(date.today())
        date_label = "Today" if is_today else dt.strftime("%a %d %b")
    except Exception:
        date_label = date_str
        is_today = False

    time_label = f" · {kt} UTC" if kt and kt not in ("00:00", "nan", "") else ""
    kick_badge = "Today's kick-off" if is_today else "Next kick-off"
    chip_text = f"WC26 · Grp {group} · {date_label}{time_label}"

    factors = row.get("top_factors", [])
    if isinstance(factors, str):
        try:
            factors = json.loads(factors)
        except Exception:
            factors = []

    return f"""
<div class="match-card hero-card">
  <div class="match-card-rail"></div>
  <div class="match-card-body">
    <div style="display:flex;align-items:center;justify-content:space-between;
                flex-wrap:wrap;gap:0.5rem;margin-bottom:0.85rem;">
      <span class="hero-badge"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align:middle;margin-right:3px;"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>{kick_badge}</span>
      <span class="match-chip" style="margin-bottom:0;">{chip_text}</span>
    </div>
    <div class="match-teams" style="margin-bottom:1.1rem;">
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
    {_prob_bar_html(p_h, p_d, p_a, home, away)}
    {_favored_html(p_h, p_d, p_a, home, away, hf, af)}
    {_factors_html(factors)}
  </div>
</div>"""


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


def _no_data_banner() -> None:
    st.markdown("""
<div class="no-data">
  <h3>No predictions yet</h3>
  <p>Run the refresh pipeline to fetch data and generate predictions:</p>
  <p><code>python pipelines/refresh.py</code></p>
  <p style="margin-top:1rem;font-size:0.8rem;color:var(--text-muted);">
    Downloads historical data, trains the XGBoost model, writes predictions.parquet.
  </p>
</div>""", unsafe_allow_html=True)


def render(theme=DARK) -> None:
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
            _no_data_banner()
        return

    today_str = str(date.today())
    upcoming = df[df["date"] >= today_str].copy()
    # Known-team group-stage matches only — per §0.5/§3 (no placeholder knockouts until R6)
    upcoming = upcoming[upcoming["group_label"].str.match(r"^[A-L]$", na=False)].copy()

    sort_cols = ["date", "kickoff_time"] if "kickoff_time" in upcoming.columns else ["date"]
    upcoming = upcoming.sort_values(sort_cols).reset_index(drop=True)

    if upcoming.empty:
        _no_data_banner()
        return

    # ── Hero match — First Answer + One Hero rules ────────────────────────────
    # Next known-team fixture by kickoff: always the first visible element.
    hero_row = upcoming.iloc[0]
    hero_idx = 0  # reset_index guarantees this
    st.markdown(_hero_card_html(hero_row), unsafe_allow_html=True)

    # ── Chip filters ──────────────────────────────────────────────────────────
    all_groups = sorted(upcoming["group_label"].dropna().unique().tolist())

    st.markdown('<div class="filter-label">Group</div>', unsafe_allow_html=True)
    sel_group = st.radio(
        "Group filter",
        options=["All"] + all_groups,
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        key="pred_group_chip",
    )

    filtered = upcoming if sel_group == "All" else upcoming[upcoming["group_label"] == sel_group]

    # Date chips are derived from the group-filtered set
    all_dates = sorted(filtered["date"].unique().tolist())
    date_label_map: dict[str, str] = {}
    date_display: list[str] = []
    for d in all_dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            lbl = "Today" if d == today_str else dt.strftime("%a %d")
        except Exception:
            lbl = d
        date_label_map[lbl] = d
        date_display.append(lbl)

    st.markdown('<div class="filter-label">Date</div>', unsafe_allow_html=True)
    sel_date_label = st.radio(
        "Date filter",
        options=["All"] + date_display,
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        key="pred_date_chip",
    )

    if sel_date_label == "All":
        view = filtered
    else:
        sel_date = date_label_map.get(sel_date_label)
        view = filtered[filtered["date"] == sel_date] if sel_date else filtered

    # Grid always excludes the hero row — it's shown above the fold
    grid = view[view.index != hero_idx]

    st.markdown("<div style='margin-top:1.1rem;'></div>", unsafe_allow_html=True)

    # ── Match grid ────────────────────────────────────────────────────────────
    if grid.empty:
        if sel_group != "All" or sel_date_label != "All":
            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.82rem;padding:0.25rem 0;">'
                "No other matches match the selected filters.</p>",
                unsafe_allow_html=True,
            )
    else:
        for match_date, date_group in grid.groupby("date", sort=True):
            try:
                dt = datetime.strptime(str(match_date), "%Y-%m-%d")
                is_td = str(match_date) == today_str
                day_lbl = ("Today — " if is_td else "") + dt.strftime("%A, %d %B %Y")
            except Exception:
                day_lbl = str(match_date)

            st.markdown(f'<div class="sec-heading">{day_lbl}</div>', unsafe_allow_html=True)
            cols = st.columns(2)
            for i, (_, row) in enumerate(date_group.iterrows()):
                with cols[i % 2]:
                    st.markdown(_match_card_html(row), unsafe_allow_html=True)

    # ── Data stamp ────────────────────────────────────────────────────────────
    if not df.empty:
        try:
            created = pd.to_datetime(df["created_at"].iloc[0]).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            created = str(df["created_at"].iloc[0])[:19]
        st.markdown(
            f'<p class="data-stamp" style="margin-top:1.5rem;">Data as of <code>{created}</code> · '
            f'Updates daily via batch</p>',
            unsafe_allow_html=True,
        )
