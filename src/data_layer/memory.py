"""
Supermemory integration — persistent long-term memory for Tempo.

Persists predictions, model events, and match results as searchable documents.
All calls are fire-and-forget: a failure never blocks the pipeline.

Container tags (one scope per concern):
  tempo-wc2026-predictions  — one doc per upcoming match prediction batch
  tempo-wc2026-model        — one doc per model training/promotion event
  tempo-wc2026-results      — one doc per real result ingested

Layer boundary: Layer 1 only. Never import streamlit or plotly here.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

_TAG_PREDICTIONS = "tempo-wc2026-predictions"
_TAG_MODEL       = "tempo-wc2026-model"
_TAG_RESULTS     = "tempo-wc2026-results"


def _safe_id(text: str) -> str:
    """Normalise to ASCII and strip characters not allowed in Supermemory custom_id."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9\-_:]", "_", ascii_text)


def _client():
    """Return an authenticated Supermemory client, or None if unavailable."""
    try:
        from supermemory import Supermemory
    except ImportError:
        logger.warning("supermemory not installed — run: pip install supermemory")
        return None

    key = os.environ.get("SUPERMEMORY_API_KEY", "").strip()
    if not key:
        logger.debug("SUPERMEMORY_API_KEY not set — memory persistence skipped.")
        return None

    return Supermemory(api_key=key)


# ── Persist ────────────────────────────────────────────────────────────────

def persist_predictions(predictions_df) -> int:
    """
    Store each upcoming-match prediction as a searchable memory document.
    Returns number of documents successfully stored (0 on any failure).
    """
    client = _client()
    if client is None:
        return 0

    stored = 0
    for _, row in predictions_df.iterrows():
        try:
            home    = str(row["home_team"])
            away    = str(row["away_team"])
            date    = str(row["date"])
            group   = str(row.get("group_label", "WC"))
            ph      = float(row["p_home"])
            pd_     = float(row["p_draw"])
            pa      = float(row["p_away"])
            model_v = str(row.get("model_version", ""))[:32]
            created = str(row.get("created_at", ""))[:19]

            best = max(ph, pd_, pa)
            if best == ph:
                verdict = f"Home win ({home}) {ph:.1%}"
            elif best == pa:
                verdict = f"Away win ({away}) {pa:.1%}"
            else:
                verdict = f"Draw {pd_:.1%}"

            factors = row.get("top_factors", [])
            if isinstance(factors, str):
                try:
                    factors = json.loads(factors)
                except Exception:
                    factors = []
            factors_txt = " | ".join(
                f"{'up' if f.get('direction', '+') == '+' else 'down'} {f.get('label', '')}"
                for f in factors[:3]
            ) or "none"

            content = (
                f"WC2026 prediction: {home} vs {away}\n"
                f"Group/stage: {group} | Date: {date}\n"
                f"Verdict: {verdict}\n"
                f"Probabilities: Home {ph:.1%} | Draw {pd_:.1%} | Away {pa:.1%}\n"
                f"Key factors: {factors_txt}\n"
                f"Model: {model_v} | Generated: {created}"
            )

            client.documents.add(
                content=content,
                container_tag=_TAG_PREDICTIONS,
                custom_id=_safe_id(f"pred-{home}-{away}-{date}"),
                metadata={
                    "home": home, "away": away,
                    "date": date, "group": group,
                    "p_home": ph, "p_draw": pd_, "p_away": pa,
                    "model_version": model_v,
                },
            )
            stored += 1

        except Exception as exc:
            logger.warning(
                "Supermemory: failed to store prediction %s vs %s — %s",
                row.get("home_team", "?"), row.get("away_team", "?"), exc,
            )

    if stored:
        logger.info("Supermemory: stored %d prediction documents.", stored)
    return stored


