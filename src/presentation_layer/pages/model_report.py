"""Model Report page — RPS headline strip, reliability diagram, RPS-vs-baseline timeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.presentation_layer.theme import DARK, APP_NAME
from src.intelligence_layer.registry import list_registry

DB_PATH   = "data/tempo.db"
_REPORTS  = Path("artifacts/reports")

# ── Design tokens (kept local — no cross-layer import) ────────────────────────
_WIN   = "#4CA882"
_DRAW  = "#6B8ABF"
_LOSS  = "#C9645C"
_GOLD  = "#E8B84B"
_TEXT  = "#F4F1EA"
_MUTED = "#A7A39B"
_BG    = "rgba(0,0,0,0)"
_SURF  = "#141417"
_BORDER= "#2A2A31"
_MONO  = "JetBrains Mono, monospace"
_BODY  = "Inter, sans-serif"
_DISP  = "Archivo, sans-serif"


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_holdout_summary() -> dict:
    p = _REPORTS / "holdout_summary.parquet"
    if not p.exists():
        return {}
    try:
        return pd.read_parquet(p).iloc[0].to_dict()
    except Exception:
        return {}


def _load_holdout_calibration() -> tuple[pd.DataFrame, pd.DataFrame]:
    cal_p  = _REPORTS / "holdout_calibration.parquet"
    conf_p = _REPORTS / "holdout_confidence.parquet"
    cal  = pd.read_parquet(cal_p)  if cal_p.exists()  else pd.DataFrame()
    conf = pd.read_parquet(conf_p) if conf_p.exists() else pd.DataFrame()
    return cal, conf


def _load_metrics_history() -> pd.DataFrame:
    """All model versions from the registry, with RPS from holdout summary where available."""
    reg = list_registry()
    if not reg:
        return pd.DataFrame()
    rows = []
    for r in reg:
        rows.append({
            "version":    r.get("version", ""),
            "created_at": r.get("created_at", ""),
            "log_loss":   r.get("log_loss_test"),
            "accuracy":   r.get("accuracy_test"),
            "brier":      r.get("brier_test"),
            "n_test":     r.get("n_test"),
        })
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df = df.sort_values("created_at").reset_index(drop=True)
    return df


def _compute_baselines(cal_df: pd.DataFrame) -> dict[str, float]:
    """
    Derive uniform and always-home RPS baselines from the holdout class distribution.

    RPS is computed analytically from observed class frequencies:
      - Uniform (1/3, 1/3, 1/3): closed-form per class
      - Always-home (1, 0, 0): closed-form per class
    """
    if cal_df.empty:
        return {"uniform": 0.240, "always_home": 0.420}

    freqs: dict[str, float] = {}
    for outcome in ["home", "draw", "away"]:
        sub = cal_df[cal_df["outcome"] == outcome].dropna(subset=["obs_freq", "bin_count"])
        if not sub.empty:
            total_n = sub["bin_count"].sum()
            total_k = (sub["obs_freq"] * sub["bin_count"]).sum()
            freqs[outcome] = float(total_k / total_n) if total_n > 0 else 1 / 3

    f_h = freqs.get("home", 1 / 3)
    f_d = freqs.get("draw", 1 / 3)
    f_a = freqs.get("away", 1 / 3)

    # Uniform: cum_pred=[1/3, 2/3]
    #   Home  (y=0): ((1/3-1)²+(2/3-1)²)/2 = 5/18
    #   Draw  (y=1): ((1/3-0)²+(2/3-1)²)/2 = 1/9
    #   Away  (y=2): ((1/3-0)²+(2/3-0)²)/2 = 5/18
    rps_uniform = f_h * (5 / 18) + f_d * (1 / 9) + f_a * (5 / 18)

    # Always-home: cum_pred=[1, 1]
    #   Home  (y=0): 0
    #   Draw  (y=1): ((1-0)²+(1-1)²)/2 = 0.5
    #   Away  (y=2): ((1-0)²+(1-0)²)/2 = 1.0
    rps_always_home = f_d * 0.5 + f_a * 1.0

    return {"uniform": rps_uniform, "always_home": rps_always_home}


# ── Metric strip ──────────────────────────────────────────────────────────────

def _metric_strip_html(holdout: dict, baselines: dict) -> str:
    rps       = holdout.get("rps_test")
    ll        = holdout.get("log_loss_test")
    brier     = holdout.get("brier_test")
    acc       = holdout.get("accuracy_test")
    n_test    = holdout.get("n_test")
    ver       = str(holdout.get("model_version", "—"))

    rps_str   = f"{rps:.4f}"  if rps    is not None else "—"
    ll_str    = f"{ll:.4f}"   if ll     is not None else "—"
    brier_str = f"{brier:.4f}" if brier  is not None else "—"
    acc_str   = f"{acc:.1%}"  if acc    is not None else "—"
    n_str     = f"{int(n_test):,}" if n_test is not None else "—"
    ver_short = ver[:28] + "…" if len(ver) > 28 else ver

    b_uni  = baselines.get("uniform",     0.240)
    b_home = baselines.get("always_home", 0.420)

    beats_uni  = rps is not None and rps < b_uni
    beats_home = rps is not None and rps < b_home

    def _badge(label: str, ok: bool) -> str:
        color = _WIN if ok else _LOSS
        symbol = "✓" if ok else "✗"
        return (
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'background:{"rgba(76,168,130,0.12)" if ok else "rgba(201,100,92,0.12)"};'
            f'border:1px solid {"rgba(76,168,130,0.3)" if ok else "rgba(201,100,92,0.3)"};'
            f'border-radius:5px;padding:1px 8px;font-family:{_MONO};font-size:0.65rem;'
            f'color:{color};">{symbol} {label}</span>'
        )

    return f"""
