"""
Tempo icon system — §7g of DESIGN.md.

All icons are inline Lucide SVG: 1.5px stroke, currentColor, no fill.
Available sizes: 16, 20, 24px.

Usage:
    from src.presentation_layer.icons import icon
    st.markdown(icon("trending-up", size=20) + " RPS improving", unsafe_allow_html=True)

No emoji as icons. Inline SVG only (accessible, color-inheriting, crisp at any DPR).
"""

from __future__ import annotations

# Lucide icon paths — d attribute only. All icons share the same 24×24 viewBox.
# Stroke: 1.5px, round cap/join, no fill (fill="none").
_PATHS: dict[str, str] = {
    # Status / feedback
    "x":               "M18 6 6 18M6 6l12 12",
    "check":           "M20 6 9 17l-5-5",
    "check-circle":    "M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4 12 14.01l-3-3",
    "info":            "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    "alert-triangle":  "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01",
    "circle-dot":      "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zm-10 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",

    # Trend / data
    "trending-up":     "M22 7 13.5 15.5 8.5 10.5 2 17M22 7h-6M22 7v6",
    "trending-down":   "M22 17 13.5 8.5 8.5 13.5 2 7M22 17h-6M22 17v-6",
    "bar-chart-2":     "M18 20V10M12 20V4M6 20v-6",
    "target":          "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zm-6 0a4 4 0 1 1-8 0 4 4 0 0 1 8 0zm-2 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0",
    "activity":        "M22 12h-4l-3 9L9 3l-3 9H2",

    # Navigation / UI
    "chevron-right":   "m9 18 6-6-6-6",
    "chevron-down":    "m6 9 6 6 6-6",
    "chevron-up":      "m18 15-6-6-6 6",
    "external-link":   "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3",
    "filter":          "M22 3H2l8 9.46V19l4 2v-8.54L22 3",
    "search":          "M11 3a8 8 0 1 0 0 16A8 8 0 0 0 11 3zm10 10-4.35-4.35",
    "sliders":         "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",

    # Time / schedule
    "calendar":        "M8 2v4M16 2v4M3 10h18M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z",
    "clock":           "M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 5v5l3 3",
    "refresh-cw":      "M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16",

    # Awards / social
    "award":           "M8.21 13.89 7 23l5-3 5 3-1.21-9.12M12 15a7 7 0 1 0 0-14 7 7 0 0 0 0 14z",
    "trophy":          "M6 9H3.5a2.5 2.5 0 0 1 0-5H6M18 9h2.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17a1 1 0 0 1-.33.67L8 20h8l-1.67-2.33A1 1 0 0 1 14 17v-2.34M18 2H6v7a6 6 0 0 0 12 0V2z",
    "share-2":         "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13",

    # Data / files
    "database":        "M12 2C8.13 2 5 3.34 5 5v14c0 1.66 3.13 3 7 3s7-1.34 7-3V5c0-1.66-3.13-3-7-3zM5 12c0 1.66 3.13 3 7 3s7-1.34 7-3M5 5c0 1.66 3.13 3 7 3s7-1.34 7-3",
    "download":        "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",

    # Football / sports
    "globe":           "M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z",
    "flag":            "M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7",
    "zap":             "M13 2 3 14h9l-1 8 10-12h-9l1-8",
}


def icon(
    name: str,
    size: int = 20,
    stroke_width: float = 1.5,
    color: str = "currentColor",
    label: str = "",
    css_class: str = "",
) -> str:
    """
    Return an inline SVG string for the named Lucide icon.

    Args:
        name:         Icon key from _PATHS (e.g. "trending-up").
        size:         Pixel size — 16, 20, or 24 recommended (§7g).
        stroke_width: Line width in px. Default 1.5 per §7g.
        color:        CSS color or "currentColor" (inherits from parent).
        label:        aria-label for accessibility. Required for standalone icons.
        css_class:    Extra CSS class names to add to the <svg> element.

    Returns:
        HTML string containing one <svg> element. Safe to pass to
        st.markdown(..., unsafe_allow_html=True).
    """
    if name not in _PATHS:
        available = ", ".join(sorted(_PATHS.keys()))
        raise ValueError(f"Unknown icon '{name}'. Available: {available}")

    path_d = _PATHS[name]
    aria = f' aria-label="{label}"' if label else ' aria-hidden="true"'
    cls = f"tempo-icon {css_class}".strip()

    return (
        f'<svg class="{cls}" xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round"{aria}>'
        f'<path d="{path_d}"/>'
        f"</svg>"
    )


def icon_text(
    icon_name: str,
    text: str,
    size: int = 16,
    gap: str = "6px",
    color: str = "currentColor",
    bold: bool = False,
) -> str:
    """Inline icon + text in a flex span. Convenience wrapper for common pattern."""
    weight = "600" if bold else "400"
    svg = icon(icon_name, size=size, color=color)
    return (
        f'<span style="display:inline-flex;align-items:center;gap:{gap};'
        f'font-weight:{weight};">{svg}{text}</span>'
    )
