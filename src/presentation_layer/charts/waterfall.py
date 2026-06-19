"""
Per-match prediction waterfall chart.

Starts at the uniform base rate (1/3) and terminates at the calibrated
home-win probability shown on the match card.

Reconciliation note (§0.5):
  XGBoost pred_contribs live in log-odds/margin space. After isotonic
  calibration they cannot directly sum to the calibrated output.
  We therefore SCALE each factor's signed contribution proportionally so
  that their net equals (p_home − base_rate), then label the chart
  "Directional drivers — scaled to calibrated output."
  This satisfies §0.5: the waterfall terminates at the displayed
  probability and the label is honest about the scaling.

If factors push in opposite directions and the intermediate cumulative
value briefly exceeds 1.0, a reference line at p=1.0 makes that
overshoot visible rather than hiding it — it is informative (one factor
alone would strongly favour home, another pulls back).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Uniform base rate for a 3-outcome match
_BASE_RATE: float = 1.0 / 3.0

# Design tokens
_BG          = "rgba(0,0,0,0)"
_SURFACE     = "#141417"
_BORDER      = "#2A2A31"
_TEXT        = "#F4F1EA"
_MUTED       = "#A7A39B"
_GOLD        = "#E8B84B"
_WIN_COLOR   = "#1FB479"   # positive / home-favoring
_LOSS_COLOR  = "#E4564A"   # negative / away-favoring
_BASE_COLOR  = "#3E7BFA"   # draw blue — used for the base-rate bar
_TOTAL_COLOR = _GOLD       # calibrated output bar


def prediction_waterfall(row: pd.Series) -> go.Figure:
    """
    Build a Plotly waterfall for one match prediction row.

    Parameters
    ----------
    row : pd.Series
        One row from predictions.parquet — needs p_home, p_draw, p_away,
        home_team, away_team, top_factors.

    Returns
    -------
    go.Figure
    """
    home   = str(row["home_team"])
    away   = str(row["away_team"])
    p_home = float(row["p_home"])
    p_draw = float(row["p_draw"])
    p_away = float(row["p_away"])

    factors = row.get("top_factors", [])
    if isinstance(factors, str):
        try:
            factors = json.loads(factors)
        except Exception:
            factors = []

    # ── Compute scaled steps ──────────────────────────────────────────────────
    base     = _BASE_RATE
    swing    = p_home - base        # signed; positive ⟹ model favours home

    # Assign signed raw impacts (direction "+" → pushes toward home win)
    signed = [
        float(f["impact"]) if f.get("direction", "+") == "+" else -float(f["impact"])
        for f in factors
    ]
    total_signed = sum(signed)

    if abs(total_signed) > 1e-9:
        scale  = swing / total_signed
        steps  = [s * scale for s in signed]
    else:
        # Degenerate: all factors cancel → spread swing evenly
        n = len(factors) or 1
        steps = [swing / n] * len(factors)

    # Sort: largest absolute step first so the biggest driver leads
    order = sorted(range(len(factors)), key=lambda i: abs(steps[i]), reverse=True)
    factors = [factors[i] for i in order]
    steps   = [steps[i]   for i in order]

    # ── Build waterfall traces ────────────────────────────────────────────────
    labels  = ["Base rate"] + [f["label"] for f in factors] + [f"{home} win\n(calibrated)"]
    y_vals  = [base]        + steps                          + [0.0]
    measure = ["absolute"]  + ["relative"] * len(factors)   + ["total"]

    # Per-bar colors
    colors = [_BASE_COLOR]
    for s in steps:
        colors.append(_WIN_COLOR if s >= 0 else _LOSS_COLOR)
    colors.append(_TOTAL_COLOR)

    # ── Compute running totals for y-axis range ───────────────────────────────
    running = [base]
    acc = base
    for s in steps:
        acc += s
        running.append(acc)
    running.append(acc)   # total bar at p_home

    y_min = min(0.0, min(running))
    y_max = max(1.0, max(running))
    pad   = 0.08 * (y_max - y_min)

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = go.Figure(go.Waterfall(
        name          = "Home win probability",
        orientation   = "v",
        measure       = measure,
        x             = labels,
        y             = y_vals,
        base          = 0,
        connector     = dict(line=dict(color=_BORDER, width=1, dash="dot")),
        decreasing    = dict(marker_color=_LOSS_COLOR, marker_line_width=0),
        increasing    = dict(marker_color=_WIN_COLOR,  marker_line_width=0),
        totals        = dict(marker_color=_TOTAL_COLOR, marker_line_width=0),
        text          = [f"{v:+.1%}" if i != 0 and i != len(labels) - 1 else ""
                         for i, v in enumerate(y_vals)],
        textposition  = "outside",
        textfont      = dict(family="'JetBrains Mono',monospace", size=10, color=_MUTED),
        hovertemplate = "%{x}<br><b>%{y:.1%}</b><extra></extra>",
        cliponaxis    = False,
    ))

    # Reference line at p=1.0 (when intermediate steps exceed it)
    shapes = [dict(
        type="line", xref="paper", yref="y",
        x0=0, x1=1, y0=1.0, y1=1.0,
        line=dict(color="#555566", width=1, dash="dot"),
        layer="below",
    )]

    # Callout annotation on the calibrated bar
    fig.add_annotation(
        x    = labels[-1],
        y    = p_home,
        text = f"<b>{p_home:.1%}</b>",
        showarrow = False,
        yanchor   = "bottom",
        yshift    = 8,
        font      = dict(family="'JetBrains Mono',monospace", size=13, color=_GOLD),
    )

    fig.update_layout(
        title = dict(
            text      = (
                f"<b>{home}</b> vs {away}"
                "<br><sup style='font-size:10px'>"
                "Directional drivers — scaled to calibrated output · not raw additive</sup>"
            ),
            font      = dict(family="'Archivo',sans-serif", size=14, color=_TEXT),
            x         = 0.01,
        ),
        paper_bgcolor = _BG,
        plot_bgcolor  = _BG,
        font          = dict(family="'Inter',sans-serif", color=_TEXT),
        xaxis         = dict(
            showgrid     = False,
            tickfont     = dict(family="'Inter',sans-serif", size=11, color=_MUTED),
            linecolor    = _BORDER,
        ),
        yaxis         = dict(
            title        = "P(Home win)",
            range        = [max(-0.05, y_min - pad), y_max + pad],
            gridcolor    = _BORDER,
            gridwidth    = 1,
            tickformat   = ".0%",
            tickfont     = dict(family="'JetBrains Mono',monospace", size=10, color=_MUTED),
            zerolinecolor= _BORDER,
            zerolinewidth= 1,
        ),
        showlegend    = False,
        height        = 340,
        margin        = dict(l=10, r=10, t=70, b=10),
        shapes        = shapes,
    )

    return fig


def all_three_waterfall(row: pd.Series) -> go.Figure:
    """
    Variant: show three waterfalls (Home/Draw/Away) as a 1×3 subplot.
    Used on the match detail page for a fuller picture.
    Each sub-waterfall is scaled independently.
    """
    from plotly.subplots import make_subplots

    home   = str(row["home_team"])
    away   = str(row["away_team"])
    probs  = [float(row["p_home"]), float(row["p_draw"]), float(row["p_away"])]
    labels_out = [f"{home} win", "Draw", f"{away} win"]
    colors_out = [_WIN_COLOR, _BASE_COLOR, _LOSS_COLOR]

    factors = row.get("top_factors", [])
    if isinstance(factors, str):
        try:
            factors = json.loads(factors)
        except Exception:
            factors = []

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=labels_out,
        horizontal_spacing=0.10,
    )

    for col_i, (p_target, label_out, bar_color) in enumerate(
        zip(probs, labels_out, colors_out), start=1
    ):
        swing = p_target - _BASE_RATE

        # For draw/away, reverse direction sign
        if col_i == 1:  # home
            signed = [
                float(f["impact"]) if f.get("direction", "+") == "+" else -float(f["impact"])
                for f in factors
            ]
        elif col_i == 3:  # away — flip signs
            signed = [
                -float(f["impact"]) if f.get("direction", "+") == "+" else float(f["impact"])
                for f in factors
            ]
        else:  # draw — magnitude only, direction inferred from whether factor reduces spread
            signed = [
                float(f["impact"]) * np.sign(swing) for f in factors
            ]

        total_signed = sum(signed)
        if abs(total_signed) > 1e-9:
            steps = [s * swing / total_signed for s in signed]
        else:
            n = max(len(factors), 1)
            steps = [swing / n] * len(factors)

        order   = sorted(range(len(factors)), key=lambda i: abs(steps[i]), reverse=True)
        f_ord   = [factors[i] for i in order]
        s_ord   = [steps[i]   for i in order]

        xlabels = ["Base\nrate"] + [f["label"] for f in f_ord] + [label_out]
        y_vals  = [_BASE_RATE]   + s_ord                       + [0.0]
        measure = ["absolute"]   + ["relative"] * len(f_ord)   + ["total"]
        step_colors = [_BASE_COLOR] + [
            _WIN_COLOR if s >= 0 else _LOSS_COLOR for s in s_ord
        ] + [bar_color]

        fig.add_trace(
            go.Waterfall(
                measure       = measure,
                x             = xlabels,
                y             = y_vals,
                base          = 0,
                connector     = dict(line=dict(color=_BORDER, width=1, dash="dot")),
                decreasing    = dict(marker_color=_LOSS_COLOR, marker_line_width=0),
                increasing    = dict(marker_color=_WIN_COLOR,  marker_line_width=0),
                totals        = dict(marker_color=bar_color,   marker_line_width=0),
                textposition  = "outside",
                textfont      = dict(family="'JetBrains Mono',monospace",
                                     size=9, color=_MUTED),
                hovertemplate = "%{x}<br><b>%{y:.1%}</b><extra></extra>",
                showlegend    = False,
                cliponaxis    = False,
            ),
            row=1, col=col_i,
        )
        fig.add_annotation(
            xref=f"x{col_i}", yref=f"y{col_i}",
            x=xlabels[-1], y=p_target,
            text=f"<b>{p_target:.1%}</b>",
            showarrow=False, yanchor="bottom", yshift=6,
            font=dict(family="'JetBrains Mono',monospace", size=12, color=_GOLD),
        )

    fig.update_layout(
        paper_bgcolor = _BG,
        plot_bgcolor  = _BG,
        font          = dict(family="'Inter',sans-serif", color=_TEXT),
        height        = 340,
        margin        = dict(l=10, r=10, t=60, b=10),
        showlegend    = False,
        title         = dict(
            text  = f"<b>{home}</b> vs <b>{away}</b> — all outcomes",
            font  = dict(family="'Archivo',sans-serif", size=13, color=_TEXT),
            x     = 0.01,
        ),
    )
    for i in range(1, 4):
        fig.update_yaxes(
            tickformat=".0%", gridcolor=_BORDER, gridwidth=1,
            tickfont=dict(family="'JetBrains Mono',monospace", size=9, color=_MUTED),
            range=[-0.05, 1.15], row=1, col=i,
        )
        fig.update_xaxes(
            showgrid=False, tickfont=dict(size=9, color=_MUTED),
            linecolor=_BORDER, row=1, col=i,
        )

    return fig