def persist_model_event(registry_entry: dict, rps: Optional[float] = None) -> bool:
    """Log a model training/promotion event for long-term tracking."""
    client = _client()
    if client is None:
        return False

    try:
        version    = registry_entry.get("version", "unknown")
        model_type = registry_entry.get("model_type", "")
        ll         = registry_entry.get("log_loss_test", 0)
        acc        = registry_entry.get("accuracy_test", 0)
        brier      = registry_entry.get("brier_test", 0)
        n_train    = registry_entry.get("n_train", 0)
        n_test     = registry_entry.get("n_test", 0)
        created    = str(registry_entry.get("created_at", ""))[:19]
        rps_str    = f"{rps:.4f}" if rps is not None else "not computed"

        content = (
            f"Tempo model event: {model_type}\n"
            f"Version: {version} | Date: {created}\n"
            f"RPS: {rps_str} | Log-loss: {ll:.4f} | Accuracy: {acc:.1%} | Brier: {brier:.4f}\n"
            f"Train samples: {n_train:,} | Test samples: {n_test:,}"
        )

        client.documents.add(
            content=content,
            container_tag=_TAG_MODEL,
            custom_id=f"model-{version}",
            metadata={
                "version": version, "model_type": model_type,
                "rps": rps, "log_loss": ll, "accuracy": acc,
                "n_train": n_train, "n_test": n_test,
                "created_at": created,
            },
        )
        logger.info("Supermemory: stored model event %s.", version)
        return True

    except Exception as exc:
        logger.warning("Supermemory: model event failed — %s", exc)
        return False


def persist_result(home: str, away: str, date: str,
                   home_score: int, away_score: int,
                   predicted_p_home: Optional[float] = None,
                   predicted_p_draw: Optional[float] = None,
                   predicted_p_away: Optional[float] = None) -> bool:
    """Log a real match result, with our prediction alongside it if available."""
    client = _client()
    if client is None:
        return False

    try:
        if home_score > away_score:
            outcome = "Home win"
        elif home_score < away_score:
            outcome = "Away win"
        else:
            outcome = "Draw"

        pred_block = ""
        if predicted_p_home is not None:
            best = max(predicted_p_home, predicted_p_draw or 0, predicted_p_away or 0)
            if best == predicted_p_home:
                our_call = f"Home win {predicted_p_home:.1%}"
            elif best == predicted_p_away:
                our_call = f"Away win {predicted_p_away:.1%}"
            else:
                our_call = f"Draw {predicted_p_draw:.1%}"
            correct = (
                (outcome == "Home win" and best == predicted_p_home) or
                (outcome == "Away win" and best == predicted_p_away) or
                (outcome == "Draw"     and best == predicted_p_draw)
            )
            pred_block = (
                f"\nOur prediction: {our_call} — "
                f"{'CORRECT' if correct else 'WRONG'}"
            )

        content = (
            f"WC2026 result: {home} vs {away} | Date: {date}\n"
            f"Score: {home_score}-{away_score} | Outcome: {outcome}"
            f"{pred_block}"
        )

        client.documents.add(
            content=content,
            container_tag=_TAG_RESULTS,
            custom_id=_safe_id(f"result-{home}-{away}-{date}"),
            metadata={
                "home": home, "away": away, "date": date,
                "home_score": home_score, "away_score": away_score,
                "outcome": outcome,
            },
        )
        logger.info("Supermemory: stored result %s vs %s (%s).", home, away, outcome)
        return True

    except Exception as exc:
        logger.warning("Supermemory: result storage failed — %s", exc)
        return False


# ── Recall ─────────────────────────────────────────────────────────────────

def search_predictions(query: str, limit: int = 5) -> list[dict]:
    """
    Search stored predictions by free text (team name, date, outcome, etc.).
    Returns list of {content, score} dicts; empty list on any failure.
    """
    client = _client()
    if client is None:
        return []

    try:
        result = client.search.execute(
            q=query,
            container_tag=_TAG_PREDICTIONS,
            limit=limit,
            rerank=True,
        )
        return [
            {"content": r.content, "score": getattr(r, "score", 0.0)}
            for r in (result.results or [])
        ]
    except Exception as exc:
        logger.warning("Supermemory search failed — %s", exc)
        return []
