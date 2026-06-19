"""
Single source of truth for all Tempo design tokens.
Follows CLAUDE.md §7.  Import this module; never hardcode hex values in components.
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
    """Inject Google Fonts + full CSS custom properties into the Streamlit app."""
    import streamlit as st

    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800;900'
        '&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap"'
        ' rel="stylesheet">',
        unsafe_allow_html=True,
    )

    css = f"""
<style>
/* ── Custom properties ────────────────────────────────────────────── */
:root {{
  --bg:              {theme.BG};
  --surface:         {theme.SURFACE};
  --surface-raised:  {theme.SURFACE_RAISED};
  --border:          {theme.BORDER};
  --text:            {theme.TEXT};
  --text-muted:      {theme.TEXT_MUTED};
  --gold:            {theme.GOLD};
  --gold-bright:     {theme.GOLD_BRIGHT};
  --win:             {theme.WIN};
  --draw:            {theme.DRAW};
  --loss:            {theme.LOSS};
  --win-text:        {theme.WIN_TEXT};
  --draw-text:       {theme.DRAW_TEXT};
  --loss-text:       {theme.LOSS_TEXT};
  --ff-display:      {FONTS.DISPLAY};
  --ff-body:         {FONTS.BODY};
  --ff-mono:         {FONTS.MONO};
  --anim-fast:       {ANIMATION.FAST};
  --anim-normal:     {ANIMATION.NORMAL};
  --anim-slow:       {ANIMATION.SLOW};
  --radius-sm:       8px;
  --radius-md:       12px;
  --radius-lg:       16px;
}}

/* ── Base ─────────────────────────────────────────────────────────── */
.stApp,
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {{
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--ff-body) !important;
  font-size: 16px;
  line-height: 1.6;
}}

/* Hide Streamlit default hamburger + footer */
#MainMenu {{ visibility: hidden !important; }}
footer {{ visibility: hidden !important; }}
[data-testid="stToolbar"] {{ visibility: hidden !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stHeader"] {{
  background-color: var(--bg) !important;
  border-bottom: 1px solid var(--border);
}}

[data-testid="block-container"] {{
  padding-top: 1.5rem !important;
  padding-bottom: 3rem !important;
  max-width: 1400px;
}}

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background-color: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] * {{
  color: var(--text) !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
  padding: 0 !important;
}}

/* Radio nav */
[data-testid="stSidebar"] [data-baseweb="radio"] {{
  gap: 4px !important;
}}
[data-testid="stSidebar"] [data-baseweb="radio"] label {{
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 0.55rem 0.9rem !important;
  border-radius: var(--radius-sm) !important;
  cursor: pointer !important;
  transition: background var(--anim-fast), color var(--anim-fast) !important;
  font-family: var(--ff-body) !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  color: var(--text-muted) !important;
  border: 1px solid transparent !important;
}}
[data-testid="stSidebar"] [data-baseweb="radio"] label:hover {{
  background: var(--surface-raised) !important;
  color: var(--text) !important;
}}
[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"] ~ label,
[data-testid="stSidebar"] [data-baseweb="radio"] label:has([aria-checked="true"]) {{
  background: rgba(232,184,75,0.08) !important;
  color: var(--gold) !important;
  border-color: rgba(232,184,75,0.2) !important;
}}
/* Hide the default radio circle */
[data-testid="stSidebar"] [data-baseweb="radio"] [type="radio"] {{
  display: none !important;
}}

/* ── Metrics ──────────────────────────────────────────────────────── */
[data-testid="metric-container"] {{
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  padding: 1rem 1.1rem !important;
  transition: border-color var(--anim-normal), box-shadow var(--anim-normal) !important;
}}
[data-testid="metric-container"]:hover {{
  border-color: rgba(232,184,75,0.3) !important;
  box-shadow: 0 0 0 1px rgba(232,184,75,0.1) !important;
}}
[data-testid="metric-container"] label {{
  color: var(--text-muted) !important;
  font-size: 0.72rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  font-weight: 600 !important;
  font-family: var(--ff-body) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  color: var(--gold) !important;
  font-family: var(--ff-mono) !important;
  font-size: 1.75rem !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
  font-variant-numeric: tabular-nums !important;
}}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
  font-family: var(--ff-mono) !important;
  font-size: 0.75rem !important;
}}

