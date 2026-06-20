"""Model Report page — model performance, calibration, and prediction log."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

from src.presentation_layer.theme import DARK, APP_NAME
from src.intelligence_layer.registry import list_registry

DB_PATH = "data/tempo.db"


def _load_metrics() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM model_metrics ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def _load_recent_results() -> pd.DataFrame:
    """Matches we predicted AND now have a real result for."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # WC2026 played matches joined with predictions parquet manually
        df = pd.read_sql(
            "SELECT date,home_team,away_team,home_score,away_score,outcome "
            "FROM matches WHERE source IN ('openfootball','football-data.org','manual') "
            "AND tournament LIKE '%2026%' "
            "ORDER BY date DESC LIMIT 50",
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def _dark_layout(title: str = "") -> dict:
    return dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="'Inter', sans-serif",
        font_color="#F4F1EA",
        title_text=title,
        title_font_family="'Archivo', sans-serif",
        title_font_size=15,
        margin=dict(l=10, r=10, t=40, b=10),
    )


_REPORTS = Path("artifacts/reports")


def _load_holdout_summary() -> dict:
    p = _REPORTS / "holdout_summary.parquet"
    if not p.exists():
        return {}
    try:
        return pd.read_parquet(p).iloc[0].to_dict()
    except Exception:
        return {}


def _load_holdout_calibration() -> tuple[pd.DataFrame, pd.DataFrame]:
    cal_p = _REPORTS / "holdout_calibration.parquet"
    conf_p = _REPORTS / "holdout_confidence.parquet"
    cal = pd.read_parquet(cal_p) if cal_p.exists() else pd.DataFrame()
    conf = pd.read_parquet(conf_p) if conf_p.exists() else pd.DataFrame()
    return cal, conf


def _reliability_diagram(cal_df: pd.DataFrame, conf_df: pd.DataFrame) -> go.Figure:
    """
    Reliability diagram (predicted vs observed per class) with confidence histogram beneath.
    Replaces the accuracy gauge per §0.5.
    """
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.68, 0.32],
        vertical_spacing=0.08,
        subplot_titles=["Reliability Diagram", "Model Confidence Distribution"],
    )

    outcome_meta = [
        ("home", "Home Win", "#1FB479"),
        ("draw", "Draw",     "#3E7BFA"),
        ("away", "Away Win", "#E4564A"),
    ]

    for outcome, label, color in outcome_meta:
        sub = cal_df[cal_df["outcome"] == outcome].dropna(subset=["mean_pred", "obs_freq"])
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["mean_pred"],
            y=sub["obs_freq"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2),
            marker=dict(
                size=sub["bin_count"].clip(upper=200) / 15 + 5,
                color=color,
                opacity=0.85,
                line=dict(color="#0B0B0D", width=1),
            ),
            customdata=sub[["bin_count"]].values,
            hovertemplate=(
                f"<b>{label}</b><br>"
                "Predicted: %{x:.0%}<br>"
                "Observed: %{y:.0%}<br>"
                "N=%{customdata[0]}<extra></extra>"
            ),
        ), row=1, col=1)

    # Perfect calibration diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        name="Perfect calibration",
        line=dict(color="#E8B84B", width=1.5, dash="dot"),
        hoverinfo="skip",
    ), row=1, col=1)

    # Confidence histogram
    if not conf_df.empty:
        fig.add_trace(go.Histogram(
            x=conf_df["confidence"],
            nbinsx=20,
            name="Confidence",
            marker_color="#3E7BFA",
            marker_line=dict(color="#0B0B0D", width=0.5),
            opacity=0.75,
            hovertemplate="Confidence: %{x:.0%}<br>Matches: %{y}<extra></extra>",
        ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="'Inter', sans-serif",
        font_color="#F4F1EA",
        margin=dict(l=10, r=10, t=50, b=10),
        height=480,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#A7A39B", size=10),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
        showlegend=True,
    )
    axis_style = dict(gridcolor="#2A2A31", color="#A7A39B",
                      tickfont=dict(family="'JetBrains Mono',monospace", size=10))
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    fig.update_xaxes(range=[0, 1], tickformat=".0%", row=1, col=1)
    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=1, col=1)
    fig.update_xaxes(tickformat=".0%", title_text="Max predicted probability", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)

    # Annotation per subplot title
    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=12, color="#A7A39B", family="'Inter',sans-serif")

    return fig


