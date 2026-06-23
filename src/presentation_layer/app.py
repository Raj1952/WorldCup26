"""
Tempo — Streamlit application entrypoint.

Run:  streamlit run src/presentation_layer/app.py

Navigation: fixed top-nav console (replaces Streamlit sidebar).
Routing:    st.query_params["page"] — URL-safe, bookmarkable, survives refresh.

Layer boundary: NEVER import scikit-learn, xgboost, or any
Layer 2 training/model module from this file or any component it calls.
"""

import sys
from pathlib import Path

# Add repo root to sys.path so 'src' is importable on Streamlit Cloud
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from dotenv import load_dotenv

from src.presentation_layer.theme import APP_NAME, DARK
from src.presentation_layer.styles import inject as inject_styles
from src.presentation_layer.charts.template import register_tempo_template
from src.presentation_layer.icons import icon
from src.presentation_layer.pages import today
from src.presentation_layer.pages import model_report
from src.presentation_layer.pages import match_detail
from src.presentation_layer.pages import match_space
from src.presentation_layer.pages import bracket
from src.presentation_layer.pages import share

load_dotenv()

import base64

def _icon_img(name: str, size: int = 16, color: str = "#A7A39B") -> str:
    """Base64 data URI <img> for a Lucide icon — survives DOMPurify (inline SVG does not)."""
    svg = icon(name, size=size, color=color)
    b64 = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{size}" height="{size}" alt="" aria-hidden="true" style="display:inline-block;vertical-align:middle;flex-shrink:0;">'

# ── Wordmark (loaded once at startup; SVG color replaced & base64 encoded for st.html) ──
_SVG_PATH = Path(__file__).resolve().parents[2] / "assets" / "tempo-wordmark.svg"
try:
    _RAW_WORDMARK_SVG = _SVG_PATH.read_text(encoding="utf-8").strip()
    # Replace currentColor with our signature gold #E8B84B so it renders properly in <img>
    _GOLD_WORDMARK_SVG = _RAW_WORDMARK_SVG.replace("currentColor", "#E8B84B")
    _WORDMARK_B64 = base64.b64encode(_GOLD_WORDMARK_SVG.encode("utf-8")).decode("utf-8")
    _WORDMARK_SVG_URI: str | None = f"data:image/svg+xml;base64,{_WORDMARK_B64}"
except FileNotFoundError:
    _WORDMARK_SVG_URI = None

# T-block: the two filled rects only — compact icon for ≤480px viewport.
# viewBox tightened to the bounding box of the rects (x 28-188, y 38-242).
_TBLOCK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="28 38 160 204"'
    ' fill="none" role="img" aria-label="Tempo">'
    '<g fill="currentColor" stroke="none">'
    '<rect x="30" y="40" width="156" height="50" rx="11"/>'
    '<rect x="83" y="40" width="50"  height="200" rx="11"/>'
    '</g></svg>'
)
_GOLD_TBLOCK_SVG = _TBLOCK_SVG.replace("currentColor", "#E8B84B")
_TBLOCK_B64 = base64.b64encode(_GOLD_TBLOCK_SVG.encode("utf-8")).decode("utf-8")
_TBLOCK_SVG_URI = f"data:image/svg+xml;base64,{_TBLOCK_B64}"

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",   # sidebar hidden — top-nav is the shell
    menu_items={"About": f"{APP_NAME} — FIFA World Cup 2026 AI Predictor"},
)

# ── Shared CSS + Plotly template (injected ONCE before any st.markdown) ─────
inject_styles(theme=DARK)
register_tempo_template()