/* ── Selectbox ────────────────────────────────────────────────────── */
[data-baseweb="select"] > div,
[data-testid="stSelectbox"] > div > div {{
  background-color: var(--surface-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text) !important;
  font-family: var(--ff-body) !important;
  font-size: 0.88rem !important;
  transition: border-color var(--anim-fast) !important;
}}
[data-baseweb="select"] > div:focus-within,
[data-baseweb="select"] > div:hover {{
  border-color: rgba(232,184,75,0.5) !important;
  box-shadow: 0 0 0 2px rgba(232,184,75,0.1) !important;
}}
[data-baseweb="select"] [data-testid="stSelectboxVirtualDropdown"],
[data-baseweb="popover"] [role="listbox"] {{
  background: var(--surface-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
}}
[role="option"] {{
  background: transparent !important;
  color: var(--text) !important;
  font-size: 0.88rem !important;
  padding: 8px 14px !important;
}}
[role="option"]:hover, [aria-selected="true"] {{
  background: rgba(232,184,75,0.08) !important;
  color: var(--gold) !important;
}}

/* ── Multiselect ──────────────────────────────────────────────────── */
[data-baseweb="multi-select"] > div {{
  background-color: var(--surface-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-sm) !important;
  min-height: 38px !important;
}}
[data-baseweb="multi-select"] > div:focus-within {{
  border-color: rgba(232,184,75,0.5) !important;
  box-shadow: 0 0 0 2px rgba(232,184,75,0.1) !important;
}}
[data-baseweb="tag"] {{
  background: rgba(232,184,75,0.1) !important;
  border: 1px solid rgba(232,184,75,0.3) !important;
  border-radius: 6px !important;
  color: var(--gold) !important;
  font-size: 0.73rem !important;
  font-family: var(--ff-body) !important;
  padding: 1px 6px !important;
}}
[data-baseweb="tag"] [data-testid="stMarkdownContainer"],
[data-baseweb="tag"] span {{ color: var(--gold) !important; }}
[data-baseweb="multi-select"] input {{
  color: var(--text) !important;
  font-family: var(--ff-body) !important;
  font-size: 0.85rem !important;
}}

/* ── Tabs ─────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
  background: transparent !important;
  color: var(--text-muted) !important;
  font-weight: 500 !important;
  border-bottom: 2px solid transparent !important;
  padding: 0.55rem 1.1rem !important;
  font-size: 0.85rem !important;
  font-family: var(--ff-body) !important;
  transition: color var(--anim-fast), border-color var(--anim-fast) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {{
  color: var(--text) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
  color: var(--gold) !important;
  border-bottom-color: var(--gold) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: var(--gold) !important;
  height: 2px !important;
}}

/* ── Dataframe / Table ────────────────────────────────────────────── */
[data-testid="stDataFrame"],
iframe {{
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border) !important;
  overflow: hidden !important;
}}
[data-testid="stDataFrameGlideDataEditor"] {{
  background: var(--surface) !important;
}}

/* ── Plotly chart containers ──────────────────────────────────────── */
[data-testid="stPlotlyChart"] {{
  border-radius: var(--radius-md);
  overflow: hidden;
}}

/* ── Buttons ──────────────────────────────────────────────────────── */
[data-testid="baseButton-secondary"],
button[kind="secondary"] {{
  background: var(--surface-raised) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--ff-body) !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  transition: all var(--anim-fast) !important;
}}
[data-testid="baseButton-secondary"]:hover {{
  border-color: rgba(232,184,75,0.5) !important;
  color: var(--gold) !important;
  box-shadow: 0 2px 12px rgba(232,184,75,0.15) !important;
}}
[data-testid="baseButton-primary"],
button[kind="primary"] {{
  background: var(--gold) !important;
  border: none !important;
  color: #0B0B0D !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--ff-display) !important;
  font-weight: 700 !important;
  font-size: 0.88rem !important;
}}
[data-testid="baseButton-primary"]:hover {{
  background: var(--gold-bright) !important;
  box-shadow: 0 4px 16px rgba(232,184,75,0.35) !important;
}}

/* ── Scrollbar ────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: #3a3a45; }}

/* ── Label text ───────────────────────────────────────────────────── */
[data-testid="stWidgetLabel"] p,
.stSelectbox label,
.stMultiSelect label {{
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  font-family: var(--ff-body) !important;
}}

/* ── Focus ring ───────────────────────────────────────────────────── */
:focus-visible {{
  outline: 2px solid var(--gold) !important;
  outline-offset: 2px !important;
}}