<div style="
  background:{_SURF};
  border:1px solid {_BORDER};
  border-radius:12px;
  padding:1.1rem 1.4rem 1rem;
  margin-bottom:1.5rem;
  position:relative;
  overflow:hidden;
">
  <!-- Tri-color accent rail -->
  <div style="position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,{_WIN} 0% 33.3%,{_DRAW} 33.3% 66.6%,{_LOSS} 66.6% 100%);
  "></div>

  <!-- Primary: RPS -->
  <div style="display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;margin-bottom:0.5rem;">
    <div>
      <div style="font-family:{_BODY};font-size:0.65rem;font-weight:600;
        text-transform:uppercase;letter-spacing:0.1em;color:{_MUTED};margin-bottom:3px;">
        Ranked Probability Score &nbsp;·&nbsp; primary &nbsp;·&nbsp; lower = better
      </div>
      <div style="font-family:{_MONO};font-size:2.6rem;font-weight:700;
        color:{_GOLD};line-height:1;font-variant-numeric:tabular-nums;">
        {rps_str}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:5px;padding-top:4px;">
      {_badge(f"beats uniform {b_uni:.3f}", beats_uni)}
      {_badge(f"beats always-home {b_home:.3f}", beats_home)}
    </div>
  </div>

  <!-- Divider -->
  <div style="border-top:1px solid {_BORDER};margin:0.7rem 0;"></div>

  <!-- Secondary metrics -->
  <div style="display:flex;flex-wrap:wrap;gap:0.35rem 1.5rem;align-items:baseline;">
    <span style="font-family:{_MONO};font-size:0.78rem;color:{_MUTED};">
      Log-Loss <span style="color:{_TEXT};font-weight:600;">{ll_str}</span>
    </span>
    <span style="color:{_BORDER};">·</span>
    <span style="font-family:{_MONO};font-size:0.78rem;color:{_MUTED};">
      Brier <span style="color:{_TEXT};font-weight:600;">{brier_str}</span>
    </span>
    <span style="color:{_BORDER};">·</span>
    <span style="font-family:{_MONO};font-size:0.78rem;color:{_MUTED};">
      Accuracy <span style="color:{_TEXT};font-weight:600;">{acc_str}</span>
      <span style="font-size:0.62rem;color:{_MUTED};opacity:0.7;">(secondary — not headline)</span>
    </span>
    <span style="color:{_BORDER};">·</span>
    <span style="font-family:{_MONO};font-size:0.72rem;color:{_MUTED};">
      {n_str} test matches
    </span>
    <span style="color:{_BORDER};">·</span>
    <span style="font-family:{_MONO};font-size:0.65rem;color:{_MUTED};opacity:0.65;">
      {ver_short}
    </span>
  </div>
