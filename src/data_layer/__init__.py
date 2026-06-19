"""
data_layer — Layer 1 of Tempo.

Responsibilities: ingest historical + live data, validate schema,
normalize team names via alias map, persist to tempo.db + Parquet,
build feature tables for the intelligence layer.

Layer boundary: this layer NEVER imports streamlit or plotly.
"""