/* ──────────────────────────────────────────────────────────────────
   CUSTOM COMPONENT STYLES
   ────────────────────────────────────────────────────────────────── */

/* Accent rail */
.accent-rail {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--win) 0% 33.3%,
    var(--draw) 33.3% 66.6%,
    var(--loss) 66.6% 100%);
  border-radius: 2px;
  margin-bottom: 1.5rem;
}}

/* Page header */
.page-header {{
  margin-bottom: 1.25rem;
}}
.page-header h1 {{
  font-family: var(--ff-display) !important;
  font-weight: 900 !important;
  font-size: 2rem !important;
  color: var(--text) !important;
  margin: 0 0 0.25rem 0 !important;
  line-height: 1.1 !important;
  letter-spacing: -0.02em !important;
}}
.page-header .subtitle {{
  color: var(--text-muted);
  font-size: 0.87rem;
  letter-spacing: 0.01em;
  margin: 0;
}}

/* Section heading */
.sec-heading {{
  font-family: var(--ff-display);
  font-weight: 800;
  font-size: 0.78rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 0.75rem;
  margin-top: 0.25rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}}

/* ── Match cards ──────────────────────────────────────────────────── */
.match-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 1rem;
  transition:
    border-color var(--anim-normal),
    box-shadow var(--anim-normal),
    transform var(--anim-fast);
  position: relative;
}}
.match-card::before {{
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  background: radial-gradient(ellipse at 50% 0%, rgba(232,184,75,0.04) 0%, transparent 60%);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--anim-normal);
}}
.match-card:hover {{
  border-color: rgba(232,184,75,0.4);
  box-shadow:
    0 0 0 1px rgba(232,184,75,0.08),
    0 8px 32px rgba(0,0,0,0.45),
    0 2px 8px rgba(232,184,75,0.05);
}}
.match-card:hover::before {{
  opacity: 1;
}}
.match-card-rail {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--win) 0% 33.3%,
    var(--draw) 33.3% 66.6%,
    var(--loss) 66.6% 100%);
}}
.match-card-body {{
  padding: 1.1rem 1.25rem 1.1rem;
}}

/* Match chip (WC26 · Grp A · Fri 20 Jun) */
.match-chip {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 10px;
  font-family: var(--ff-mono);
  font-size: 0.66rem;
  color: var(--text-muted);
  letter-spacing: 0.05em;
  margin-bottom: 0.85rem;
  text-transform: uppercase;
}}

/* Teams */
.match-teams {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 1rem;
}}
.team-block {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}}
.team-block.away {{
  flex-direction: row-reverse;
  text-align: right;
}}
.team-flag {{
  font-size: 1.5rem;
  line-height: 1;
  flex-shrink: 0;
}}
.team-name {{
  font-family: var(--ff-display) !important;
  font-weight: 800 !important;
  font-size: 0.98rem !important;
  color: var(--text) !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em !important;
}}
.match-vs {{
  color: var(--border);
  font-family: var(--ff-mono);
  font-size: 0.72rem;
  font-weight: 600;
  flex-shrink: 0;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  letter-spacing: 0.08em;
}}

/* ── Probability bar ──────────────────────────────────────────────── */
.prob-bar-track {{
  display: flex;
  height: 28px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  gap: 2px;
  margin-bottom: 4px;
}}
.prob-seg {{
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--ff-mono);
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  min-width: 0;
  letter-spacing: -0.01em;
}}
.seg-home {{
  background: var(--win);
  color: #0a3d27;
  border-radius: 6px 0 0 6px;
}}
.seg-draw {{
  background: var(--draw);
  color: #0d1e52;
}}
.seg-away {{
  background: var(--loss);
  color: #4a0f0a;
  border-radius: 0 6px 6px 0;
}}
.prob-bar-labels {{
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  padding: 0 1px;
}}
.prob-label {{
  font-size: 0.62rem;
  color: var(--text-muted);
  font-family: var(--ff-mono);
  letter-spacing: 0.03em;
}}

/* ── Favored chip ─────────────────────────────────────────────────── */
.favored-chip {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(232,184,75,0.08);
  border: 1px solid rgba(232,184,75,0.2);
  border-radius: 20px;
  padding: 3px 12px 3px 8px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--gold);
  font-family: var(--ff-body);
  margin: 0.4rem 0;
}}
.favored-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold);
  display: inline-block;
  flex-shrink: 0;
  box-shadow: 0 0 6px rgba(232,184,75,0.6);
}}

