"""Schema validation for ingested data using pydantic v2."""

from __future__ import annotations

__all__ = ["validate_match_row", "MatchRow", "FixtureRow", "PredictionRow"]

from datetime import date as Date
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class MatchRow(BaseModel):
    match_id: str
    date: str           # ISO-8601 YYYY-MM-DD
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    outcome: str        # 'home' | 'draw' | 'away'
    tournament: str
    is_neutral: bool
    stage: str          # 'group', 'knockout', 'friendly', etc.
    source: str         # 'historical' | 'openfootball' | 'api' | 'manual'

    @field_validator("outcome")
    @classmethod
    def outcome_valid(cls, v: str) -> str:
        if v not in ("home", "draw", "away"):
            raise ValueError(f"outcome must be home/draw/away, got '{v}'")
        return v

    @field_validator("home_score", "away_score")
    @classmethod
    def score_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("score cannot be negative")
        return v

    @model_validator(mode="after")
    def teams_differ(self) -> "MatchRow":
        if self.home_team == self.away_team:
            raise ValueError("home_team and away_team must differ")
        return self


class FixtureRow(BaseModel):
    match_id: str
    date: str
    kickoff_time: str   # HH:MM UTC
    home_team: str
    away_team: str
    group_label: str    # 'A'…'L', 'R32', 'R16', 'QF', 'SF', '3P', 'F'
    venue: str
    city: str
    status: str         # 'scheduled' | 'played' | 'cancelled'
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    source: str = "openfootball"

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("scheduled", "played", "cancelled"):
            raise ValueError(f"invalid status: {v}")
        return v


class PredictionRow(BaseModel):
    match_id: str
    date: str
    home_team: str
    away_team: str
    p_home: float
    p_draw: float
    p_away: float
    top_factors: list[dict]   # [{"label": str, "direction": str, "impact": float}]
    model_version: str
    created_at: str

    @model_validator(mode="after")
    def probs_sum_to_one(self) -> "PredictionRow":
        total = self.p_home + self.p_draw + self.p_away
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"probabilities must sum to ~1.0, got {total:.4f}")
        return self


def validate_match_row(row: dict) -> MatchRow:
    return MatchRow(**row)


def derive_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"
