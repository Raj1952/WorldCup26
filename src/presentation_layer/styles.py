"""
Tempo — Streamlit chrome-strip + font wiring.

Call inject() once at app startup (before any st.markdown calls).
Responsibility split:
  styles.py  — infrastructure: font loading (@font-face), chrome removal, padding reset
  theme.py   — brand: design tokens (CSS custom properties), component styles

Layer boundary: this file may import streamlit (it IS Layer 3 presentation).
Never import scikit-learn, xgboost, or any Layer 2 module here.
"""

from __future__ import annotations

_FONT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800;900&family=Inter:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;600&display=swap');
"""

# Every selector here has been verified against Streamlit 1.30-1.45.
# Two-layer approach: config.toml sets toolbarMode=minimal (framework level),
# CSS below catches any residual elements that survive the config flag.
_CHROME_CSS = """
/* ── Hamburger menu (top-left ≡ icon) ────────────────────────────── */
#MainMenu                               { display: none !important; }

/* ── "Made with Streamlit" footer ────────────────────────────────── */
footer                                  { display: none !important; }
footer[data-testid="stFooter"]          { display: none !important; }

/* ── Top toolbar: Deploy button + kebab ──────────────────────────── */
[data-testid="stToolbar"]               { display: none !important; }
[data-testid="stToolbarActions"]        { display: none !important; }
[data-testid="stDeployButton"]          { display: none !important; }

/* ── Rainbow decoration stripe (top of page) ─────────────────────── */
[data-testid="stDecoration"]            { display: none !important; }

/* ── Full header bar — hide it; sidebar nav replaces the function ── */
[data-testid="stHeader"]                { display: none !important; }

/* ── Reclaim the gap the hidden header left behind ───────────────── */
/* Streamlit adds top padding equal to the header height; zero it out */
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="block-container"],
.block-container                        { padding-top: 1.5rem !important; }

/* ── Bottom padding: give content room to breathe ────────────────── */
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
.block-container                        { padding-bottom: 3rem !important; }

/* ── Max content width ───────────────────────────────────────────── */
[data-testid="block-container"],
.block-container                        { max-width: 1400px !important; }

/* ── Side gutters on the main area ───────────────────────────────── */
[data-testid="stMainBlockContainer"]    {
    padding-left:  2rem !important;
    padding-right: 2rem !important;
}

/* ── Remove Streamlit's default blank-page background flash ─────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0B0B0D !important;
}
"""

# Font-family assignments: applied early so browser doesn't FOUT on first paint.
_FONT_APPLY_CSS = """
html, body,
.stApp, .stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 16px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Display / heading weight — Archivo */
h1, h2, h3, h4, h5, h6,
.page-header h1,
.sidebar-brand-name,
.sec-heading,
.team-name {
    font-family: 'Archivo', sans-serif !important;
}

/* Monospace — JetBrains Mono with tabular figures */
code, pre,
[data-testid="stMetricValue"],
.prob-seg,
.match-chip,
.data-stamp,
.sidebar-brand-sub,
.favored-chip,
.sidebar-legend {
    font-family: 'JetBrains Mono', monospace !important;
    font-variant-numeric: tabular-nums !important;
}
"""

_MOBILE_CSS = """
/* ── Mobile-first adjustments (375px breakpoint) ─────────────────── */
@media (max-width: 480px) {
    [data-testid="stMainBlockContainer"],
    [data-testid="block-container"] {
        padding-left:  0.75rem !important;
        padding-right: 0.75rem !important;
        /* Respect iOS safe-area insets */
        padding-left:  max(0.75rem, env(safe-area-inset-left))  !important;
        padding-right: max(0.75rem, env(safe-area-inset-right)) !important;
    }
}

/* ── Reduced motion ───────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration:        0.01ms !important;
        animation-iteration-count: 1      !important;
        transition-duration:       0.01ms !important;
        scroll-behavior:           auto   !important;
    }
}
"""


def inject() -> None:
    """
    Inject font @import + chrome-strip CSS into the running Streamlit app.
    Call once from app.py before apply_global_css().
    """
    import streamlit as st

    # 1. Font preconnect hints — reduces latency before @import fires
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        unsafe_allow_html=True,
    )

    # 2. Font @import + chrome strip + font-family assignments, one <style> block
    full_css = _FONT_CSS + _CHROME_CSS + _FONT_APPLY_CSS + _MOBILE_CSS
    st.markdown(f"<style>{full_css}</style>", unsafe_allow_html=True)
