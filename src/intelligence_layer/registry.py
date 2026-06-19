"""
Model promotion registry.

A candidate model replaces the live model only if its log-loss on the
held-out test set does not regress (i.e., is lower or within tolerance).
Registry state is stored in artifacts/models/registry.json.
Models are pickled to artifacts/models/.
"""

from __future__ import annotations

__all__ = ["promote_if_better", "get_live_model", "list_registry"]

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path("artifacts/models/registry.json")
MODELS_DIR = Path("artifacts/models")
_LOG_LOSS_TOLERANCE = 0.002   # new model may be up to this much worse and still promote


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except Exception:
            pass
    return {"live_version": None, "models": []}


def _save_registry(reg: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=2))


def promote_if_better(model, metrics: dict, model_type: str = "xgboost") -> bool:
    """
    Pickle the model and register it as live if it improves on the current live model.

    metrics must contain: log_loss, accuracy, brier, n_train, n_test.
    Returns True if promoted, False if rejected.
    """
    reg = _load_registry()
    version = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{model_type}"

    # Check against current live model
    live_ll = None
    for entry in reg["models"]:
        if entry["version"] == reg.get("live_version"):
            live_ll = entry.get("log_loss_test")
            break

    new_ll = metrics.get("log_loss", float("inf"))
    should_promote = (
        live_ll is None                          # no live model yet
        or new_ll <= live_ll + _LOG_LOSS_TOLERANCE  # not regressing
    )

    if should_promote:
        model_path = MODELS_DIR / f"{version}.pkl"
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        entry = {
            "version": version,
            "model_type": model_type,
            "model_path": str(model_path),
            "log_loss_test": new_ll,
            "accuracy_test": metrics.get("accuracy"),
            "brier_test": metrics.get("brier"),
            "n_train": metrics.get("n_train"),
            "n_test": metrics.get("n_test"),
            "created_at": datetime.utcnow().isoformat(),
        }
        reg["models"].append(entry)
        reg["live_version"] = version
        _save_registry(reg)
        logger.info("Promoted %s  log_loss=%.4f", version, new_ll)
        return True
    else:
        logger.info(
            "Rejected %s  log_loss=%.4f >= live=%.4f",
            version, new_ll, live_ll,
        )
        return False


def get_live_model():
    """Load and return the currently promoted live model, or None."""
    reg = _load_registry()
    live_v = reg.get("live_version")
    if not live_v:
        return None, None

    for entry in reg["models"]:
        if entry["version"] == live_v:
            try:
                with open(entry["model_path"], "rb") as f:
                    model = pickle.load(f)
                return model, entry
            except Exception as exc:
                logger.error("Failed to load live model: %s", exc)
                return None, None
    return None, None


def list_registry() -> list[dict]:
    """Return all model registry entries."""
    return _load_registry().get("models", [])
