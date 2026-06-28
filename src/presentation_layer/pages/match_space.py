"""
Match Space — Scatterternary of upcoming group-stage matches in W/D/L space.

Desktop: click point → gold ring + comparative context + consequence chain.
Mobile:  text selectbox below chart (same session_state key, same panels).
§0.5: every chart must filter or reveal on interaction.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.presentation_layer.theme import DARK
from src.presentation_layer.charts.ternary import ternary_scatter
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img

_PREDICTIONS_PATH = Path("predictions.parquet")
_DB_PATH          = Path("data/tempo.db")
_SK = "ms_selected"   # session_state key

_REQUIRED_COLS = frozenset({
    "match_id", "date", "home_team", "away_team",
    "p_home", "p_draw", "p_away",
    "model_version", "created_at",
})


# ── Data loading ──────────────────────────────────────────────────────────────

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


@st.cache_data(ttl=3600, show_spinner=False)
def _load_elo() -> dict[str, float]:
    """Return {team: current_elo} from elo_current table."""
    if not _DB_PATH.exists():
        return {}
    try:
        con = sqlite3.connect(str(_DB_PATH))
        rows = con.execute("SELECT team, elo FROM elo_current").fetchall()
        con.close()
        return {r[0]: float(r[1]) for r in rows}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _load_sim() -> pd.DataFrame | None:
    """Run full-tournament Monte Carlo (cached 1 h). Returns None on failure."""
    if not _DB_PATH.exists() or not _PREDICTIONS_PATH.exists():
        return None
    try:
        from src.intelligence_layer.monte_carlo import simulate_full_tournament, N_SIMS, SEED
        return simulate_full_tournament(str(_DB_PATH), str(_PREDICTIONS_PATH),
                                        n_sims=N_SIMS, seed=SEED)
    except Exception:
        return None


# ── Neighbor calculation ──────────────────────────────────────────────────────

def _find_neighbors(row: pd.Series, upcoming: pd.DataFrame, k: int = 3) -> list[int]:
    """Return k nearest match indices in (p_home, p_draw, p_away) space."""
    sel  = np.array([float(row["p_home"]), float(row["p_draw"]), float(row["p_away"])])
    pts  = upcoming[["p_home", "p_draw", "p_away"]].values.astype(float)
    dist = np.sqrt(((pts - sel) ** 2).sum(axis=1))
    return [int(i) for i in np.argsort(dist) if dist[i] > 1e-9][:k]


# ── Panel 1: Comparative Context ──────────────────────────────────────────────

def _context_strip_html(
    row: pd.Series,
    upcoming: pd.DataFrame,
    elo_map: dict[str, float],
    neighbor_idxs: list[int],
) -> str:
    home = str(row["home_team"])
    away = str(row["away_team"])

    # Confidence: max probability for this match vs tournament average
    conf     = max(float(row["p_home"]), float(row["p_draw"]), float(row["p_away"]))
    conf_avg = float(upcoming[["p_home", "p_draw", "p_away"]].max(axis=1).mean())
    conf_delta = conf - conf_avg
    conf_tag   = "above avg" if conf_delta > 0.005 else ("below avg" if conf_delta < -0.005 else "at avg")
    conf_color = "var(--win)" if conf_delta > 0.005 else ("var(--loss)" if conf_delta < -0.005 else "var(--text-muted)")

    # Elo gap: |elo_home - elo_away| vs tournament average
    h_elo = elo_map.get(home)
    a_elo = elo_map.get(away)
    if h_elo and a_elo:
        gap = abs(h_elo - a_elo)
        all_gaps = [
            abs(elo_map[str(r["home_team"])] - elo_map[str(r["away_team"])])
            for _, r in upcoming.iterrows()
            if str(r["home_team"]) in elo_map and str(r["away_team"]) in elo_map
        ]
        avg_gap     = sum(all_gaps) / len(all_gaps) if all_gaps else None
        gap_str     = f"{gap:.0f}"
        avg_gap_str = f"tourn avg: {avg_gap:.0f}" if avg_gap else "—"
        gap_delta   = gap - avg_gap if avg_gap else 0
        gap_tag     = "larger gap" if gap_delta > 5 else ("smaller gap" if gap_delta < -5 else "near avg")
        gap_color   = "var(--win)" if gap_delta > 5 else ("var(--loss)" if gap_delta < -5 else "var(--text-muted)")
    else:
        gap_str     = "—"
        avg_gap_str = "—"
        gap_tag     = ""
        gap_color   = "var(--text-muted)"

    # Similar matches: gold chips
    nbr_chips = ""
    for ni in neighbor_idxs:
        if 0 <= ni < len(upcoming):
            nr  = upcoming.iloc[ni]
            h3  = str(nr["home_team"])[:3].upper()
            a3  = str(nr["away_team"])[:3].upper()
            nbr_chips += (
                f'<span style="display:inline-flex;align-items:center;'
                f'background:rgba(232,184,75,0.08);border:1px solid rgba(232,184,75,0.25);'
                f'border-radius:5px;padding:2px 7px;margin:2px 4px 2px 0;'
                f'font-family:\'JetBrains Mono\',monospace;font-size:0.67rem;'
                f'color:var(--gold);letter-spacing:0.04em;">'
                f'{h3}–{a3}</span>'
            )
    if not nbr_chips:
        nbr_chips = '<span style="color:var(--text-muted);font-size:0.8rem;">—</span>'

    cell = "display:flex;flex-direction:column;justify-content:center;padding:0.85rem 1.2rem;"
    div  = "width:1px;background:var(--border);flex-shrink:0;margin:0.4rem 0;"
    lbl  = ("font-family:'Inter',sans-serif;font-size:0.72rem;text-transform:uppercase;"
            "letter-spacing:0.1em;color:var(--text-muted);margin-bottom:0.3rem;")
    sub  = "font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:var(--text-muted);margin-top:0.15rem;"

    return f"""