# ── Route table ─────────────────────────────────────────────────────────────
# (route_key, lucide_icon_name, display_label, coming_soon)
_ROUTES = [
    ("predictions",  "zap",         "Predictions",  False),
    ("match-space",  "target",      "Match Space",  False),
    ("match-detail", "search",      "Match Detail", False),
    ("model-report", "bar-chart-2", "Model Report", False),
    ("bracket",      "trophy",      "Bracket",      False),
    ("share-card",   "share-2",     "Share Card",   False),
]
_VALID_PAGES = {r[0] for r in _ROUTES} | {"foundation"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_page() -> str:
    """Read current page from URL query param; default to predictions."""
    raw = st.query_params.get("page", "predictions")
    return raw if raw in _VALID_PAGES else "predictions"


def _nav_html(current_page: str) -> str:
    """Build the fixed broadcast-console nav bar as an HTML string."""
    # Desktop: full SVG wordmark. Mobile ≤480px: T-block icon only (CSS toggles).
    # Fallback to text "Tempo" when SVG not on disk (e.g. first run before assets/).
    if _WORDMARK_SVG_URI is not None:
        brand_inner = (
            f'<span class="tempo-brand-wordmark"><img src="{_WORDMARK_SVG_URI}" alt="Tempo" /></span>'
            f'<span class="tempo-brand-icon"><img src="{_TBLOCK_SVG_URI}" alt="Tempo icon" /></span>'
            f'<span class="tempo-brand-sub">WC26 · AI Predictor</span>'
        )
    else:
        brand_inner = (
            f'<span class="tempo-brand-name">{APP_NAME}</span>'
            f'<span class="tempo-brand-sub">WC26 · AI Predictor</span>'
        )

    links_html = ""
    for route, icon_name, label, soon in _ROUTES:
        active_class = " is-active" if current_page == route else ""
        aria_current = 'aria-current="page"' if current_page == route else ""
        soon_badge = '<span class="tempo-nav-soon">soon</span>' if soon else ""
        nav_icon = _icon_img(icon_name, size=16)
        links_html += (
            f'<li role="none">'
            f'<a href="?page={route}" class="tempo-nav-link{active_class}" '
            f'role="menuitem" {aria_current} aria-label="{label}">'
            f'{nav_icon}'
            f'<span class="tempo-nav-label">{label}</span>'
            f'{soon_badge}'
            f'</a></li>'
        )
    return f"""
<nav class="tempo-nav" role="navigation" aria-label="Tempo main navigation">
  <div class="tempo-nav-rail"></div>
  <div class="tempo-nav-inner">
    <a class="tempo-brand" href="?page=predictions" aria-label="Tempo — home">
      {brand_inner}
    </a>
    <ul class="tempo-nav-links" role="menubar" aria-label="Main pages">
      {links_html}
    </ul>
    <span class="tempo-nav-meta" aria-hidden="true">Updates daily · batch</span>
  </div>
</nav>
"""


# ── Page renderers ───────────────────────────────────────────────────────────

def _render_bracket_placeholder() -> None:
    """Stub for Bracket page — Monte Carlo simulator pending R6."""
    st.markdown(
        '<div class="page-header">'
        '<h1>Bracket &amp; Simulation</h1>'
        '<p class="subtitle">'
        'Monte Carlo tournament simulation — advancement odds &amp; road-to-final'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("""
<div class="no-data">
  <h3>Coming soon — R6</h3>
  <p>
    Once the group stage resolves, this page will show Monte Carlo advancement
    and title odds (50,000 runs · seed=42 · conditioned on live standings).
  </p>
  <p><code>python pipelines/refresh.py --monte-carlo</code></p>
  <p style="margin-top:1rem;font-size:0.75rem;color:var(--text-muted);">
    Knockout fixtures display only after concrete teams are known — per §0.5/§3.
  </p>
</div>""", unsafe_allow_html=True)


def _render_foundation_demo() -> None:
    """Throwaway validation page — confirm CSS, template, icons are live."""
    import plotly.graph_objects as go
    from src.presentation_layer.icons import icon_text

    st.markdown(
        '<div class="page-header">'
        '<h1>Foundation pass</h1>'
        '<p class="subtitle">'
        'Visual base validation — chrome strip · fonts · Plotly template · icon system'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-heading">Design tokens — color</div>', unsafe_allow_html=True)
    swatches = [
        (DARK.WIN,            "Win #4CA882"),
        (DARK.DRAW,           "Draw #6B8ABF"),
        (DARK.LOSS,           "Loss #C9645C"),
        (DARK.GOLD,           "Gold #E8B84B"),
        (DARK.TEXT,           "Text #F4F1EA"),
        (DARK.SURFACE_RAISED, "Raised #1C1C21"),
    ]
    cols = st.columns(len(swatches))
    for col, (hex_, label) in zip(cols, swatches):
        with col:
            st.markdown(
                f'<div style="background:{hex_};height:48px;border-radius:8px;'
                f'border:1px solid {DARK.BORDER};margin-bottom:6px;"></div>'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;'
                f'color:{DARK.TEXT_MUTED};">{label}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-heading">Typography</div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-family:\'Archivo\',sans-serif;font-weight:900;font-size:2rem;'
        f'letter-spacing:-0.02em;color:{DARK.TEXT};margin:0 0 4px;">Archivo 900 — Display</p>'
        f'<p style="font-family:\'Inter\',sans-serif;font-size:1rem;color:{DARK.TEXT_MUTED};margin:0 0 4px;">'
        f'Inter 400 — Body. Prediction-first, broadcast-grade, earned credibility.</p>'
        f'<p style="font-family:\'JetBrains Mono\',monospace;font-size:0.85rem;color:{DARK.GOLD};margin:0;">'
        f'JetBrains Mono — 52% Home · 28% Draw · 20% Away</p>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-heading">Icon system — Lucide SVG §7g</div>', unsafe_allow_html=True)
    icon_names = ["trending-up", "bar-chart-2", "target", "calendar", "filter",
                  "award", "globe", "refresh-cw", "check", "alert-triangle"]
    icon_row = "".join(
        f'<span title="{n}" style="margin-right:12px;">'
        f'{icon(n, size=20, color=DARK.TEXT_MUTED)}</span>'
        for n in icon_names
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;padding:8px 0;">'
        f'{icon_row}</div>'
        f'<div style="margin-top:8px;">'
        f'{icon_text("trending-up", "RPS improving", size=16, color=DARK.WIN, bold=True)}'
        f'&nbsp;&nbsp;'
        f'{icon_text("alert-triangle", "Model not trained", size=16, color=DARK.LOSS)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-heading">Plotly template="tempo" — broadcast check</div>', unsafe_allow_html=True)
    teams   = ["England", "Brazil", "France", "Argentina", "Spain"]
    p_home  = [0.52, 0.45, 0.48, 0.55, 0.41]
    p_draw  = [0.27, 0.30, 0.28, 0.24, 0.33]
    p_away  = [0.21, 0.25, 0.24, 0.21, 0.26]
    fig = go.Figure(data=[
        go.Bar(name="Home Win", x=teams, y=p_home, marker_color=DARK.WIN,
               hovertemplate="<b>%{x}</b><br>Home Win: %{y:.0%}<extra></extra>"),
        go.Bar(name="Draw",     x=teams, y=p_draw, marker_color=DARK.DRAW,
               hovertemplate="<b>%{x}</b><br>Draw: %{y:.0%}<extra></extra>"),
        go.Bar(name="Away Win", x=teams, y=p_away, marker_color=DARK.LOSS,
               hovertemplate="<b>%{x}</b><br>Away Win: %{y:.0%}<extra></extra>"),
    ])
    fig.update_layout(
        template="tempo",
        barmode="stack",
        title_text="Outcome distribution — synthetic validation data",
        yaxis=dict(tickformat=".0%", title="Probability"),
        xaxis=dict(title="Home team"),
        height=300,
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        '<p class="data-stamp" style="margin-top:1.5rem;">'
        'Foundation pass · CSS consolidated · template="tempo" · icon system live</p>',
        unsafe_allow_html=True,
    )


# ── Render nav + route ───────────────────────────────────────────────────────

page = _get_page()
st.html(_nav_html(page))

if page == "predictions":
    today.render(theme=DARK)
elif page == "match-space":
    match_space.render(theme=DARK)
elif page == "match-detail":
    match_detail.render(theme=DARK)
elif page == "model-report":
    model_report.render(theme=DARK)
elif page == "bracket":
    bracket.render(theme=DARK)
elif page == "share-card":
    share.render(theme=DARK)
elif page == "foundation":
    _render_foundation_demo()