</div>"""


# ── Charts ────────────────────────────────────────────────────────────────────

def _reliability_diagram(cal_df: pd.DataFrame, conf_df: pd.DataFrame) -> go.Figure:
    """Reliability diagram (rows 1) + confidence histogram (row 2). template=tempo."""
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.10,
        subplot_titles=["Reliability Diagram", "Model Confidence Distribution"],
    )

    outcome_meta = [
        ("home", "Home Win", _WIN),
        ("draw", "Draw",     _DRAW),
        ("away", "Away Win", _LOSS),
    ]

    for outcome, label, color in outcome_meta:
        sub = cal_df[cal_df["outcome"] == outcome].dropna(subset=["mean_pred", "obs_freq"])
        if sub.empty:
            continue
        sizes = (sub["bin_count"].clip(upper=200) / 15 + 5).tolist()
        fig.add_trace(go.Scatter(
            x=sub["mean_pred"],
            y=sub["obs_freq"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2),
            marker=dict(
                size=sizes,
                color=color,
                opacity=0.85,
                line=dict(color="#111114", width=1),
            ),
            customdata=sub[["bin_count"]].values,
            hovertemplate=(
                f"<b>{label}</b><br>"
                "Predicted: %{x:.0%}<br>"
                "Observed: %{y:.0%}<br>"
                "N = %{customdata[0]}<extra></extra>"
            ),
        ), row=1, col=1)

    # Perfect calibration diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        name="Perfect calibration",
        line=dict(color=_GOLD, width=1.5, dash="dot"),
        hoverinfo="skip",
    ), row=1, col=1)

    # Confidence histogram
    if not conf_df.empty:
        fig.add_trace(go.Histogram(
            x=conf_df["confidence"],
            nbinsx=25,
            name="Confidence",
            marker_color=_DRAW,
            marker_line=dict(color="#111114", width=0.5),
            opacity=0.78,
            hovertemplate="Confidence: %{x:.0%}<br>Matches: %{y}<extra></extra>",
            showlegend=False,
        ), row=2, col=1)

    _ax = dict(gridcolor=_BORDER, color=_MUTED,
               tickfont=dict(family=_MONO, size=10, color=_MUTED),
               linecolor=_BORDER)

    fig.update_layout(
        template="tempo",
        height=500,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_MUTED, size=11),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right",  x=1,
        ),
    )
    fig.update_xaxes(**_ax)
    fig.update_yaxes(**_ax)
    fig.update_xaxes(range=[0, 1], tickformat=".0%", row=1, col=1)
    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=1, col=1)
    fig.update_xaxes(tickformat=".0%", title_text="Max predicted probability (model confidence)", row=2, col=1)
    fig.update_yaxes(title_text="Match count", row=2, col=1)
    for ann in fig["layout"]["annotations"]:
        ann["font"] = dict(size=12, color=_MUTED, family=_BODY)

    return fig


def _rps_timeline(hist_df: pd.DataFrame, holdout: dict, baselines: dict) -> go.Figure:
    """RPS per model version vs uniform and always-home baselines. template=tempo."""
    b_uni  = baselines.get("uniform",     0.240)
    b_home = baselines.get("always_home", 0.420)

    # Build model RPS series: use holdout_summary for the current version
    # (model_metrics table doesn't store RPS; registry entries don't either)
    rps_val  = holdout.get("rps_test")
    ver      = holdout.get("model_version", "")
    created  = holdout.get("created_at")

    points_x, points_y, points_label = [], [], []
    if rps_val is not None and created:
        try:
            ts = pd.to_datetime(created)
            points_x.append(ts)
            points_y.append(rps_val)
            ver_short = str(ver)[:20] + "…" if len(str(ver)) > 20 else str(ver)
            points_label.append(f"<b>{ver_short}</b><br>RPS: {rps_val:.4f}")
        except Exception:
            pass

    fig = go.Figure()

    # Model RPS line / markers
    if points_x:
        fig.add_trace(go.Scatter(
            x=points_x,
            y=points_y,
            mode="lines+markers",
            name="Model RPS",
            line=dict(color=_GOLD, width=2.5),
            marker=dict(
                size=12, color=_GOLD,
                line=dict(color="#111114", width=2),
                symbol="circle",
            ),
            text=points_label,
            hovertemplate="%{text}<extra></extra>",
        ))

    # X range: always span at least the tournament window so a single point
    # doesn't collapse to microsecond precision on the axis
    _tournament_start = pd.Timestamp("2026-06-11")
    _tournament_end   = pd.Timestamp("2026-07-20")
    if points_x:
        x0 = min(min(points_x) - pd.Timedelta(days=7), _tournament_start)
        x1 = max(max(points_x) + pd.Timedelta(days=7), _tournament_end)
    else:
        x0 = _tournament_start
        x1 = _tournament_end

    def _ref_line(y: float, label: str, color: str, dash: str = "dash") -> None:
        fig.add_shape(
            type="line", xref="paper", yref="y",
            x0=0, x1=1, y0=y, y1=y,
            line=dict(color=color, width=1.5, dash=dash),
        )
        fig.add_annotation(
            xref="paper", yref="y", x=1.01, y=y,
            text=f"<b>{label}</b><br>{y:.3f}",
            showarrow=False, xanchor="left",
            font=dict(family=_MONO, size=10, color=color),
        )

    _ref_line(b_uni,  "Uniform",      _MUTED,  "dot")
    _ref_line(b_home, "Always-home",  _BORDER, "dash")

    # Beat-zone shading (below uniform = model territory)
    if points_x:
        fig.add_hrect(
            y0=0, y1=b_uni,
            fillcolor="rgba(76,168,130,0.04)",
            line_width=0,
            annotation_text="model territory", annotation_position="top left",
            annotation_font=dict(size=9, color=_WIN, family=_MONO),
        )

    fig.update_layout(
        template="tempo",
        height=280,
        margin=dict(l=10, r=110, t=30, b=10),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=_MUTED, size=11),
            orientation="h", yanchor="top", y=1.12, xanchor="left", x=0,
        ),
        yaxis=dict(
            title="RPS (lower = better)",
            tickformat=".3f",
            gridcolor=_BORDER,
            color=_MUTED,
            tickfont=dict(family=_MONO, size=10, color=_MUTED),
            range=[0, max(b_home + 0.05, (max(points_y) if points_y else 0.5) + 0.05)],
        ),
        xaxis=dict(
            range=[x0, x1],
            tickformat="%b %d\n%Y",
            tickfont=dict(family=_MONO, size=10, color=_MUTED),
            color=_MUTED,
            gridcolor=_BORDER,
        ),
    )
    return fig


# ── Page renderer ─────────────────────────────────────────────────────────────

def render(theme=DARK) -> None:
    st.markdown(
        '<div class="page-header">'
        "<h1>Model Report</h1>"
        '<p class="subtitle">'
        "Calibration quality, prediction drivers, and honest performance against baselines"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    registry = list_registry()
    if not registry:
        st.markdown(
            '<div class="no-data">'
            "<h3>Model artifacts are being generated</h3>"
            "<p>They’ll appear after the next daily refresh — "
            "predictions update every morning.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    holdout  = _load_holdout_summary()
    cal_df, conf_df = _load_holdout_calibration()
    hist_df  = _load_metrics_history()
    baselines = _compute_baselines(cal_df)

    # ── 1. Lower-third metric strip ───────────────────────────────────────────
    if holdout:
        st.markdown(_metric_strip_html(holdout, baselines), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="no-data" style="padding:1.25rem;">'
            "<h3>Performance metrics are being generated</h3>"
            "<p>They'll appear after the next daily refresh.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── 2. Reliability diagram + confidence histogram ─────────────────────────
    st.markdown(
        '<div class="sec-heading">Reliability Diagram · Confidence Distribution</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:0.78rem;color:var(--text-muted);margin:-0.4rem 0 0.9rem;">'
        "Points above the gold diagonal → model under-predicts that outcome; "
        "below → over-predicts. Marker size scales with sample count per bin.</p>",
        unsafe_allow_html=True,
    )
    if not cal_df.empty:
        st.plotly_chart(
            _reliability_diagram(cal_df, conf_df),
            width="stretch",
        )
    else:
        st.markdown(
            '<div class="no-data" style="padding:2rem;">'
            "<h3>Calibration data is being generated</h3>"
            "<p>It'll appear after the next daily refresh.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── 3. RPS-vs-baseline timeline ───────────────────────────────────────────
    st.markdown(
        '<div class="sec-heading">RPS vs Baselines</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:0.78rem;color:var(--text-muted);margin:-0.4rem 0 0.9rem;">'
        "Gold = model · Dashed = theoretical baselines computed from holdout class distribution. "
        "Green zone = model territory (beats uniform).</p>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _rps_timeline(hist_df, holdout, baselines),
        width="stretch",
    )

    # ── 4. Model registry ─────────────────────────────────────────────────────
    st.markdown('<div class="sec-heading">Model Registry</div>', unsafe_allow_html=True)
    reg_rows = []
    for r in registry:
        rps_cell = f"{holdout['rps_test']:.4f}" if holdout.get("rps_test") else "—"
        reg_rows.append({
            "Version":   r.get("version", "")[:32],
            "Type":      r.get("model_type", ""),
            "RPS":       rps_cell,
            "Log-Loss":  f"{r.get('log_loss_test', 0):.4f}",
            "Brier":     f"{r.get('brier_test', 0):.4f}",
            "Accuracy":  f"{r.get('accuracy_test', 0):.1%}",
            "Train N":   f"{r.get('n_train', 0):,}",
            "Created":   str(r.get("created_at", ""))[:19],
        })
    st.dataframe(pd.DataFrame(reg_rows), width="stretch", hide_index=True)

    # ── 5. Data stamp ─────────────────────────────────────────────────────────
    created_at = str(holdout.get("created_at", registry[-1].get("created_at", "")))[:19]
    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.25rem;">'
        f"Data as of <code>{created_at}</code> · Updates daily via batch</p>",
        unsafe_allow_html=True,
    )
