"""
Tempo shared Plotly template.

Call register_tempo_template() once at app startup (before any chart renders).
Every chart that passes template="tempo" gets consistent:
  - Transparent backgrounds
  - JetBrains Mono tick labels
  - Hairline #2A2A31 gridlines
  - Win/Draw/Loss semantic colorway (never default Plotly blue)
  - Slim modebar
  - Themed hover labels
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# Design tokens (kept local to avoid cross-layer imports; must stay in sync with theme.py)
_BG = "rgba(0,0,0,0)"
_SURFACE = "#141417"
_BORDER = "#2A2A31"
_TEXT = "#F4F1EA"
_MUTED = "#A7A39B"
_GOLD = "#E8B84B"
_WIN = "#1FB479"
_DRAW = "#3E7BFA"
_LOSS = "#E4564A"
_WIN_MUTED = "#A8F0CF"
_DRAW_MUTED = "#B8CFFE"
_LOSS_MUTED = "#FAC0BC"
_GOLD_BRIGHT = "#FFD66B"

_MONO = "JetBrains Mono, monospace"
_DISPLAY = "Archivo, sans-serif"
_BODY = "Inter, sans-serif"


def _cartesian_axis() -> dict:
    """Styling for standard x/y Cartesian axes."""
    return dict(
        gridcolor=_BORDER,
        gridwidth=1,
        linecolor=_BORDER,
        linewidth=1,
        tickcolor=_MUTED,
        tickfont=dict(family=_MONO, size=11, color=_MUTED),
        title_font=dict(family=_BODY, size=12, color=_MUTED),
        zerolinecolor=_BORDER,
        zerolinewidth=1,
    )


def _ternary_axis(title: str = "") -> dict:
    """Styling for ternary axes — subset of valid properties (no zerolinecolor)."""
    d = dict(
        gridcolor=_BORDER,
        linecolor=_BORDER,
        tickcolor=_MUTED,
        tickfont=dict(family=_MONO, size=10, color=_MUTED),
    )
    if title:
        d["title"] = title
    return d


def register_tempo_template() -> None:
    """
    Build and register pio.templates["tempo"].
    Idempotent — safe to call multiple times.
    """
    ca = _cartesian_axis()

    layout = go.Layout(
        # ── Surfaces ──────────────────────────────────────────────────────
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,

        # ── Typography ────────────────────────────────────────────────────
        font=dict(family=_BODY, size=13, color=_TEXT),
        title=dict(
            font=dict(family=_DISPLAY, size=15, color=_TEXT),
            x=0,
            xanchor="left",
            pad=dict(l=0, t=0),
        ),

        # ── Axes ──────────────────────────────────────────────────────────
        xaxis=ca,
        yaxis=ca,

        # ── Legend ────────────────────────────────────────────────────────
        legend=dict(
            bgcolor="rgba(20,20,23,0.85)",
            bordercolor=_BORDER,
            borderwidth=1,
            font=dict(family=_BODY, size=12, color=_TEXT),
        ),

        # ── Hover ─────────────────────────────────────────────────────────
        hoverlabel=dict(
            bgcolor=_SURFACE,
            bordercolor=_BORDER,
            font=dict(family=_MONO, size=12, color=_TEXT),
            align="left",
        ),
        hovermode="closest",

        # ── Colorway — Win/Draw/Loss triad first, gold accent, then muted ─
        colorway=[_WIN, _DRAW, _LOSS, _GOLD, _WIN_MUTED, _DRAW_MUTED, _LOSS_MUTED, _GOLD_BRIGHT],

        # ── Margins ───────────────────────────────────────────────────────
        margin=dict(l=48, r=16, t=40, b=40),

        # ── Modebar — slim, no logo ────────────────────────────────────────
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=_MUTED,
            activecolor=_GOLD,
            orientation="v",
        ),

        # ── Ternary (for match space scatterternary) ───────────────────────
        ternary=dict(
            bgcolor=_BG,
            aaxis=_ternary_axis("Home Win"),
            baxis=_ternary_axis("Draw"),
            caxis=_ternary_axis("Away Win"),
        ),
    )

    pio.templates["tempo"] = go.layout.Template(layout=layout)
