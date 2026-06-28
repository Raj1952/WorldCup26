"""
Bracket & Simulation — Monte Carlo tournament advancement and title odds.

Road-to-final ladder: Reach R32 → R16 → QF → SF → Final → Champion,
sorted by Champion % descending.

All knockout slots are projected (50k sim re-seeded-bracket) and labeled
clearly. Never injected into Predictions page — Bracket page only.

§0.5/§3: "projected knockout slots displayed only on the Bracket page,
labeled 'Projected' — never injected into Predictions / match-card flow."
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.presentation_layer.theme import DARK
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

_DB_PATH      = "data/tempo.db"
_PRED_PATH    = "predictions.parquet"
_MANUAL_CSV   = "data/manual_results.csv"

# Ladder columns (display order)
_ROUNDS = ["r32_pct", "r16_pct", "qf_pct", "sf_pct", "final_pct", "champion_pct"]
_LABELS = ["R32",     "R16",     "QF",      "SF",      "Final",    "Champion"]

# Design tokens (mirror theme.py; used inline for Plotly/HTML)
_BG      = "rgba(0,0,0,0)"
_SURFACE = "#141417"
_BORDER  = "#2A2A31"
_TEXT    = "#F4F1EA"
_MUTED   = "#A7A39B"
_GOLD    = "#E8B84B"
_WIN     = "#4CA882"


# ── Penalty-draw helpers ──────────────────────────────────────────────────────

_KO_GROUP_LABELS = tuple("ABCDEFGHIJKL")


def _get_unresolved_penalties(
    db_path: str = _DB_PATH,
    manual_path: str = _MANUAL_CSV,
) -> list[tuple]:
    """Return list of (date, home, away, h_score, a_score) for KO draws with no manual winner."""
    import sqlite3 as _sq
    try:
        conn = _sq.connect(db_path)
        df = pd.read_sql(
            "SELECT date, home_team, away_team, home_score, away_score "
            "FROM wc2026_fixtures "
            "WHERE home_score IS NOT NULL AND home_score = away_score "
            "  AND group_label NOT IN ('A','B','C','D','E','F','G','H','I','J','K','L')",
            conn,
        )
        conn.close()
    except Exception:
        return []
    if df.empty:
        return []
    # Check which are already resolved in manual_results.csv
    resolved: set[tuple] = set()
    mp = Path(manual_path)
    if mp.exists():
        try:
            mdf = pd.read_csv(mp)
            if "knockout_winner" in mdf.columns:
                for _, r in mdf[mdf["knockout_winner"].notna()].iterrows():
                    resolved.add((str(r["date"]), str(r["home_team"]), str(r["away_team"])))
        except Exception:
            pass
    result = []
    for _, r in df.iterrows():
        key = (str(r["date"]), str(r["home_team"]), str(r["away_team"]))
        if key not in resolved:
            result.append((
                str(r["date"]), str(r["home_team"]), str(r["away_team"]),
                int(r["home_score"]), int(r["away_score"]),
            ))
    return result


def _penalty_warning_html(unresolved: list[tuple]) -> str:
    items = "".join(
        f"<li><strong>{h} vs {a}</strong> on {d} — ended {hs}–{as_} in 90 min</li>"
        for d, h, a, hs, as_ in unresolved
    )
    return (
        '<div style="background:rgba(232,184,75,0.08);border:1px solid rgba(232,184,75,0.5);'
        'border-radius:6px;padding:0.75rem 1rem;margin-bottom:1rem;">'
        '<strong style="color:#E8B84B;">&#9888; Penalty result needed</strong>'
        f'<ul style="margin:0.5rem 0 0;padding-left:1.2rem;color:var(--text-muted);font-size:0.85rem;">'
        f'{items}</ul>'
        '<p style="color:var(--text-muted);font-size:0.78rem;margin:0.5rem 0 0;">'
        'Add a <code>knockout_winner</code> column to '
        '<code>data/manual_results.csv</code> to resolve the bracket.</p>'
        '</div>'
    )


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _run_simulation() -> pd.DataFrame | None:
    """Run full tournament MC (cached 1 h). Returns None on error."""
    db = Path(_DB_PATH)
    pred = Path(_PRED_PATH)
    if not db.exists():
        return None
    if not pred.exists():
        return None
    try:
        from src.intelligence_layer.monte_carlo import simulate_full_tournament, N_SIMS, SEED
        return simulate_full_tournament(
            str(db), str(pred), n_sims=N_SIMS, seed=SEED
        )
    except Exception as exc:
        st.error(f"Simulation error: {exc}")
        return None


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _hero_html(df: pd.DataFrame) -> str:
    top  = df.iloc[0]
    team = str(top["team"])
    pct  = float(top["champion_pct"])
    std  = float(top["champion_std"])
    ci95 = std * 1.96
    flag = flag_img(get_flag_code(team), width=32, team_name=team)
    # Second favorite
    ctx = ""
    if len(df) > 1:
        s2   = df.iloc[1]
        t2   = str(s2["team"])
        p2   = float(s2["champion_pct"])
        f2   = flag_img(get_flag_code(t2), width=20, team_name=t2)
        ctx  = (
            f'<span class="bracket-hero-ctx">'
            f' · ahead of {f2} {t2} ({p2:.1%})'
            f'</span>'
        )
    return f"""
