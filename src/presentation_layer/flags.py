"""
Flag rendering helper — Layer 3 presentation only.

flag_img(code, width) → HTML string with base64-inlined SVG.

SVGs are sourced from assets/flags/{code}.svg (lipis/flag-icons, MIT).
Base64 inlining is required because Streamlit cannot serve arbitrary local
paths inside unsafe_allow_html markdown.

Fail-soft per §6: missing SVG → neutral geo-unit chip with 3-letter abbreviation.
"""

from __future__ import annotations

import base64
import functools
from pathlib import Path

_FLAGS_DIR = Path("assets/flags")

# Inline style shared by all flag images
_IMG_STYLE = (
    "display:inline-block;"
    "vertical-align:middle;"
    "border-radius:4px;"
    "border:1px solid var(--border,#2A2A31);"
    "flex-shrink:0;"
    "object-fit:cover;"
)

# Fallback chip style when no SVG is available
_CHIP_STYLE = (
    "display:inline-flex;align-items:center;justify-content:center;"
    "width:{w}px;height:{h}px;"
    "border-radius:4px;border:1px solid var(--border,#2A2A31);"
    "background:var(--surface-raised,#1C1C21);"
    "font-family:'JetBrains Mono',monospace;"
    "font-size:{fs}px;font-weight:600;"
    "color:var(--text-muted,#A7A39B);"
    "letter-spacing:0.05em;flex-shrink:0;"
)


@functools.lru_cache(maxsize=64)
def _load_b64(code: str) -> str | None:
    """Read SVG from disk and return base64-encoded string, or None if missing."""
    path = _FLAGS_DIR / f"{code}.svg"
    if not path.exists():
        return None
    raw = path.read_bytes()
    return base64.b64encode(raw).decode("ascii")


def flag_img(
    code: str,
    width: int = 30,
    team_name: str = "",
    extra_style: str = "",
) -> str:
    """
    Return an HTML snippet for a country flag.

    Parameters
    ----------
    code        lipis/flag-icons code, e.g. "gb-eng", "fr", "us"
    width       rendered width in px (height = width * 3/4 for 4:3 ratio)
    team_name   used only for alt text and the fallback chip label
    extra_style additional inline CSS appended to the <img> style
    """
    height = round(width * 3 / 4)
    abbr = (team_name[:3] or code[:3]).upper()
    alt  = team_name or code

    b64 = _load_b64(code) if code else None

    if b64 is not None:
        style = _IMG_STYLE + (f";{extra_style}" if extra_style else "")
        return (
            f'<img src="data:image/svg+xml;base64,{b64}" '
            f'width="{width}" height="{height}" '
            f'alt="{alt}" title="{alt}" '
            f'style="{style}">'
        )

    # Fail-soft: geo-unit chip with 3-letter abbreviation
    fs = max(7, round(width * 0.28))
    chip_style = _CHIP_STYLE.format(w=width, h=height, fs=fs)
    return f'<span style="{chip_style}" title="{alt}">{abbr}</span>'