def _metrics_timeline(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["created_at"], y=df["log_loss_test"],
        name="Log-Loss (lower = better)",
        line=dict(color="#3E7BFA", width=2),
        mode="lines+markers",
        marker=dict(size=6, color="#3E7BFA"),
    ))
    fig.add_trace(go.Scatter(
        x=df["created_at"], y=df["accuracy_test"],
        name="Accuracy",
        line=dict(color="#1FB479", width=2),
        mode="lines+markers",
        marker=dict(size=6, color="#1FB479"),
        yaxis="y2",
    ))
    fig.update_layout(
        **_dark_layout("Model Metrics Over Time"),
        yaxis=dict(title="Log-Loss", gridcolor="#2A2A31", color="#A7A39B"),
        yaxis2=dict(title="Accuracy", overlaying="y", side="right", gridcolor="#2A2A31", color="#A7A39B"),
        xaxis=dict(gridcolor="#2A2A31", color="#A7A39B"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#A7A39B")),
        height=280,
    )
    return fig


def _outcome_distribution(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    counts = df["outcome"].value_counts().reindex(["home", "draw", "away"], fill_value=0)
    fig = go.Figure(go.Bar(
        x=["Home Win", "Draw", "Away Win"],
        y=counts.values,
        marker_color=["#1FB479", "#3E7BFA", "#E4564A"],
        text=counts.values,
        textposition="outside",
        textfont=dict(color="#F4F1EA", family="'JetBrains Mono', monospace"),
    ))
    fig.update_layout(
        **_dark_layout("WC2026 Results So Far"),
        xaxis=dict(color="#A7A39B"),
        yaxis=dict(gridcolor="#2A2A31", color="#A7A39B"),
        height=240,
    )
    return fig


def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Model Report</h1>"
        '<p class="subtitle">Model performance, calibration, and prediction history</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    metrics_df = _load_metrics()
    results_df = _load_recent_results()
    registry = list_registry()

    if not registry:
        st.markdown(
            '<div class="no-data"><h3>No model trained yet</h3>'
            "<p>Run <code>python pipelines/refresh.py</code> to train the model.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Latest model metrics
    latest = registry[-1]
    ll = latest.get("log_loss_test", 0)
    acc = latest.get("accuracy_test", 0)
    brier = latest.get("brier_test", 0)
    n_train = latest.get("n_train", 0)
    n_test = latest.get("n_test", 0)
    model_type = latest.get("model_type", "")
    created_at = (latest.get("created_at") or "")[:19]

    # Load RPS from holdout artifact (written by scripts/compute_holdout_metrics.py)
    holdout = _load_holdout_summary()
    rps = holdout.get("rps_test")

    # Top metric cards — RPS is the headline per §0.5
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rps_label = f"{rps:.4f}" if rps is not None else "run script"
        st.metric("RPS (Test)", rps_label,
                  help="Ranked Probability Score — primary metric. Lower is better. Uniform baseline ~0.333.")
    with col2:
        st.metric("Log-Loss", f"{ll:.4f}")
    with col3:
        st.metric("Brier Score", f"{brier:.4f}")
    with col4:
        st.metric("Accuracy", f"{acc:.1%}",
                  help="Secondary metric only — not the headline per post-council review.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Reliability diagram — the credibility centrepiece (replaces accuracy gauge per §0.5)
    cal_df, conf_df = _load_holdout_calibration()
    if not cal_df.empty:
        st.markdown('<div class="sec-heading">Reliability Diagram · Confidence Distribution</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:0.78rem;color:var(--text-muted);margin:-0.5rem 0 0.75rem;">'
            'Points above the gold diagonal = model under-predicts that outcome; '
            'below = over-predicts. Marker size scales with sample count per bin.</p>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_reliability_diagram(cal_df, conf_df), use_container_width=True)
    else:
        st.info("Run `python scripts/compute_holdout_metrics.py` to generate the reliability diagram.")

    # Baselines comparison — text only, no gauge
    rps_str = f"{rps:.4f}" if rps is not None else "run script"
    beats = rps is not None and rps < 0.333
    beats_html = '&nbsp; <span style="color:var(--win);">beats uniform</span>' if beats else ""
    st.markdown(
        f'<div style="font-size:0.78rem;color:var(--text-muted);padding:0.25rem 0 1rem;">'
        f'<strong style="color:var(--text);">RPS baselines</strong> &nbsp;|&nbsp; '
        f'Uniform (1/3 each): ~0.333 &nbsp;|&nbsp; '
        f'Always-home: ~0.300 &nbsp;|&nbsp; '
        f'<span style="color:var(--gold);font-family:var(--ff-mono);">Model: {rps_str}</span>'
        f'{beats_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # WC2026 results distribution (half-width — leave room for future metrics)
    col_results, _ = st.columns([1, 1])
    with col_results:
        st.markdown('<div class="sec-heading">WC2026 Results So Far</div>', unsafe_allow_html=True)
        if not results_df.empty:
            st.plotly_chart(_outcome_distribution(results_df), use_container_width=True)
        else:
            st.markdown(
                '<p style="color:var(--text-muted);font-size:0.82rem;">'
                "No WC2026 results ingested yet.</p>",
                unsafe_allow_html=True,
            )

    # Metrics timeline
    if len(metrics_df) > 1:
        st.markdown('<div class="sec-heading">Training History</div>', unsafe_allow_html=True)
        st.plotly_chart(_metrics_timeline(metrics_df), use_container_width=True)

    # Model registry table
    st.markdown('<div class="sec-heading">Model Registry</div>', unsafe_allow_html=True)
    if registry:
        reg_df = pd.DataFrame([{
            "Version": r.get("version", ""),
            "Type": r.get("model_type", ""),
            "Log-Loss": f"{r.get('log_loss_test', 0):.4f}",
            "Accuracy": f"{r.get('accuracy_test', 0):.1%}",
            "Brier": f"{r.get('brier_test', 0):.4f}",
            "Train N": f"{r.get('n_train', 0):,}",
            "Created": r.get("created_at", "")[:19],
        } for r in registry])
        st.dataframe(
            reg_df,
            use_container_width=True,
            hide_index=True,
        )

    # Recent WC2026 results table
    if not results_df.empty:
        st.markdown('<div class="sec-heading">Recent WC2026 Results</div>', unsafe_allow_html=True)
        results_df["result"] = (
            results_df["home_score"].astype(str)
            + " – "
            + results_df["away_score"].astype(str)
        )
        st.dataframe(
            results_df[["date", "home_team", "result", "away_team", "outcome"]].rename(columns={
                "date": "Date", "home_team": "Home", "result": "Score",
                "away_team": "Away", "outcome": "Outcome",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Data stamp
    data_ts = created_at if registry else "—"
    st.markdown(
        f'<p class="data-stamp" style="margin-top:1rem;">Data as of {data_ts} · '
        f'Updates daily via batch · <code>python pipelines/refresh.py</code></p>',
        unsafe_allow_html=True,
    )