<div style="display:flex;align-items:stretch;border:1px solid var(--border);
            border-radius:var(--radius-md);overflow:hidden;margin-bottom:1rem;">
  <div style="{cell}">
    <div style="{lbl}">Confidence</div>
    <div style="display:flex;align-items:baseline;gap:0.45rem;">
      <span style="font-family:'JetBrains Mono',monospace;font-size:1.45rem;
                   font-weight:700;color:var(--gold);">{conf:.0%}</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;
                   color:{conf_color};">{conf_tag}</span>
    </div>
    <div style="{sub}">tourn avg: {conf_avg:.0%}</div>
  </div>

  <div style="{div}"></div>

  <div style="{cell}">
    <div style="{lbl}">Elo gap</div>
    <div style="display:flex;align-items:baseline;gap:0.45rem;">
      <span style="font-family:'JetBrains Mono',monospace;font-size:1.45rem;
                   font-weight:700;color:var(--gold);">{gap_str}</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;
                   color:{gap_color};">{gap_tag}</span>
    </div>
    <div style="{sub}">{avg_gap_str}</div>
  </div>

  <div style="{div}"></div>

  <div style="{cell}flex:1;min-width:0;">
    <div style="{lbl}">Similar matches</div>
    <div style="margin:0.1rem 0 0.2rem;flex-wrap:wrap;">{nbr_chips}</div>
    <div style="{sub}">highlighted on chart above</div>
  </div>
