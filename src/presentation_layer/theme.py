"""
Single source of truth for all Tempo design tokens.
Follows DESIGN.md.  Import this module; never hardcode hex values in components.
"""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Tempo"


@dataclass(frozen=True)
class _DarkPalette:
    BG: str = "#0B0B0D"
    SURFACE: str = "#141417"
    SURFACE_RAISED: str = "#1C1C21"
    BORDER: str = "#2A2A31"
    TEXT: str = "#F4F1EA"
    TEXT_MUTED: str = "#A7A39B"
    GOLD: str = "#E8B84B"
    GOLD_BRIGHT: str = "#FFD66B"
    WIN: str = "#1FB479"
    DRAW: str = "#3E7BFA"
    LOSS: str = "#E4564A"
    WIN_TEXT: str = "#A8F0CF"
    DRAW_TEXT: str = "#B8CFFE"
    LOSS_TEXT: str = "#FAC0BC"


@dataclass(frozen=True)
class _LightPalette:
    BG: str = "#F8F7F4"
    SURFACE: str = "#FFFFFF"
    SURFACE_RAISED: str = "#F1EFE9"
    BORDER: str = "#DDD9D1"
    TEXT: str = "#16151A"
    TEXT_MUTED: str = "#6B675F"
    GOLD: str = "#C9982A"
    GOLD_BRIGHT: str = "#E8B84B"
    WIN: str = "#0F9060"
    DRAW: str = "#2B62D9"
    LOSS: str = "#C63F35"
    WIN_TEXT: str = "#0D6B47"
    DRAW_TEXT: str = "#1A4BAD"
    LOSS_TEXT: str = "#9E2F27"


DARK = _DarkPalette()
LIGHT = _LightPalette()


class FONTS:
    GOOGLE_FONTS_URL = (
        "https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62.5..125,100..900"
        ";0,62.5..125,100..900&family=Inter:wght@400;500;600&"
        "family=JetBrains+Mono:wght@400;600&display=swap"
    )
    DISPLAY = "'Archivo', sans-serif"
    BODY = "'Inter', sans-serif"
    MONO = "'JetBrains Mono', monospace"


class SPACING:
    S1 = "4px"; S2 = "8px"; S3 = "12px"; S4 = "16px"
    S5 = "24px"; S6 = "32px"; S7 = "48px"; S8 = "64px"


class ANIMATION:
    FAST = "150ms"; NORMAL = "200ms"; SLOW = "300ms"


class PROB_BAR:
    HEIGHT = "28px"
    MIN_SHOW_LABEL = 0.08
    ANIMATION_MS = 200


class GEO_UNIT:
    SIZE = "32px"
    OPACITY_BG = 0.06


class FLAGS:
    RETRO_GOAL_FX = False


def apply_global_css(theme: _DarkPalette | _LightPalette = DARK) -> None:
    """Thin wrapper — delegates to styles.inject(), the single CSS injection point."""
    from src.presentation_layer.styles import inject
    inject(theme=theme)