<div class="bracket-hero-block">
  <div class="bracket-hero-main">
    <span class="bracket-hero-flag">{flag}</span>
    <span class="bracket-hero-team">{team}</span>
    <span class="bracket-hero-pct">{pct:.1%}</span>
    <span class="bracket-hero-label">title probability · ±{ci95:.1%}</span>
    {ctx}
  </div>
</div>"""


def _projected_chip_html() -> str:
    return (
        '<span class="projected-chip">'
        'Projected · 50,000 simulations · seed=42'
        '</span>'
    )


def _ladder_chart(df: pd.DataFrame, max_teams: int = 32) -> go.Figure:
    """
    Heatmap: teams (Y) × rounds (X), colour = probability.
    Champion column uses gold; earlier rounds use muted green.
    """
    top = df.head(max_teams).copy()
    teams = top["team"].tolist()

    # Build 2D matrix: rows = teams (best first at bottom for plotly y-axis)
    z = top[_ROUNDS].values  # (n_teams, 6)
    # Plotly heatmap: first row appears at bottom; we want champion at top
    # So reverse rows
    z_plot   = z[::-1]
    y_labels = teams[::-1]

    # Text annotations
    text = [
        [f"{v:.0%}" if v >= 0.005 else "<1%" for v in row]
        for row in z_plot
    ]

    # Colorscale: near-black → muted green → gold
    colorscale = [
        [0.00, "#111114"],
        [0.05, "#172C22"],
        [0.20, "#2A5040"],
        [0.50, _WIN],
        [0.80, "#B08C2E"],
        [1.00, _GOLD],
    ]

    fig = go.Figure(go.Heatmap(
        z            = z_plot,
        x            = _LABELS,
        y            = y_labels,
        text         = text,
        texttemplate = "%{text}",
        textfont     = dict(
            family = "'JetBrains Mono',monospace",
            size   = 10,
        ),
        colorscale   = colorscale,
        zmin         = 0.0,
        zmax         = 1.0,
        showscale    = False,
        hovertemplate = "<b>%{y}</b><br>%{x}: <b>%{z:.1%}</b><extra></extra>",
        hoverlabel   = dict(
            bgcolor     = "#1C1C21",
            bordercolor = _BORDER,
            font        = dict(family="'Inter',sans-serif", size=12, color=_TEXT),
        ),
        xgap         = 2,
        ygap         = 2,
    ))

    # Gold vertical stripe on Champion column
    fig.add_shape(
        type     = "rect",
        xref     = "paper",
        yref     = "paper",
        x0       = 5 / 6,
        x1       = 1.0,
        y0       = 0,
        y1       = 1,
        fillcolor= f"rgba(232,184,75,0.06)",
        line     = dict(width=0),
        layer    = "below",
    )

    n_rows = len(y_labels)
    height = max(320, 26 * n_rows + 60)

    fig.update_layout(
        template      = "tempo",
        title_text    = "",
        height        = height,
        margin        = dict(l=10, r=10, t=8, b=20),
        xaxis = dict(
            side      = "top",
            tickfont  = dict(family="'Archivo',sans-serif", size=12,
                             color=_TEXT, weight="bold"),
            linecolor = _BORDER,
            showgrid  = False,
        ),
        yaxis = dict(
            tickfont  = dict(family="'Inter',sans-serif", size=10, color=_MUTED),
            linecolor = _BORDER,
            showgrid  = False,
        ),
    )

    return fig


def _uncertainty_chart(df: pd.DataFrame, max_teams: int = 16) -> go.Figure:
    """
    Horizontal bar: Champion% with ±1.96σ error bars.
    Title uncertainty = outcome spread across 50k sims.
    """
    top = df.head(max_teams).copy()
    # Plotly: first entry is bottom in horizontal bar → reverse
    top = top.iloc[::-1].reset_index(drop=True)

    labels  = [str(t) for t in top["team"]]
    pcts    = top["champion_pct"].tolist()
    ci95    = (top["champion_std"] * 1.96).tolist()
    colors  = [_GOLD if i == len(top) - 1 else _WIN for i in range(len(top))]

    fig = go.Figure(go.Bar(
        orientation  = "h",
        x            = pcts,
        y            = labels,
        error_x      = dict(
            type      = "data",
            array     = ci95,
            thickness = 1.5,
            width     = 4,
            color     = _MUTED,
        ),
        marker       = dict(
            color       = colors,
            opacity     = 0.85,
            line        = dict(width=0),
        ),
        text         = [f"{p:.1%}" for p in pcts],
        textposition = "outside",
        textfont     = dict(
            family = "'JetBrains Mono',monospace",
            size   = 10,
            color  = _MUTED,
        ),
        hovertemplate = "<b>%{y}</b><br>Champion: <b>%{x:.1%}</b><extra></extra>",
        hoverlabel    = dict(
            bgcolor     = "#1C1C21",
            bordercolor = _BORDER,
            font        = dict(family="'Inter',sans-serif", size=12, color=_TEXT),
        ),
        cliponaxis = False,
    ))

    fig.update_layout(
        template  = "tempo",
        height    = max(260, 24 * len(top) + 60),
        margin    = dict(l=10, r=80, t=48, b=10),
        title     = dict(
            text = (
                "Champion probability — top 16 · error bars = ±95% CI<br>"
                "<sup style='font-size:10px;color:#A7A39B'>"
                "Outcome spread across 50,000 simulations — not sampling error"
                "</sup>"
            ),
            font = dict(family="'Archivo',sans-serif", size=14, color=_TEXT),
            x    = 0.01,
        ),
        xaxis = dict(
            tickformat = ".0%",
            gridcolor  = _BORDER,
            gridwidth  = 1,
            tickfont   = dict(family="'JetBrains Mono',monospace", size=9, color=_MUTED),
            range      = [0, max(pcts) * 1.35],
        ),
        yaxis = dict(
            tickfont  = dict(family="'Inter',sans-serif", size=10, color=_MUTED),
            linecolor = _BORDER,
            showgrid  = False,
        ),
        showlegend = False,
    )

    return fig


# ── Page ──────────────────────────────────────────────────────────────────────

def render(theme=DARK) -> None:
    st.markdown(
        '<style>'
        '.bracket-hero-block {'
        '  margin: 0.5rem 0 1.2rem;'
        '  padding: 1rem 1.4rem;'
        '  background: var(--surface);'
        '  border: 1px solid var(--border);'
        '  border-radius: var(--radius-md);'
        '  border-left: 3px solid var(--gold);'
        '}'
        '.bracket-hero-main {'
        '  display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem;'
        '}'
        '.bracket-hero-flag { line-height:1; }'
        '.bracket-hero-team {'
        '  font-family: "Archivo",sans-serif; font-weight: 900; font-size: 1.35rem;'
        '  color: var(--text); letter-spacing: -0.02em;'
        '}'
        '.bracket-hero-pct {'
        '  font-family: "JetBrains Mono",monospace; font-weight: 700; font-size: 1.5rem;'
        '  color: var(--gold);'
        '}'
        '.bracket-hero-label {'
        '  font-family: "Inter",sans-serif; font-size: 0.82rem; color: var(--text-muted);'
        '}'
        '.bracket-hero-ctx {'
        '  font-family: "Inter",sans-serif; font-size: 0.82rem; color: var(--text-muted);'
        '  display: flex; align-items: center; gap: 0.25rem;'
        '}'
        '.projected-chip {'
        '  display: inline-flex; align-items: center;'
        '  font-family: "JetBrains Mono",monospace; font-size: 0.65rem;'
        '  text-transform: uppercase; letter-spacing: 0.08em;'
        '  color: var(--text-muted);'
        '  border: 1px dashed var(--border);'
        '  border-radius: 5px;'
        '  padding: 3px 8px;'
        '  margin-bottom: 0.75rem;'
        '}'
        '</style>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-header">'
        '<h1>Bracket &amp; Simulation</h1>'
        '<p class="subtitle">'
        'Monte Carlo tournament simulation — 50,000 runs · seed=42 · '
        'conditioned on current group standings'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Run simulation ────────────────────────────────────────────────────────
    db_ok   = Path(_DB_PATH).exists()
    pred_ok = Path(_PRED_PATH).exists()

    if not db_ok or not pred_ok:
        st.markdown(
            '<div class="no-data">'
            '<h3>Tournament simulation is updating</h3>'
            '<p>Results will appear after the next daily refresh — '
            'predictions update every morning.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Penalty-draw warning ──────────────────────────────────────────────────
    _unresolved = _get_unresolved_penalties(_DB_PATH, _MANUAL_CSV)
    if _unresolved:
        st.markdown(_penalty_warning_html(_unresolved), unsafe_allow_html=True)

    with st.spinner("Running 50,000 tournament simulations…"):
        df = _run_simulation()

    if df is None or df.empty:
        st.markdown(
            '<div class="no-data">'
            '<h3>Simulation results unavailable</h3>'
            '<p>Tournament simulation will be ready after the next daily refresh.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Hero text ─────────────────────────────────────────────────────────────
    st.markdown(_hero_html(df), unsafe_allow_html=True)

    # ── Projected chip ────────────────────────────────────────────────────────
    st.markdown(_projected_chip_html(), unsafe_allow_html=True)

    # ── Road-to-final ladder ──────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Road to Final — advancement odds by round</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _ladder_chart(df, max_teams=32),
        width="stretch",
        key="ladder_chart",
    )

    st.markdown(
        '<p style="color:var(--text-muted);font-size:0.72rem;'
        'font-family:\'JetBrains Mono\',monospace;margin:-0.5rem 0 1rem;">'
        'Knockout bracket: re-seeded by Elo before each round · '
        'no draw in knockout matches · values are projected, not confirmed'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Title uncertainty ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">Title uncertainty — outcome spread across simulations</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _uncertainty_chart(df, max_teams=16),
        width="stretch",
        key="uncertainty_chart",
    )

    # ── Data stamp ────────────────────────────────────────────────────────────
    try:
        pred_ts = pd.read_parquet(_PRED_PATH, columns=["created_at"])["created_at"].max()
        ts_str  = pd.to_datetime(pred_ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        ts_str = "unknown"

    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.25rem;">'
        f'Predictions as of <code>{ts_str}</code> · '
        f'Updates daily via batch · '
        f'50,000 Monte Carlo simulations · seed=42</p>',
        unsafe_allow_html=True,
    )
