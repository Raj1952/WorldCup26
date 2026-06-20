"""
Scatterternary: all upcoming group-stage matches in Win/Draw/Loss space.

Each point is one match. Clicking a point updates st.session_state so the
page below can filter the match list to that selection.

Design (§0.5 §2):
  - Three corners: Home Win (a), Draw (b), Away Win (c)
  - Color: favored outcome triad (win=#4CA882, draw=#6B8ABF, loss=#C9645C)
  - Size: scaled by model confidence (max(p_home, p_draw, p_away))
  - Hover: shows teams, group, probabilities
  - Click: on_select='rerun' → selection stored in session_state['ternary_selected']
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Design tokens
_BG     = "rgba(0,0,0,0)"
_BORDER = "#2A2A31"
_TEXT   = "#F4F1EA"
_MUTED  = "#A7A39B"
_GOLD   = "#E8B84B"
_WIN    = "#4CA882"
_DRAW   = "#6B8ABF"
_LOSS   = "#C9645C"


def _outcome_color(row: pd.Series) -> str:
    best = max(row["p_home"], row["p_draw"], row["p_away"])
    if best == row["p_home"]:
        return _WIN
    if best == row["p_draw"]:
        return _DRAW
    return _LOSS


def _label(row: pd.Series) -> str:
    home = str(row["home_team"])[:3].upper()
    away = str(row["away_team"])[:3].upper()
    return f"{home}–{away}"


def _hover(row: pd.Series) -> str:
    home = row["home_team"]
    away = row["away_team"]
    group = row.get("group_label", "WC")
    date  = str(row["date"])
    ph    = float(row["p_home"])
    pd_   = float(row["p_draw"])
    pa    = float(row["p_away"])
    best  = max(ph, pd_, pa)
    if best == ph:
        verdict = f"<b style='color:{_WIN}'>Home favoured</b>"
    elif best == pd_:
        verdict = f"<b style='color:{_DRAW}'>Draw likely</b>"
    else:
        verdict = f"<b style='color:{_LOSS}'>Away favoured</b>"
    return (
        f"<b>{home} vs {away}</b><br>"
        f"Group {group} · {date}<br>"
        f"Home {ph:.0%} | Draw {pd_:.0%} | Away {pa:.0%}<br>"
        f"{verdict}"
    )


def ternary_scatter(
    df: pd.DataFrame,
    selected_idx: int | None = None,
) -> go.Figure:
    """
    Build the Scatterternary figure.

    Parameters
    ----------
    df            Group-stage upcoming matches (known teams only).
    selected_idx  Row position of the currently selected match (if any).
                  That point is highlighted with a gold ring.

    Returns
    -------
    go.Figure
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=_BG,
            annotations=[dict(text="No data", x=0.5, y=0.5,
                              font=dict(color=_MUTED), showarrow=False)],
        )
        return fig

    colors     = [_outcome_color(r) for _, r in df.iterrows()]
    conf       = df[["p_home", "p_draw", "p_away"]].max(axis=1)
    sizes      = (10 + 18 * (conf - 0.33) / 0.67).clip(lower=10, upper=28).tolist()
    labels     = [_label(r)  for _, r in df.iterrows()]
    hovertexts = [_hover(r)  for _, r in df.iterrows()]

    marker_line_colors = ["#111114"] * len(df)
    marker_line_widths = [1.0] * len(df)
    if selected_idx is not None and 0 <= selected_idx < len(df):
        marker_line_colors[selected_idx] = _GOLD
        marker_line_widths[selected_idx] = 3.0

    fig = go.Figure(go.Scatterternary(
        a           = df["p_home"].tolist(),   # Home win vertex
        b           = df["p_draw"].tolist(),   # Draw vertex
        c           = df["p_away"].tolist(),   # Away win vertex
        mode        = "markers+text",
        text        = labels,
        textposition= "top center",
        textfont    = dict(
            family  = "'JetBrains Mono',monospace",
            size    = 9,
            color   = _MUTED,
        ),
        marker = dict(
            size        = sizes,
            color       = colors,
            opacity     = 0.88,
            line        = dict(
                color   = marker_line_colors,
                width   = marker_line_widths,
            ),
        ),
        hovertext     = hovertexts,
        hoverinfo     = "text",
        hoverlabel    = dict(
            bgcolor     = "#1C1C21",
            bordercolor = _BORDER,
            font        = dict(family="'Inter',sans-serif", size=12, color=_TEXT),
        ),
        customdata    = df.index.tolist(),
    ))

    # Corner labels and axis styling
    axis_style = dict(
        showgrid  = True,
        gridcolor = _BORDER,
        gridwidth = 1,
        tickfont  = dict(
            family  = "'JetBrains Mono',monospace",
            size    = 10,
            color   = _MUTED,
        ),
        tickformat = ".0%",
        linecolor  = _BORDER,
        linewidth  = 1,
    )

    fig.update_layout(
        template      = "tempo",
        ternary = dict(
            bgcolor = "rgba(20,20,23,0.6)",
            aaxis   = {**axis_style, "title": dict(
                text  = "Home Win",
                font  = dict(family="'Archivo',sans-serif", size=13,
                             color=_WIN, weight="bold"),
            )},
            baxis   = {**axis_style, "title": dict(
                text  = "Draw",
                font  = dict(family="'Archivo',sans-serif", size=13,
                             color=_DRAW, weight="bold"),
            )},
            caxis   = {**axis_style, "title": dict(
                text  = "Away Win",
                font  = dict(family="'Archivo',sans-serif", size=13,
                             color=_LOSS, weight="bold"),
            )},
        ),
        height        = 460,
        margin        = dict(l=60, r=60, t=60, b=20),
        title         = dict(
            text = (
                "Match Space — upcoming group-stage matches<br>"
                "<sup style='font-size:10px;color:#A7A39B'>"
                "Click a point to filter · "
                "<span style='color:#4CA882'>●</span> Home favoured  "
                "<span style='color:#6B8ABF'>●</span> Draw likely  "
                "<span style='color:#C9645C'>●</span> Away favoured"
                "</sup>"
            ),
            font = dict(family="'Archivo',sans-serif", size=14, color=_TEXT),
            x    = 0.01,
        ),
        dragmode      = "select",
    )

    return fig
