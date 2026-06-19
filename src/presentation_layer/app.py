"""
Tempo — Streamlit application entrypoint.

Run:  streamlit run src/presentation_layer/app.py

Layer boundary: NEVER import scikit-learn, xgboost, shap, or any
Layer 2 training/model module from this file or any component it calls.
"""

import os

import streamlit as st
from dotenv import load_dotenv

from src.presentation_layer.theme import APP_NAME, DARK, apply_global_css
from src.presentation_layer.styles import inject as inject_styles
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

apply_global_css(theme=DARK)
inject_styles()

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
        options=["Predictions", "Match Space", "Match Detail", "Model Report"],
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

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "Predictions":
    today.render(theme=DARK)
elif page == "Match Space":
    match_space.render(theme=DARK)
elif page == "Match Detail":
    match_detail.render(theme=DARK)
elif page == "Model Report":
    model_report.render(theme=DARK)
