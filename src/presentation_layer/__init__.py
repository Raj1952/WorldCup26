"""
presentation_layer — Layer 3 of Tempo.

Responsibilities: Streamlit app, Plotly charts, design system (theme.py),
reusable components, per-page modules.

Layer boundary: this layer NEVER imports scikit-learn, xgboost, or shap.
It reads only predictions.parquet and Layer 1 standing tables.
"""
