"""Match Detail page — deep dive into a single prediction with SHAP factors."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.presentation_layer.theme import DARK
from src.data_layer.team_aliases import get_flag_code
from src.presentation_layer.flags import flag_img
from src.presentation_layer.charts.waterfall import prediction_waterfall


_PREDICTIONS_PATH = Path("predictions.parquet")


def _load_predictions() -> pd.DataFrame:
    if not _PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(_PREDICTIONS_PATH)
    df["top_factors"] = df["top_factors"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
    )
    return df


def _dark_layout() -> dict:
    return dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="'Inter', sans-serif",
        font_color="#F4F1EA",
        margin=dict(l=10, r=10, t=30, b=10),
    )


def _prob_donut(p_home: float, p_draw: float, p_away: float,
                home: str, away: str) -> go.Figure:
    labels = [f"{home} Win", "Draw", f"{away} Win"]
    values = [p_home, p_draw, p_away]
    colors = ["#1FB479", "#3E7BFA", "#E4564A"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0B0B0D", width=2)),
        textfont=dict(family="'JetBrains Mono', monospace", size=12, color="#F4F1EA"),
        hovertemplate="%{label}: <b>%{percent}</b><extra></extra>",
    ))
    fig.update_layout(
        **_dark_layout(),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#A7A39B", size=11),
            orientation="h",
            yanchor="bottom", y=-0.2,
            xanchor="center", x=0.5,
        ),
        height=300,
        annotations=[dict(
            text=f"<b>{max(p_home, p_draw, p_away):.0%}</b>",
            x=0.5, y=0.5,
            font=dict(size=22, color="#E8B84B", family="'JetBrains Mono', monospace"),
            showarrow=False,
        )],
    )
    return fig


def _factors_bar(factors: list[dict], home: str) -> go.Figure:
    if not factors:
        return go.Figure()
    labels = [f["label"] for f in factors]
    impacts = [f["impact"] * (1 if f["direction"] == "+" else -1) for f in factors]
    colors = ["#1FB479" if v >= 0 else "#E4564A" for v in impacts]

    fig = go.Figure(go.Bar(
        x=impacts,
        y=labels,
        orientation="h",
        marker_color=colors,
        marker_line=dict(width=0),
        text=[f"{abs(v):.3f}" for v in impacts],
        textposition="outside",
        textfont=dict(family="'JetBrains Mono', monospace", color="#A7A39B", size=10),
        hovertemplate="%{y}: <b>%{x:.4f}</b><extra></extra>",
    ))
    fig.update_layout(
        **_dark_layout(),
        xaxis=dict(
            title="Feature contribution",
            gridcolor="#2A2A31",
            color="#A7A39B",
            zeroline=True,
            zerolinecolor="#3A3A45",
            zerolinewidth=1.5,
            tickfont=dict(family="'JetBrains Mono',monospace", size=10),
        ),
        yaxis=dict(color="#A7A39B", autorange="reversed",
                   tickfont=dict(family="'Inter',sans-serif", size=11)),
        height=max(220, len(factors) * 52),
        title_text=f"Key factors",
        title_font=dict(size=12, color="#A7A39B", family="'Inter',sans-serif"),
    )
    return fig


def render(theme=DARK) -> None:
    st.markdown('<div class="accent-rail"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-header">'
        "<h1>Match Detail</h1>"
        '<p class="subtitle">Deep prediction analysis with explainability factors</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    df = _load_predictions()

    if df.empty:
        st.markdown(
            '<div class="no-data"><h3>No predictions available</h3>'
            "<p>Run <code>python pipelines/refresh.py</code> first.</p></div>",
            unsafe_allow_html=True,
        )
        return

    # Match selector
    match_options = {
        f"{row['home_team']} vs {row['away_team']} ({row['date']})": idx
        for idx, row in df.iterrows()
    }
    selected_label = st.selectbox("Select a match:", list(match_options.keys()))
    if not selected_label:
        return

    row = df.loc[match_options[selected_label]]
    home = row["home_team"]
    away = row["away_team"]
    p_h = float(row["p_home"])
    p_d = float(row["p_draw"])
    p_a = float(row["p_away"])
    hf = flag_img(get_flag_code(home), width=48, team_name=home)
    af = flag_img(get_flag_code(away), width=48, team_name=away)
    factors = row.get("top_factors", [])

    # Match header
    st.markdown(f"""
<div class="match-card" style="margin:1rem 0;">
  <div class="match-card-rail"></div>
  <div class="match-card-body">
    <div class="match-chip">WC26 · {row.get("group_label","WC")} · {row["date"]}</div>
    <div class="match-teams">
      <div class="team-block">
        <span class="team-flag">{hf}</span>
        <span class="team-name" style="font-size:1.3rem">{home}</span>
      </div>
      <span class="match-vs" style="font-size:1rem">VS</span>
      <div class="team-block away">
        <span class="team-flag">{af}</span>
        <span class="team-name" style="font-size:1.3rem">{away}</span>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Probability summary (text-only per §0.5 — no donut) ─────────────────
    col_probs, col_wf = st.columns([1, 2])
    with col_probs:
        st.markdown('<div class="sec-heading">Outcome Probabilities</div>', unsafe_allow_html=True)
        for label, prob, color in [
            (f"{home} win", p_h, "var(--win)"),
            ("Draw",        p_d, "var(--draw)"),
            (f"{away} win", p_a, "var(--loss)"),
        ]:
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:0.6rem 0.9rem;margin-bottom:6px;border-radius:8px;
            border:1px solid var(--border);background:var(--surface);">
  <span style="color:{color};font-weight:600;font-size:0.88rem;">{label}</span>
  <span style="font-family:var(--ff-mono);font-size:1.1rem;
               font-weight:700;color:{color};">{prob:.1%}</span>
</div>""", unsafe_allow_html=True)

    # ── Waterfall ─────────────────────────────────────────────────────────────
    with col_wf:
        st.markdown('<div class="sec-heading">Prediction waterfall — base rate → calibrated</div>',
                    unsafe_allow_html=True)
        if factors:
            fig_wf = prediction_waterfall(row)
            st.plotly_chart(fig_wf, use_container_width=True,
                            key=f"wf_{row.get('match_id', 'detail')}")
        else:
            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.82rem;">'
                "Factor data not available. Re-run <code>python pipelines/refresh.py</code>.</p>",
                unsafe_allow_html=True,
            )

    # Model info
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-heading">Prediction Metadata</div>', unsafe_allow_html=True)
    meta_cols = st.columns(3)
    with meta_cols[0]:
        st.metric("Model Version", row.get("model_version", "—")[:16])
    with meta_cols[1]:
        created = str(row.get("created_at", "—"))[:19]
        st.metric("Generated At", created)
    with meta_cols[2]:
        best_p = max(p_h, p_d, p_a)
        st.metric("Confidence", f"{best_p:.1%}")

    # Data stamp
    try:
        created = pd.to_datetime(row.get("created_at", "")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        created = str(row.get("created_at", "—"))[:19]
    st.markdown(
        f'<p class="data-stamp" style="margin-top:1rem;">Data as of {created} · '
        f'Updates daily via batch · <code>python pipelines/refresh.py</code></p>',
        unsafe_allow_html=True,
    )
