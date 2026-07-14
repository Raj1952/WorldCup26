"""
Tempo heartbeat pipeline.

Usage:  python pipelines/refresh.py

Sequence:
  1. Ingest historical results (martj42 dataset)
  2. Ingest live WC2026 fixtures + results (openfootball / football-data.org / manual)
  3. Build feature tables (Elo + rolling stats)
  4. Train baseline model
  5. Train XGBoost model; calibrate; promote if better than baseline
  6. Generate predictions.parquet for all upcoming matches

Idempotent: safe to re-run at any time with no side effects beyond writing
fresher data to tempo.db and predictions.parquet.
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root on path when run as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("refresh")

DB_PATH = "data/tempo.db"


def _step(label: str):
    logger.info("▶  %s", label)
    return time.time()


def _done(label: str, t0: float):
    logger.info("✓  %s  (%.1fs)", label, time.time() - t0)


def main() -> None:
    wall_start = time.time()
    logger.info("═" * 60)
    logger.info("Tempo refresh pipeline  —  %s", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("═" * 60)

    # ── Step 1: Historical ingest ─────────────────────────────────────────
    t = _step("Ingest historical results")
    from src.data_layer.ingest_historical import ingest_historical
    n_hist = ingest_historical(db_path=DB_PATH)
    _done(f"Historical: {n_hist} new rows", t)

    # ── Step 2: Live ingest ───────────────────────────────────────────────
    t = _step("Ingest live WC2026 data")
    from src.data_layer.ingest_live import ingest_live
    n_live = ingest_live(db_path=DB_PATH)
    _done(f"Live fixtures: {n_live} upserted", t)

    # ── Step 2.1: Warn on unresolved drawn KO matches ─────────────────────
    try:
        import sqlite3 as _sq3
        import pandas as _pd
        _conn = _sq3.connect(DB_PATH)
        _draws = _pd.read_sql(
            "SELECT date, home_team, away_team, home_score, away_score "
            "FROM wc2026_fixtures "
            "WHERE home_score IS NOT NULL AND home_score = away_score "
            "  AND group_label NOT IN ('A','B','C','D','E','F','G','H','I','J','K','L')",
            _conn,
        )
        _conn.close()
        if not _draws.empty:
            _man_path = Path("data/manual_results.csv")
            _resolved: set = set()
            if _man_path.exists():
                _man_df = _pd.read_csv(_man_path)
                if "knockout_winner" in _man_df.columns:
                    for _, _r in _man_df[_man_df["knockout_winner"].notna()].iterrows():
                        _resolved.add((str(_r["date"]), str(_r["home_team"]), str(_r["away_team"])))
            for _, _r in _draws.iterrows():
                _key = (str(_r["date"]), str(_r["home_team"]), str(_r["away_team"]))
                if _key not in _resolved:
                    logger.warning(
                        "PENALTY UNRESOLVED: %s vs %s on %s (%s-%s) — "
                        "add knockout_winner to data/manual_results.csv",
                        _r["home_team"], _r["away_team"], _r["date"],
                        int(_r["home_score"]), int(_r["away_score"]),
                    )
    except Exception as _exc:
        logger.debug("Penalty-draw check failed: %s", _exc)

    # ── Step 2.5: Archive settled predictions ─────────────────────────────
    # Runs HERE — after results land in DB but before predictions.parquet is
    # overwritten with fresh upcoming matches.  Idempotent: skips known IDs.
    t = _step("Private prediction-vs-result archive")
    try:
        from pipelines.archive_results import run_archive
        n_archived = run_archive(db_path=DB_PATH)
        if n_archived:
            logger.info("  %d new prediction outcomes archived to artifacts/private/", n_archived)
        else:
            logger.info("  No new completed predictions to archive (skipped)")
    except Exception as exc:
        logger.warning("Archive step failed (non-fatal): %s", exc)
    _done("Archive", t)

    # ── Step 3: Feature tables ────────────────────────────────────────────
    t = _step("Build feature tables (Elo + rolling stats)")
    from src.data_layer.build_features import build_features
    build_features(db_path=DB_PATH)
    _done("Feature tables", t)

    # ── Step 4: Baseline model ────────────────────────────────────────────
    t = _step("Train baseline (Elo-logistic)")
    from src.intelligence_layer.train import train_baseline, train_xgboost
    from src.intelligence_layer.calibrate import calibrate_model
    from src.intelligence_layer.registry import promote_if_better
    from src.intelligence_layer.features import build_feature_matrix

    try:
        baseline_result = train_baseline(db_path=DB_PATH)
        logger.info(
            "  Baseline log-loss: %.4f (test)  accuracy: %.3f",
            baseline_result.log_loss_test, baseline_result.accuracy_test,
        )
        promote_if_better(
            baseline_result.model,
            {
                "log_loss": baseline_result.log_loss_test,
                "accuracy": baseline_result.accuracy_test,
                "brier": baseline_result.brier_test,
                "n_train": baseline_result.n_train,
                "n_test": baseline_result.n_test,
            },
            model_type="baseline",
        )
    except Exception as exc:
        logger.error("Baseline training failed: %s", exc)
    _done("Baseline model", t)

    # ── Step 5: XGBoost model ─────────────────────────────────────────────
    t = _step("Train XGBoost model")
    try:
        xgb_result = train_xgboost(db_path=DB_PATH)
        logger.info(
            "  XGBoost log-loss: %.4f (test)  accuracy: %.3f",
            xgb_result.log_loss_test, xgb_result.accuracy_test,
        )

        # Three-way chronological split: fit isotonic on the CALIBRATION slice,
        # score on the untouched FROZEN TEST slice. Fitting and scoring on the
        # same rows made the calibrated model always look better than it is.
        from src.intelligence_layer.train import evaluate_model, time_split
        X_all, y_all, meta = build_feature_matrix(db_path=DB_PATH, exclude_friendlies=True)
        _X_tr, _y_tr, X_cal, y_cal, X_test, y_test = time_split(X_all, y_all, meta)

        calibrated = calibrate_model(xgb_result.model, X_cal, y_cal)

        cal_metrics = evaluate_model(calibrated, X_test, y_test)
        logger.info("  Calibrated log-loss (frozen test): %.4f", cal_metrics["log_loss"])

        promote_if_better(
            calibrated,
            {
                "log_loss": cal_metrics["log_loss"],
                "accuracy": cal_metrics["accuracy"],
                "brier": cal_metrics["brier"],
                "n_train": xgb_result.n_train,
                "n_test": xgb_result.n_test,
            },
            model_type="xgboost_calibrated",
        )
    except Exception as exc:
        logger.error("XGBoost training failed: %s", exc)
    _done("XGBoost model", t)

    # ── Step 6: Store metrics to DB ───────────────────────────────────────
    try:
        import sqlite3, json
        from src.intelligence_layer.registry import list_registry
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                version TEXT PRIMARY KEY,
                model_type TEXT,
                log_loss_test REAL,
                accuracy_test REAL,
                brier_test REAL,
                n_train INTEGER,
                n_test INTEGER,
                feature_importances TEXT,
                created_at TEXT
            )
        """)
        for entry in list_registry():
            conn.execute("""
                INSERT OR REPLACE INTO model_metrics
                (version,model_type,log_loss_test,accuracy_test,brier_test,n_train,n_test,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                entry.get("version"), entry.get("model_type"),
                entry.get("log_loss_test"), entry.get("accuracy_test"),
                entry.get("brier_test"), entry.get("n_train"), entry.get("n_test"),
                entry.get("created_at"),
            ))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Metrics write failed: %s", exc)

    # ── Step 7: Predictions ───────────────────────────────────────────────
    t = _step("Generate predictions for upcoming matches")
    preds = None
    try:
        from src.intelligence_layer.predict import predict_upcoming
        preds = predict_upcoming(db_path=DB_PATH)
        if not preds.empty:
            logger.info("  %d predictions written to predictions.parquet", len(preds))
        else:
            logger.warning("  No predictions generated (check fixtures and model)")
    except Exception as exc:
        logger.error("Prediction failed: %s", exc)
    _done("Predictions", t)

    # ── Step 8: Supermemory — persist predictions + latest model event ────
    t = _step("Persist to Supermemory (long-term memory)")
    try:
        from src.data_layer.memory import persist_predictions, persist_model_event
        from src.intelligence_layer.registry import list_registry

        # Load RPS if available
        rps = None
        try:
            import pandas as pd
            summary_path = Path("artifacts/reports/holdout_summary.parquet")
            if summary_path.exists():
                rps = float(pd.read_parquet(summary_path).iloc[0]["rps_test"])
        except Exception:
            pass

        # Persist latest model event
        registry = list_registry()
        if registry:
            persist_model_event(registry[-1], rps=rps)

        # Persist this batch of predictions
        if preds is not None and not preds.empty:
            n_stored = persist_predictions(preds)
            logger.info("  %d prediction documents stored in Supermemory.", n_stored)
        else:
            logger.info("  No predictions to persist.")

    except Exception as exc:
        logger.warning("Supermemory step failed (non-fatal): %s", exc)
    _done("Supermemory", t)

    logger.info("═" * 60)
    logger.info("Pipeline complete in %.1fs", time.time() - wall_start)
    logger.info("═" * 60)


if __name__ == "__main__":
    main()