</div>"""


# ── Panel 2: Consequence Chain ────────────────────────────────────────────────

def _consequence_chain_html(row: pd.Series, sim: pd.DataFrame | None) -> str:
    home = str(row["home_team"])
    away = str(row["away_team"])

    def _team_data(team: str) -> dict | None:
        if sim is None:
            return None
        mask = sim["team"] == team
        if not mask.any():
            return None
        r = sim[mask].iloc[0]
        return {
            "r32":   float(r.get("r32_pct",   0)),
            "r16":   float(r.get("r16_pct",   0)),
            "qf":    float(r.get("qf_pct",    0)),
            "champ": float(r.get("champion_pct", 0)),
        }

    home_data = _team_data(home)
    away_data = _team_data(away)
    home_flag = flag_img(get_flag_code(home), width=24, team_name=home)
    away_flag = flag_img(get_flag_code(away), width=24, team_name=away)

    arrow = (
        '<span style="color:var(--border);font-size:1.1rem;'
        'padding:0 0.3rem;flex-shrink:0;">→</span>'
    )

    def _node(label: str, pct: float, is_champ: bool = False) -> str:
        val_color = "var(--gold)" if is_champ else "var(--text)"
        return (
            f'<div style="text-align:center;min-width:52px;flex-shrink:0;">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;'
            f'font-size:0.95rem;color:{val_color};">{pct:.0%}</div>'
            f'<div style="font-family:\'Inter\',sans-serif;font-size:0.62rem;'
            f'color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;">{label}</div>'
            f'</div>'
        )

    def _r32_node(pct: float) -> str:
        return (
            f'<div style="text-align:center;min-width:72px;flex-shrink:0;">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-weight:700;'
            f'font-size:0.95rem;color:var(--text);">{pct:.0%}</div>'
            f'<div style="font-family:\'Inter\',sans-serif;font-size:0.62rem;'
            f'color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;">to R32</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.58rem;'
            f'color:var(--text-muted);margin-top:2px;">opp: TBD via sim</div>'
            f'</div>'
        )

    def _no_sim_row(flag: str, team: str) -> str:
        return (
            f'<div style="display:flex;align-items:center;gap:0.5rem;padding:0.55rem 0;">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;min-width:140px;">'
            f'{flag}'
            f'<span style="font-family:\'Archivo\',sans-serif;font-weight:800;'
            f'font-size:0.92rem;color:var(--text);">{team}</span>'
            f'</div>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;'
            f'color:var(--text-muted);">sim data loading…</span>'
            f'</div>'
        )

    def _team_row(flag: str, team: str, data: dict | None, is_last: bool) -> str:
        border = "" if is_last else "border-bottom:1px solid var(--border);"
        if data is None:
            return (
                f'<div style="display:flex;align-items:center;gap:0.5rem;'
                f'padding:0.55rem 0;{border}">'
                f'<div style="display:flex;align-items:center;gap:0.5rem;min-width:140px;">'
                f'{flag}'
                f'<span style="font-family:\'Archivo\',sans-serif;font-weight:800;'
                f'font-size:0.92rem;color:var(--text);">{team}</span>'
                f'</div>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;'
                f'color:var(--text-muted);">—</span>'
                f'</div>'
            )
        return (
            f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:0.15rem;'
            f'padding:0.55rem 0;{border}">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;'
            f'min-width:140px;flex-shrink:0;">'
            f'{flag}'
            f'<span style="font-family:\'Archivo\',sans-serif;font-weight:800;'
            f'font-size:0.92rem;color:var(--text);">{team}</span>'
            f'</div>'
            f'{arrow}'
            f'{_r32_node(data["r32"])}'
            f'{arrow}'
            f'{_node("to QF", data["qf"])}'
            f'{arrow}'
            f'{_node("Champion", data["champ"], is_champ=True)}'
            f'</div>'
        )

    no_sim_note = ""
    if sim is None:
        no_sim_note = (
            '<p style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;'
            'color:var(--text-muted);margin:0.5rem 0 0;">'
            'Run <code>python pipelines/refresh.py --monte-carlo</code> for simulation data.</p>'
        )

    return (
        f'<div style="padding:0.25rem 0;">'
        f'{_team_row(home_flag, home, home_data, is_last=False)}'
        f'{_team_row(away_flag, away, away_data, is_last=True)}'
        f'{no_sim_note}'
        f'</div>'
    )


# ── Page ──────────────────────────────────────────────────────────────────────

def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Match Space</h1>"
        '<p class="subtitle">'
        "Win / Draw / Loss probability space — click a point to inspect"
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

    today_str = str(date.today())
    upcoming  = (
        df[df["date"] >= today_str]
        .pipe(lambda d: d[d["p_home"].notna()])
        .copy()
        .sort_values(["date", "kickoff_time"])
        .reset_index(drop=True)
    )

    if upcoming.empty:
        st.info("No upcoming matches with concrete predictions. Check back after the next daily refresh.")
        return

    selected: int | None = st.session_state.get(_SK)

    # Compute neighbors BEFORE rendering ternary so they can be highlighted.
    neighbor_idxs: list[int] = []
    if selected is not None and 0 <= selected < len(upcoming):
        neighbor_idxs = _find_neighbors(upcoming.iloc[selected], upcoming)

    # ── Ternary ───────────────────────────────────────────────────────────────
    fig   = ternary_scatter(upcoming, selected_idx=selected, neighbor_idxs=neighbor_idxs)
    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        key="ternary_chart",
    )

    # Resolve click → update session_state.
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
    labels      = [
        f"{r['home_team']} vs {r['away_team']}  ·  {r['date']}"
        for _, r in upcoming.iterrows()
    ]
    sel_options = ["— select a match —"] + labels
    cur_label   = labels[selected] if (selected is not None and selected < len(labels)) else sel_options[0]
    chosen      = st.selectbox(
        "Select match",
        sel_options,
        index=sel_options.index(cur_label) if cur_label in sel_options else 0,
        label_visibility="collapsed",
        key="ms_selectbox",
    )
    if chosen != sel_options[0]:
        new_pos = labels.index(chosen)
        if new_pos != selected:
            st.session_state[_SK] = new_pos
            st.rerun()
    elif chosen == sel_options[0] and selected is not None:
        st.session_state[_SK] = None
        st.rerun()

    # ── Detail panels ─────────────────────────────────────────────────────────
    st.markdown(
        '<hr style="border-color:var(--border);margin:0.75rem 0 1rem;">',
        unsafe_allow_html=True,
    )

    if selected is not None and 0 <= selected < len(upcoming):
        row     = upcoming.iloc[selected]
        elo_map = _load_elo()

        # Panel 1 — Comparative Context
        st.markdown(
            '<div class="sec-heading">Where this match sits</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _context_strip_html(row, upcoming, elo_map, neighbor_idxs),
            unsafe_allow_html=True,
        )

        # Panel 2 — Consequence Chain
        st.markdown(
            '<div class="sec-heading">What happens next</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Loading simulation…"):
            sim = _load_sim()
        st.markdown(
            _consequence_chain_html(row, sim),
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            '<p style="color:var(--text-muted);font-size:0.85rem;padding:0.2rem 0 1rem;">'
            "Click a point above or use the selector — context and consequence panels reveal here.</p>",
            unsafe_allow_html=True,
        )

    # ── Data stamp ────────────────────────────────────────────────────────────
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
