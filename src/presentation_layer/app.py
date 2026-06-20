"""
Tempo — Streamlit application entrypoint.

Run:  streamlit run src/presentation_layer/app.py

Layer boundary: NEVER import scikit-learn, xgboost, or any
Layer 2 training/model module from this file or any component it calls.
"""

import os
import sys
from pathlib import Path

# Add repo root to sys.path so 'src' is importable on Streamlit Cloud
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from dotenv import load_dotenv

from src.presentation_layer.theme import APP_NAME, DARK
from src.presentation_layer.styles import inject as inject_styles
from src.presentation_layer.charts.template import register_tempo_template
from src.presentation_layer.pages import today
from src.presentation_layer.pages import model_report
from src.presentation_layer.pages import match_detail
from src.presentation_layer.pages import match_space

load_dotenv()

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": f"{APP_NAME} — FIFA World Cup 2026 AI Predictor",
    },
)

# ── Single CSS injection + Plotly template registration ────────────────────────
# inject_styles() must be called ONCE before any st.markdown.
# register_tempo_template() makes template="tempo" available to all chart files.
inject_styles(theme=DARK)
register_tempo_template()


def _render_foundation_demo() -> None:
    """
    Throwaway validation page — confirm chrome is stripped, fonts are live,
    and the 'tempo' Plotly template reads broadcast-grade.
    Remove this page once Step 3+ UI overhaul pages are done.
    """
    import plotly.graph_objects as go
    from src.presentation_layer.icons import icon, icon_text

    st.markdown('<div class="accent-rail"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-header">'
        '<h1>Foundation pass</h1>'
        '<p class="subtitle">Visual base validation — chrome strip · fonts · Plotly template · icon system</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Token swatch row ──────────────────────────────────────────────────
    st.markdown('<div class="sec-heading">Design tokens — color</div>', unsafe_allow_html=True)
    swatches = [
        (DARK.WIN,           "Win #1FB479"),
        (DARK.DRAW,          "Draw #3E7BFA"),
        (DARK.LOSS,          "Loss #E4564A"),
        (DARK.GOLD,          "Gold #E8B84B"),
        (DARK.TEXT,          "Text #F4F1EA"),
        (DARK.SURFACE_RAISED,"Raised #1C1C21"),
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

    # ── Typography specimen ───────────────────────────────────────────────
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

    # ── Icons ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-heading">Icon system — Lucide SVG §7g</div>', unsafe_allow_html=True)
    icon_row = " ".join(
        f'<span title="{name}" style="margin-right:12px;">{icon(name, size=20, color=DARK.TEXT_MUTED)}</span>'
        for name in ["trending-up", "bar-chart-2", "target", "calendar", "filter",
                     "award", "globe", "refresh-cw", "check", "alert-triangle"]
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

    # ── Plotly template validation ────────────────────────────────────────
    st.markdown('<div class="sec-heading">Plotly template="tempo" — broadcast check</div>', unsafe_allow_html=True)

    teams = ["England", "Brazil", "France", "Argentina", "Spain"]
    p_home = [0.52, 0.45, 0.48, 0.55, 0.41]
    p_draw = [0.27, 0.30, 0.28, 0.24, 0.33]
    p_away = [0.21, 0.25, 0.24, 0.21, 0.26]

    fig = go.Figure(data=[
        go.Bar(name="Home Win", x=teams, y=p_home,
               marker_color=DARK.WIN,
               hovertemplate="<b>%{x}</b><br>Home Win: %{y:.0%}<extra></extra>"),
        go.Bar(name="Draw",     x=teams, y=p_draw,
               marker_color=DARK.DRAW,
               hovertemplate="<b>%{x}</b><br>Draw: %{y:.0%}<extra></extra>"),
        go.Bar(name="Away Win", x=teams, y=p_away,
               marker_color=DARK.LOSS,
               hovertemplate="<b>%{x}</b><br>Away Win: %{y:.0%}<extra></extra>"),
    ])
    fig.update_layout(
        template="tempo",
        barmode="stack",
        title_text="Next-match outcome distribution — synthetic validation data",
        yaxis=dict(tickformat=".0%", title="Probability"),
        xaxis=dict(title="Home team"),
        height=320,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Z-index tokens ────────────────────────────────────────────────────
    st.markdown('<div class="sec-heading">Z-index scale — §5d</div>', unsafe_allow_html=True)
    z_tokens = [
        ("--z-base",            "0",    "Default flow"),
        ("--z-sticky",          "100",  "Sticky headers"),
        ("--z-dropdown",        "200",  "Dropdowns / selects"),
        ("--z-modal-backdrop",  "300",  "Modal scrim"),
        ("--z-modal",           "400",  "Modal content"),
        ("--z-toast",           "500",  "Toast notifications"),
        ("--z-tooltip",         "600",  "Tooltips"),
    ]
    rows = "".join(
        f'<div class="outcome-row">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;color:{DARK.GOLD};">{var}</span>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;color:{DARK.TEXT_MUTED};">{val}</span>'
        f'<span style="font-size:0.75rem;color:{DARK.TEXT_MUTED};">{desc}</span>'
        f'</div>'
        for var, val, desc in z_tokens
    )
    st.markdown(f'<div class="outcome-table">{rows}</div>', unsafe_allow_html=True)

    st.markdown(
        f'<p class="data-stamp" style="margin-top:1.5rem;">'
        f'Foundation pass · styles.py consolidated · template="tempo" registered · icon system live</p>',
        unsafe_allow_html=True,
    )


# ── Sidebar navigation ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
<div class="sidebar-brand">
  <div class="sidebar-brand-name">{APP_NAME}</div>
  <div class="sidebar-brand-sub">WC 2026 · AI Predictor</div>
  <div style="height:3px;background:linear-gradient(90deg,
    var(--win) 0% 33.3%,var(--draw) 33.3% 66.6%,var(--loss) 66.6% 100%);
    border-radius:2px;margin-top:0.9rem;"></div>
</div>""", unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        options=["Predictions", "Match Space", "Match Detail", "Model Report", "Foundation"],
        label_visibility="collapsed",
    )

    st.markdown("""
<div class="sidebar-legend">
  <div style="margin-bottom:0.3rem;display:flex;gap:10px;flex-wrap:wrap;">
    <span><span style="color:var(--win);">■</span> Home Win</span>
    <span><span style="color:var(--draw);">■</span> Draw</span>
    <span><span style="color:var(--loss);">■</span> Away Win</span>
  </div>
  <div>Model: XGBoost + Isotonic calibration</div>
  <div>Data: martj42 · openfootball</div>
  <div>49,475 historical matches</div>
</div>""", unsafe_allow_html=True)

# ── Page routing ────────────────────────────────────────────────────────────
if page == "Predictions":
    today.render(theme=DARK)
elif page == "Match Space":
    match_space.render(theme=DARK)
elif page == "Match Detail":
    match_detail.render(theme=DARK)
elif page == "Model Report":
    model_report.render(theme=DARK)
elif page == "Foundation":
    _render_foundation_demo()
