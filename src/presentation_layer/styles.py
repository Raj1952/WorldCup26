"""
Tempo — single CSS injection point.

Call inject(theme) ONCE from app.py at startup, before any st.markdown calls.
Emits all CSS custom properties (colors, type, spacing, radius, easing, z-index),
Google Fonts wiring, Streamlit chrome strip, and all component styles in one block.

Layer boundary: may import streamlit (Layer 3 presentation).
Never import scikit-learn, xgboost, or any Layer 2 model module here.
"""

from __future__ import annotations

from src.presentation_layer.theme import DARK, _DarkPalette, _LightPalette

_FONT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Archivo:wght@400;600;700;800;900"
    "&family=Inter:ital,wght@0,400;0,500;0,600;1,400"
    "&family=JetBrains+Mono:wght@400;600"
    "&display=swap"
)


def _build_css(theme: _DarkPalette | _LightPalette) -> str:
    t = theme
    return f"""
@import url('{_FONT_URL}');

/* ── Design tokens ──────────────────────────────────────────────────────── */
:root {{
  /* Color — §2a */
  --bg:              {t.BG};
  --surface:         {t.SURFACE};
  --surface-raised:  {t.SURFACE_RAISED};
  --border:          {t.BORDER};
  --text:            {t.TEXT};
  --text-muted:      {t.TEXT_MUTED};
  --gold:            {t.GOLD};
  --gold-bright:     {t.GOLD_BRIGHT};
  --win:             {t.WIN};
  --draw:            {t.DRAW};
  --loss:            {t.LOSS};
  --win-text:        {t.WIN_TEXT};
  --draw-text:       {t.DRAW_TEXT};
  --loss-text:       {t.LOSS_TEXT};

  /* Typography — §3a */
  --ff-display: 'Archivo', sans-serif;
  --ff-body:    'Inter', sans-serif;
  --ff-mono:    'JetBrains Mono', monospace;

  /* Spacing — 4pt base, 8pt rhythm — §4a */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
  --sp-5: 24px; --sp-6: 32px; --sp-7: 48px; --sp-8: 64px;

  /* Border radius — §5a */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;

  /* Motion — durations — §5c */
  --anim-fast:   150ms;
  --anim-normal: 200ms;
  --anim-slow:   300ms;

  /* Motion — explicit cubic-bezier easing (never the 'ease' keyword) — §5c */
  --ease-fast:   cubic-bezier(0.25, 0, 0, 1);    /* ease-out-quart  */
  --ease-normal: cubic-bezier(0.16, 1, 0.3, 1);  /* expo-out        */
  --ease-slow:   cubic-bezier(0.12, 0, 0.39, 0); /* ease-out-quint  */

  /* Z-index — semantic scale, never arbitrary values — §5d */
  --z-base:            0;
  --z-sticky:        100;
  --z-dropdown:      200;
  --z-modal-backdrop: 300;
  --z-modal:         400;
  --z-toast:         500;
  --z-tooltip:       600;

  /* App shell — top nav: 3px tri-rail + 56px inner */
  --nav-height: 59px;
}}

/* ── Streamlit chrome strip ─────────────────────────────────────────────── */
/* config.toml sets toolbarMode=minimal — CSS doubles down on survivors      */
#MainMenu,
footer,
footer[data-testid="stFooter"],
[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stDeployButton"],
[data-testid="stDecoration"],
[data-testid="stHeader"]                     {{ display: none !important; }}

[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="block-container"],
.block-container                             {{ padding-top: calc(var(--nav-height) + 1rem) !important; }}

[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
.block-container                             {{ padding-bottom: 3rem !important; }}

[data-testid="block-container"],
.block-container                             {{ max-width: 1400px !important; margin: 0 auto; }}

[data-testid="stMainBlockContainer"]         {{
  padding-left:  2rem !important;
  padding-right: 2rem !important;
}}

/* ── Base surface ───────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {{
  background-color: var(--bg) !important;
}}
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
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

/* ── Font-family assignments ────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6,
.page-header h1, .sidebar-brand-name, .sec-heading, .team-name {{
  font-family: var(--ff-display) !important;
}}
code, pre,
[data-testid="stMetricValue"],
.prob-seg, .match-chip, .data-stamp,
.sidebar-brand-sub, .favored-chip, .sidebar-legend {{
  font-family: var(--ff-mono) !important;
  font-variant-numeric: tabular-nums !important;
}}

/* Prose typography — §3c */
p, .subtitle, .stMarkdown p {{
  text-wrap: pretty;     /* prevent orphaned last words */
}}
h1, h2, h3 {{
  text-wrap: balance;    /* even line breaks on headings */
}}
.stMarkdown p, .subtitle {{
  max-width: 72ch;       /* cap body line length per §3c */
}}

/* ── Sidebar: hidden — top-nav console replaces it ──────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNav"],
button[aria-label="Open sidebar"],
button[title="Open sidebar"]               {{ display: none !important; }}

/* ── Top navigation — fixed broadcast console ────────────────────────────
   Position: fixed at viewport top so it survives page scroll.
   z-index: --z-sticky (100) — above content, below Streamlit dropdowns (200).
   ──────────────────────────────────────────────────────────────────────── */
.tempo-nav {{
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: var(--z-sticky);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}}
/* Tri-color accent rail — 3px at very top of nav */
.tempo-nav-rail {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--win) 0% 33.3%, var(--draw) 33.3% 66.6%, var(--loss) 66.6% 100%);
}}
/* Inner row: brand | links | meta */
.tempo-nav-inner {{
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 56px;
  max-width: 1400px;
  margin: 0 auto;
  gap: 0;
}}
/* Brand */
.tempo-brand {{
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-decoration: none;
  margin-right: 2rem;
  flex-shrink: 0;
  min-height: 44px;
  line-height: 1;
  color: var(--gold);          /* currentColor in SVG resolves to gold */
}}
.tempo-brand:hover {{ color: var(--gold); }}  /* no hover-dim on wordmark */
.tempo-brand-name {{
  font-family: var(--ff-display);
  font-weight: 900;
  font-size: 1.05rem;
  color: var(--gold);
  letter-spacing: -0.03em;
  line-height: 1.1;
}}
.tempo-brand-sub {{
  font-family: var(--ff-mono);
  font-size: 0.52rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  line-height: 1.6;
}}
/* Wordmark SVG — sizing; responsive visibility toggled by media queries below */
.tempo-brand-wordmark {{ display: flex; align-items: center; line-height: 0; }}
.tempo-brand-wordmark svg {{ height: 24px; width: auto; display: block; }}
.tempo-brand-icon {{ display: none; line-height: 0; }}
.tempo-brand-icon svg {{ height: 24px; width: auto; display: block; }}
/* Nav link list */
.tempo-nav-links {{
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  align-items: center;
}}
.tempo-nav-links::-webkit-scrollbar {{ display: none; }}
/* Individual nav link */
.tempo-nav-link {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 14px;
  min-height: 44px;     /* §9: 44px touch target */
  min-width: 44px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  font-family: var(--ff-body);
  font-size: 0.84rem;
  font-weight: 500;
  color: var(--text-muted);
  white-space: nowrap;
  border: 1px solid transparent;
  transition:
    background     var(--anim-fast) var(--ease-fast),
    color          var(--anim-fast) var(--ease-fast),
    border-color   var(--anim-fast) var(--ease-fast);
}}
.tempo-nav-link:hover {{
  background: var(--surface-raised);
  color: var(--text);
}}
/* Active route — Signal Gold + raised background */
.tempo-nav-link.is-active {{
  background: rgba(232,184,75,0.08);
  color: var(--gold);
  border-color: rgba(232,184,75,0.2);
}}
.tempo-nav-link.is-active svg {{ color: var(--gold); }}
/* Keyboard focus — §9 */
.tempo-nav-link:focus-visible {{
  outline: 2px solid var(--gold) !important;
  outline-offset: 2px !important;
}}
.tempo-brand:focus-visible {{
  outline: 2px solid var(--gold) !important;
  outline-offset: 2px !important;
  border-radius: var(--radius-sm);
}}
/* SVG icon inside link */
.tempo-nav-link svg {{ flex-shrink: 0; transition: color var(--anim-fast) var(--ease-fast); }}
/* "Soon" badge on not-yet-built routes */
.tempo-nav-soon {{
  font-size: 0.5rem;
  font-family: var(--ff-mono);
  background: var(--surface-raised);
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
  line-height: 1.4;
}}
/* Right-side meta ("Updates daily · batch") */
.tempo-nav-meta {{
  flex-shrink: 0;
  margin-left: 1.25rem;
  font-family: var(--ff-mono);
  font-size: 0.6rem;
  color: var(--text-muted);
  white-space: nowrap;
  letter-spacing: 0.05em;
  opacity: 0.7;
}}

/* ── Nav: mobile ≤768px ────────────────────────────────────────────────── */
@media (max-width: 768px) {{
  .tempo-nav-inner {{
    padding: 0 0.75rem;
    height: 56px; /* keep single-row height for consistent --nav-height */
  }}
  .tempo-brand {{ margin-right: 1rem; }}
  .tempo-brand-sub {{ display: none; }}
  .tempo-nav-meta {{ display: none; }}
}}
/* ── Nav: compact icon-only at 480px ────────────────────────────────────── */
@media (max-width: 480px) {{
  .tempo-nav-label {{ display: none; }}
  .tempo-nav-link {{
    padding: 0 10px;
    min-width: 44px;
    justify-content: center;
    gap: 0;
  }}
  /* Swap full wordmark for T-block icon */
  .tempo-brand-wordmark {{ display: none; }}
  .tempo-brand-icon {{ display: flex; align-items: center; }}
}}

/* ── st.metric ──────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {{
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  padding: 1rem 1.1rem !important;
  transition: border-color var(--anim-normal) var(--ease-normal),
              box-shadow   var(--anim-normal) var(--ease-normal) !important;
}}
[data-testid="metric-container"]:hover {{
  border-color: rgba(232,184,75,0.3) !important;
  box-shadow: 0 0 0 1px rgba(232,184,75,0.1) !important;
}}
[data-testid="metric-container"] label {{
  color: var(--text-muted) !important; font-size: 0.72rem !important;
  text-transform: uppercase !important; letter-spacing: 0.07em !important;
  font-weight: 600 !important; font-family: var(--ff-body) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  color: var(--gold) !important; font-family: var(--ff-mono) !important;
  font-size: 1.75rem !important; font-weight: 700 !important;
  line-height: 1.2 !important; font-variant-numeric: tabular-nums !important;
}}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
  font-family: var(--ff-mono) !important; font-size: 0.75rem !important;
}}

/* ── Selectbox ──────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div,
[data-testid="stSelectbox"] > div > div {{
  background-color: var(--surface-raised) !important;
  border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important;
  color: var(--text) !important; font-family: var(--ff-body) !important;
  font-size: 0.88rem !important;
  transition: border-color var(--anim-fast) var(--ease-fast) !important;
}}
[data-baseweb="select"] > div:focus-within,
[data-baseweb="select"] > div:hover {{
  border-color: rgba(232,184,75,0.5) !important;
  box-shadow: 0 0 0 2px rgba(232,184,75,0.1) !important;
}}
[data-baseweb="select"] [data-testid="stSelectboxVirtualDropdown"],
[data-baseweb="popover"] [role="listbox"] {{
  background: var(--surface-raised) !important;
  border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
  z-index: var(--z-dropdown) !important;
}}
[role="option"] {{
  background: transparent !important; color: var(--text) !important;
  font-size: 0.88rem !important; padding: 8px 14px !important;
}}
[role="option"]:hover, [aria-selected="true"] {{
  background: rgba(232,184,75,0.08) !important; color: var(--gold) !important;
}}

/* ── Multiselect ────────────────────────────────────────────────────────── */
[data-baseweb="multi-select"] > div {{
  background-color: var(--surface-raised) !important;
  border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important;
  min-height: 38px !important;
}}
[data-baseweb="multi-select"] > div:focus-within {{
  border-color: rgba(232,184,75,0.5) !important;
  box-shadow: 0 0 0 2px rgba(232,184,75,0.1) !important;
}}
[data-baseweb="tag"] {{
  background: rgba(232,184,75,0.1) !important;
  border: 1px solid rgba(232,184,75,0.3) !important; border-radius: 6px !important;
  color: var(--gold) !important; font-size: 0.73rem !important;
  font-family: var(--ff-body) !important; padding: 1px 6px !important;
}}
[data-baseweb="tag"] [data-testid="stMarkdownContainer"],
[data-baseweb="tag"] span {{ color: var(--gold) !important; }}
[data-baseweb="multi-select"] input {{
  color: var(--text) !important; font-family: var(--ff-body) !important;
  font-size: 0.85rem !important;
}}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  background: var(--surface) !important;
  border-bottom: 1px solid var(--border) !important; gap: 0 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
  background: transparent !important; color: var(--text-muted) !important;
  font-weight: 500 !important; border-bottom: 2px solid transparent !important;
  padding: 0.55rem 1.1rem !important; font-size: 0.85rem !important;
  font-family: var(--ff-body) !important;
  transition: color var(--anim-fast) var(--ease-fast),
              border-color var(--anim-fast) var(--ease-fast) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {{ color: var(--text) !important; }}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {{
  color: var(--gold) !important; border-bottom-color: var(--gold) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: var(--gold) !important; height: 2px !important;
}}

/* ── Dataframe ──────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"], iframe {{
  border-radius: var(--radius-md) !important;
  border: 1px solid var(--border) !important; overflow: hidden !important;
}}
[data-testid="stDataFrameGlideDataEditor"] {{ background: var(--surface) !important; }}

/* ── Plotly containers ──────────────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {{ border-radius: var(--radius-md); overflow: hidden; }}

/* ── Buttons ────────────────────────────────────────────────────────────── */
[data-testid="baseButton-secondary"], button[kind="secondary"] {{
  background: var(--surface-raised) !important;
  border: 1px solid var(--border) !important; color: var(--text) !important;
  border-radius: var(--radius-sm) !important; font-family: var(--ff-body) !important;
  font-size: 0.85rem !important; font-weight: 500 !important;
  transition: border-color var(--anim-fast) var(--ease-fast),
              color      var(--anim-fast) var(--ease-fast),
              box-shadow var(--anim-fast) var(--ease-fast) !important;
}}
[data-testid="baseButton-secondary"]:hover {{
  border-color: rgba(232,184,75,0.5) !important; color: var(--gold) !important;
  box-shadow: 0 2px 12px rgba(232,184,75,0.15) !important;
}}
[data-testid="baseButton-primary"], button[kind="primary"] {{
  background: var(--gold) !important; border: none !important;
  color: #111114 !important; border-radius: var(--radius-sm) !important;
  font-family: var(--ff-display) !important; font-weight: 700 !important;
  font-size: 0.88rem !important;
}}
[data-testid="baseButton-primary"]:hover {{
  background: var(--gold-bright) !important;
  box-shadow: 0 4px 16px rgba(232,184,75,0.35) !important;
}}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: #3a3a45; }}

/* ── Widget labels ──────────────────────────────────────────────────────── */
[data-testid="stWidgetLabel"] p, .stSelectbox label, .stMultiSelect label {{
  color: var(--text-muted) !important; font-size: 0.75rem !important;
  font-weight: 600 !important; text-transform: uppercase !important;
  letter-spacing: 0.06em !important; font-family: var(--ff-body) !important;
}}

/* ── Focus rings — §9 ───────────────────────────────────────────────────── */
:focus-visible {{
  outline: 2px solid var(--gold) !important; outline-offset: 2px !important;
}}

/* ─────────────────────────────────────────────────────────────────────────
   COMPONENT STYLES
   ───────────────────────────────────────────────────────────────────────── */

/* Tri-color accent rail — §6b */
.accent-rail {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--win) 0% 33.3%, var(--draw) 33.3% 66.6%, var(--loss) 66.6% 100%);
  border-radius: 2px; margin-bottom: 1.5rem;
}}

/* Page header */
.page-header {{ margin-bottom: 1.25rem; }}
.page-header h1 {{
  font-family: var(--ff-display) !important; font-weight: 900 !important;
  font-size: 2rem !important; color: var(--text) !important;
  margin: 0 0 0.25rem 0 !important; line-height: 1.1 !important;
  letter-spacing: -0.02em !important; text-wrap: balance;
}}
.page-header .subtitle {{
  color: var(--text-muted); font-size: 0.87rem;
  letter-spacing: 0.01em; margin: 0; text-wrap: pretty;
}}

/* Section heading — §7d */
.sec-heading {{
  font-family: var(--ff-display); font-weight: 800; font-size: 0.78rem;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em;
  margin-bottom: 0.75rem; margin-top: 0.25rem;
  padding-bottom: 0.4rem; border-bottom: 1px solid var(--border);
}}

/* Match card — §7b: --radius-md (12px), no default shadow */
.match-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); overflow: hidden; margin-bottom: 1rem;
  transition:
    border-color var(--anim-normal) var(--ease-normal),
    box-shadow   var(--anim-normal) var(--ease-normal),
    transform    var(--anim-fast)   var(--ease-fast);
  position: relative;
}}
.match-card::before {{
  content: ''; position: absolute; inset: 0; border-radius: var(--radius-md);
  background: radial-gradient(ellipse at 50% 0%, rgba(232,184,75,0.04) 0%, transparent 60%);
  pointer-events: none; opacity: 0;
  transition: opacity var(--anim-normal) var(--ease-normal);
}}
.match-card:hover {{
  border-color: rgba(232,184,75,0.4);
  box-shadow: 0 0 0 1px rgba(232,184,75,0.08), 0 8px 32px rgba(0,0,0,0.45);
}}
.match-card:hover::before {{ opacity: 1; }}
.match-card-rail {{
  height: 3px;
  background: linear-gradient(90deg,
    var(--win) 0% 33.3%, var(--draw) 33.3% 66.6%, var(--loss) 66.6% 100%);
}}
.match-card-body {{ padding: 1.1rem 1.25rem; }}

/* Match chip — §6c */
.match-chip {{
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--surface-raised); border: 1px solid var(--border);
  border-radius: 6px; padding: 2px 10px; font-family: var(--ff-mono);
  font-size: 0.66rem; color: var(--text-muted); letter-spacing: 0.05em;
  margin-bottom: 0.85rem; text-transform: uppercase;
}}

/* Teams */
.match-teams {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.5rem; margin-bottom: 1rem;
}}
.team-block {{
  display: flex; align-items: center; gap: 0.5rem; flex: 1; min-width: 0;
}}
.team-block.away {{ flex-direction: row-reverse; text-align: right; }}
.team-flag {{ font-size: 1.5rem; line-height: 1; flex-shrink: 0; }}
.team-name {{
  font-family: var(--ff-display) !important; font-weight: 800 !important;
  font-size: 0.98rem !important; color: var(--text) !important;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  letter-spacing: -0.01em !important;
}}
.match-vs {{
  color: var(--border); font-family: var(--ff-mono); font-size: 0.72rem;
  font-weight: 600; flex-shrink: 0; padding: 4px 8px;
  border: 1px solid var(--border); border-radius: 4px; letter-spacing: 0.08em;
}}

/* Probability bar — §6a */
.prob-bar-track {{
  display: flex; height: 28px; border-radius: var(--radius-sm);
  overflow: hidden; gap: 2px; margin-bottom: 4px;
}}
.prob-seg {{
  display: flex; align-items: center; justify-content: center;
  font-family: var(--ff-mono); font-size: 0.72rem; font-weight: 700;
  white-space: nowrap; overflow: hidden; min-width: 0; letter-spacing: -0.01em;
}}
.seg-home {{ background: var(--win);  color: var(--win-text);  border-radius: 6px 0 0 6px; }}
.seg-draw {{ background: var(--draw); color: var(--draw-text); }}
.seg-away {{ background: var(--loss); color: var(--loss-text); border-radius: 0 6px 6px 0; }}
.prob-bar-labels {{
  display: flex; justify-content: space-between; margin-bottom: 0.5rem; padding: 0 1px;
}}
.prob-label {{
  font-size: 0.62rem; color: var(--text-muted); font-family: var(--ff-mono);
  letter-spacing: 0.03em;
}}

/* Favored chip — §6d */
.favored-chip {{
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(232,184,75,0.08); border: 1px solid rgba(232,184,75,0.2);
  border-radius: 20px; padding: 3px 12px 3px 8px; font-size: 0.72rem;
  font-weight: 600; color: var(--gold); font-family: var(--ff-body); margin: 0.4rem 0;
}}
.favored-dot {{
  width: 6px; height: 6px; border-radius: 50%; background: var(--gold);
  display: inline-block; flex-shrink: 0; box-shadow: 0 0 6px rgba(232,184,75,0.6);
}}

/* Factor chips — §6e */
.factors-row {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 0.4rem; }}
.factor-chip {{
  font-size: 0.67rem; font-family: var(--ff-body); font-weight: 500;
  border-radius: 5px; padding: 3px 8px; letter-spacing: 0.01em; line-height: 1.3;
}}
.fpos {{ background: rgba(76,168,130,0.1);  color: #a8d5c2; border: 1px solid rgba(76,168,130,0.22); }}
.fneg {{ background: rgba(201,100,92,0.1);  color: #ecb2ae; border: 1px solid rgba(201,100,92,0.22); }}

/* Data stamp — §7e */
.data-stamp {{
  font-size: 0.68rem; color: var(--text-muted); font-family: var(--ff-mono);
  padding: 4px 0; margin-top: 0.5rem;
}}
.data-stamp code {{
  background: var(--surface-raised); border: 1px solid var(--border);
  border-radius: 4px; padding: 1px 6px; color: var(--gold); font-size: 0.68rem;
}}

/* No-data state — §7f */
.no-data {{
  text-align: center; padding: 3.5rem 1rem; color: var(--text-muted);
  border: 1px dashed var(--border); border-radius: var(--radius-lg); margin: 1rem 0;
}}
.no-data h3 {{
  font-family: var(--ff-display); font-size: 1.15rem; font-weight: 800;
  color: var(--text); margin: 0 0 0.5rem 0;
}}
.no-data code {{
  background: var(--surface-raised); border: 1px solid var(--border);
  border-radius: 5px; padding: 3px 8px; font-family: var(--ff-mono);
  font-size: 0.8rem; color: var(--gold);
}}

/* Custom metric card (distinct from st.metric) */
.metric-card {{
  flex: 1; min-width: 120px; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 1rem 1.1rem; transition: border-color var(--anim-normal) var(--ease-normal);
}}
.metric-card:hover {{ border-color: rgba(232,184,75,0.3); }}
.metric-card .mc-label {{
  font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.07em; font-weight: 600; margin-bottom: 5px;
}}
.metric-card .mc-value {{
  font-family: var(--ff-mono); font-size: 1.65rem; font-weight: 700;
  color: var(--gold); line-height: 1.1; font-variant-numeric: tabular-nums;
}}
.metric-card .mc-sub {{ font-size: 0.67rem; color: var(--text-muted); margin-top: 3px; }}

.beat-baseline {{
  background: rgba(76,168,130,0.1); border: 1px solid rgba(76,168,130,0.28);
  color: #a8d5c2; border-radius: 6px; padding: 2px 8px;
  font-size: 0.7rem; font-family: var(--ff-mono); display: inline-block; margin-left: 6px;
}}

/* Outcome table */
.outcome-table {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); overflow: hidden; margin-top: 0.75rem;
}}
.outcome-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.55rem 1rem; border-top: 1px solid var(--border);
}}
.outcome-row:first-child {{ border-top: none; }}

/* Sidebar brand */
.sidebar-brand {{
  padding: 0.5rem 0 1.25rem; border-bottom: 1px solid var(--border); margin-bottom: 0.75rem;
}}
.sidebar-brand-name {{
  font-family: var(--ff-display); font-weight: 900; font-size: 1.55rem;
  color: var(--gold); letter-spacing: -0.03em; line-height: 1; margin-bottom: 3px;
}}
.sidebar-brand-sub {{
  font-size: 0.68rem; color: var(--text-muted); font-family: var(--ff-mono);
  text-transform: uppercase; letter-spacing: 0.12em;
}}
.sidebar-legend {{
  font-size: 0.68rem; color: var(--text-muted); padding-top: 1rem;
  border-top: 1px solid var(--border); margin-top: auto; line-height: 1.8;
}}

/* Icon baseline — §7g */
.tempo-icon {{ display: inline-block; vertical-align: middle; flex-shrink: 0; }}

/* Skeleton shimmer — §7h */
@keyframes skeleton-shimmer {{
  0%   {{ background-position: 200% 0; }}
  100% {{ background-position: -200% 0; }}
}}
.skeleton {{
  background: linear-gradient(90deg,
    var(--surface-raised) 0%, var(--border) 50%, var(--surface-raised) 100%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s var(--ease-normal) infinite;
  border-radius: var(--radius-sm);
}}

/* ── Hero match card ─────────────────────────────────────────────────────
   Larger than a grid card: bigger flags (width=44), team names 1.3rem,
   taller prob bar, "Next kick-off" badge at top.                         */
.hero-card {{
  margin-bottom: 1.75rem;
}}
.hero-card .match-card-body {{
  padding: 1.35rem 1.6rem 1.4rem;
}}
.hero-team-name {{
  font-size: 1.3rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em !important;
}}
.hero-badge {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(232,184,75,0.08);
  border: 1px solid rgba(232,184,75,0.25);
  border-radius: 6px;
  padding: 2px 10px;
  font-family: var(--ff-mono);
  font-size: 0.62rem;
  color: var(--gold);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}}
.hero-card .prob-bar-track {{
  height: 36px;
}}

/* ── Chip filters — radio group restyled as pill chips ────────────────────
   Targets st.radio with horizontal=True. The radio circle is hidden;
   the label itself becomes the clickable pill.                            */
.filter-label {{
  font-family: var(--ff-mono);
  font-size: 0.6rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 0.75rem;
  margin-bottom: 0.3rem;
}}
/* Wrap the options in a flex row */
div[data-testid="stRadio"] > div[role="radiogroup"] {{
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: wrap !important;
  gap: 5px !important;
  align-items: center !important;
}}
/* Each option label becomes a pill chip */
div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
  display: inline-flex !important;
  align-items: center !important;
  cursor: pointer !important;
  background: var(--surface-raised) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 3px 12px !important;
  font-size: 0.73rem !important;
  font-family: var(--ff-mono) !important;
  color: var(--text-muted) !important;
  font-weight: 500 !important;
  letter-spacing: 0.03em !important;
  transition:
    background    var(--anim-fast) var(--ease-fast),
    border-color  var(--anim-fast) var(--ease-fast),
    color         var(--anim-fast) var(--ease-fast) !important;
  white-space: nowrap !important;
  min-height: 28px !important;
  user-select: none !important;
  line-height: 1 !important;
}}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
  background: var(--surface) !important;
  border-color: rgba(232,184,75,0.3) !important;
  color: var(--text) !important;
}}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {{
  background: rgba(232,184,75,0.1) !important;
  border-color: rgba(232,184,75,0.4) !important;
  color: var(--gold) !important;
  font-weight: 700 !important;
}}
/* Hide the radio circle dot — the pill is the affordance */
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {{
  display: none !important;
}}
div[data-testid="stRadio"] p {{
  font-size: 0.73rem !important;
  font-family: var(--ff-mono) !important;
  margin: 0 !important;
  color: inherit !important;
  line-height: 1 !important;
}}

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 768px) {{
  [data-testid="block-container"] {{
    padding-left:  max(0.75rem, env(safe-area-inset-left))  !important;
    padding-right: max(0.75rem, env(safe-area-inset-right)) !important;
  }}
  .page-header h1 {{ font-size: 1.5rem !important; }}
  .team-name {{ font-size: 0.85rem !important; }}
  .match-card-body {{ padding: 0.9rem 1rem; }}
  .match-teams {{ flex-direction: column; gap: 0.35rem; }}
  .team-block.away {{ flex-direction: row; text-align: left; }}
}}
/* ── 375px — single-column, no overflow ────────────────────────────────── */
@media (max-width: 375px) {{
  .team-name {{
    font-size: 0.8rem !important;
    white-space: normal !important;
    word-break: break-word !important;
  }}
  .match-chip {{
    font-size: 0.58rem !important;
    white-space: normal !important;
  }}
  .match-card-body {{ padding: 0.75rem 0.875rem; }}
  .hero-team-name {{ font-size: 1rem !important; }}
  /* Share card preview — scroll rather than break layout */
  .sc-card-scroll-wrap {{ overflow-x: auto; max-width: 100%; }}
}}
/* ── 320px — tightest supported viewport ───────────────────────────────── */
@media (max-width: 320px) {{
  [data-testid="stMainBlockContainer"] {{
    padding-left:  0.5rem !important;
    padding-right: 0.5rem !important;
  }}
  .team-name {{ font-size: 0.75rem !important; }}
  .page-header h1 {{ font-size: 1.25rem !important; }}
  .prob-bar-track {{ height: 24px !important; }}
  .prob-seg {{ font-size: 0.62rem !important; }}
}}

/* ── Reduced motion — §9 ────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }}
  .skeleton {{ animation: none; background: var(--surface-raised); }}
}}
"""


def inject(theme: _DarkPalette | _LightPalette = DARK) -> None:
    """
    Inject all Tempo CSS into the running Streamlit app.
    Call ONCE from app.py at startup, before any st.markdown calls.
    """
    import streamlit as st

    # Preconnect hints reduce font-loading latency before @import fires
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{_build_css(theme)}</style>", unsafe_allow_html=True)