/* ── Factor chips ─────────────────────────────────────────────────── */
.factors-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 0.4rem;
}}
.factor-chip {{
  font-size: 0.67rem;
  font-family: var(--ff-body);
  font-weight: 500;
  border-radius: 5px;
  padding: 3px 8px;
  letter-spacing: 0.01em;
  line-height: 1.3;
}}
.fpos {{
  background: rgba(31,180,121,0.1);
  color: #6ee9b7;
  border: 1px solid rgba(31,180,121,0.22);
}}
.fneg {{
  background: rgba(228,86,74,0.1);
  color: #f9a9a4;
  border: 1px solid rgba(228,86,74,0.22);
}}

/* ── Live badge ───────────────────────────────────────────────────── */
.live-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(228,86,74,0.1);
  border: 1px solid rgba(228,86,74,0.3);
  border-radius: 20px;
  padding: 3px 11px;
  font-size: 0.65rem;
  font-family: var(--ff-mono);
  color: var(--loss);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
}}
.live-dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--loss);
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50%  {{ opacity: 0.35; transform: scale(0.85); }}
}}

/* ── Data stamp ───────────────────────────────────────────────────── */
.data-stamp {{
  font-size: 0.68rem;
  color: var(--text-muted);
  font-family: var(--ff-mono);
  padding: 4px 0;
  margin-top: 0.5rem;
}}
.data-stamp code {{
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  color: var(--gold);
  font-size: 0.68rem;
}}

/* ── No-data state ────────────────────────────────────────────────── */
.no-data {{
  text-align: center;
  padding: 3.5rem 1rem;
  color: var(--text-muted);
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
  margin: 1rem 0;
}}
.no-data h3 {{
  font-family: var(--ff-display);
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text);
  margin: 0 0 0.5rem 0;
}}
.no-data code {{
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 3px 8px;
  font-family: var(--ff-mono);
  font-size: 0.8rem;
  color: var(--gold);
}}

/* ── Model report cards ───────────────────────────────────────────── */
.metric-card {{
  flex: 1;
  min-width: 120px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1rem 1.1rem;
  transition: border-color var(--anim-normal);
}}
.metric-card:hover {{
  border-color: rgba(232,184,75,0.3);
}}
.metric-card .mc-label {{
  font-size: 0.68rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600;
  margin-bottom: 5px;
}}
.metric-card .mc-value {{
  font-family: var(--ff-mono);
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--gold);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}}
.metric-card .mc-sub {{
  font-size: 0.67rem;
  color: var(--text-muted);
  margin-top: 3px;
}}

/* Beat-baseline badge */
.beat-baseline {{
  background: rgba(31,180,121,0.1);
  border: 1px solid rgba(31,180,121,0.28);
  color: #6ee9b7;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 0.7rem;
  font-family: var(--ff-mono);
  display: inline-block;
  margin-left: 6px;
}}

/* ── Outcome probability table ────────────────────────────────────── */
.outcome-table {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  margin-top: 0.75rem;
}}
.outcome-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.55rem 1rem;
  border-top: 1px solid var(--border);
}}
.outcome-row:first-child {{ border-top: none; }}

/* ── Sidebar brand ────────────────────────────────────────────────── */
.sidebar-brand {{
  padding: 0.5rem 0 1.25rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.75rem;
}}
.sidebar-brand-name {{
  font-family: var(--ff-display);
  font-weight: 900;
  font-size: 1.55rem;
  color: var(--gold);
  letter-spacing: -0.03em;
  line-height: 1;
  margin-bottom: 3px;
}}
.sidebar-brand-sub {{
  font-size: 0.68rem;
  color: var(--text-muted);
  font-family: var(--ff-mono);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}}
.sidebar-legend {{
  font-size: 0.68rem;
  color: var(--text-muted);
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  margin-top: auto;
  line-height: 1.8;
}}

/* ── Animations ───────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }}
}}

/* ── Mobile ───────────────────────────────────────────────────────── */
@media (max-width: 768px) {{
  [data-testid="block-container"] {{
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
  }}
  .page-header h1 {{ font-size: 1.5rem !important; }}
  .team-name {{ font-size: 0.85rem !important; }}
  .match-card-body {{ padding: 0.9rem 1rem; }}
  .match-teams {{ flex-direction: column; gap: 0.35rem; }}
  .team-block.away {{ flex-direction: row; text-align: left; }}
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)
