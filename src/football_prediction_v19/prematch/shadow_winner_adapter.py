"""Frozen MODEL_D primary-plus-rating prospective shadow adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2180_dynamic_rating import build_rating_features, candidate_configs
from football_prediction_v19.analysis.v2180_meta_winner import fit_meta_model, meta_features, predict_meta_model
from football_prediction_v19.analysis.v2180_winner_validation import prepare_challenger_dataset
from football_prediction_v19.prematch.input_schema import MatchInput


MODEL_NAME = "PRIMARY_PLUS_RATING_META_V2182"
MODEL_VERSION = "v2.18.2"
MODEL_ROLE = "SHADOW_WINNER_CHALLENGER"
FROZEN_RATING_CONFIG = "ELO_GOAL_DIFFERENCE_K30_HA60_S20"
FROZEN_META_C = 1.0
KNOWN_LIMITATIONS = ["DRAW_RECALL_LOW", "DRAW_TOP_PREDICTIONS_REQUIRE_MONITORING"]
DEFAULT_ARTIFACT = "models/primary_plus_rating_meta_v2182.joblib"
DEFAULT_MANIFEST = "models/primary_plus_rating_meta_v2182_manifest.json"


def train_frozen_shadow_artifact(project_root: str | Path, artifact_path: str | Path | None = None) -> dict:
    root = Path(project_root)
    artifact = Path(artifact_path) if artifact_path else root / DEFAULT_ARTIFACT
    rows = prepare_challenger_dataset(root)
    slim = rows[[
        "competition", "season", "match_date", "home_team", "away_team",
        "actual_home_goals", "actual_away_goals", "actual_result",
    ]]
    config = next(item for item in candidate_configs() if item["config_name"] == FROZEN_RATING_CONFIG)
    rating = build_rating_features(slim, config)
    for column in (
        "rating_home_probability", "rating_draw_probability", "rating_away_probability",
        "rating_difference", "rating_home_advantage", "rating_momentum_last5",
        "rating_momentum_last10", "rating_uncertainty", "history_count",
    ):
        rows[column] = rating[column].to_numpy()
    hierarchy_placeholder = rows[[
        "base_home_probability", "base_draw_probability", "base_away_probability"
    ]].to_numpy()
    all_meta = meta_features(rows, hierarchy_placeholder)
    columns = _model_d_columns(all_meta)
    model = fit_meta_model(
        all_meta[columns], rows["actual_result"],
        "MULTINOMIAL_LOGISTIC_STACKER", {"C": FROZEN_META_C},
    )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "feature_columns": columns,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "rating_config": config,
        "meta_c": FROZEN_META_C,
        "training_rows": len(rows),
        "training_max_date": pd.to_datetime(rows["match_date"]).max().date().isoformat(),
        "known_limitations": KNOWN_LIMITATIONS,
        "authoritative_for_1x2": False,
        "probability_blending_enabled": False,
    }
    joblib.dump(payload, artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {
        key: value for key, value in payload.items() if key != "model"
    } | {"artifact_sha256": digest}
    manifest_path = artifact.with_name("primary_plus_rating_meta_v2182_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest | {"artifact_path": str(artifact.resolve()), "manifest_path": str(manifest_path.resolve())}


def predict_shadow(
    *,
    project_root: str | Path,
    match: MatchInput,
    history: pd.DataFrame,
    primary_probabilities: dict[str, float],
    data_quality: dict,
    canonical_home_team: str,
    canonical_away_team: str,
    canonical_competition: str,
    team_resolution_audit: list[dict],
) -> dict:
    root = Path(project_root)
    artifact_path = root / DEFAULT_ARTIFACT
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Frozen shadow artifact missing: {artifact_path}. "
            "Generate it with train_frozen_shadow_artifact before enabling the shadow."
        )
    payload = joblib.load(artifact_path)
    if payload["model_name"] != MODEL_NAME or payload["rating_config"]["config_name"] != FROZEN_RATING_CONFIG:
        raise RuntimeError("Frozen shadow artifact identity mismatch")
    target_date = pd.Timestamp(match.match_date)
    frame = history.copy()
    if len(frame):
        frame["match_date"] = pd.to_datetime(frame["match_date"])
        frame = frame[
            frame["competition"].astype(str).str.casefold().eq(canonical_competition.casefold())
            & frame["match_date"].lt(target_date)
        ]
    target = pd.DataFrame([{
        "competition": canonical_competition, "season": match.season, "match_date": target_date,
        "home_team": canonical_home_team, "away_team": canonical_away_team,
        "actual_home_goals": 0, "actual_away_goals": 0, "actual_result": "DRAW",
    }])
    slim = pd.concat([frame[target.columns], target], ignore_index=True)
    rating = build_rating_features(slim, payload["rating_config"]).iloc[-1]
    home_history = int(team_resolution_audit[0]["history_count"])
    away_history = int(team_resolution_audit[1]["history_count"])
    home_rating, away_rating = float(rating["home_rating"]), float(rating["away_rating"])
    fallback_reason = []
    if home_history == 0 and away_history == 0:
        home_rating = away_rating = 1500.0
        fallback_reason.append("BOTH_TEAMS_LEAGUE_MEAN_FALLBACK")
    elif home_history == 0:
        home_rating = 1500.0
        away_rating = 1500.0 + 0.5 * (away_rating - 1500.0)
        fallback_reason.append("HOME_UNKNOWN_AWAY_SHRUNK_TO_LEAGUE_MEAN")
    elif away_history == 0:
        away_rating = 1500.0
        home_rating = 1500.0 + 0.5 * (home_rating - 1500.0)
        fallback_reason.append("AWAY_UNKNOWN_HOME_SHRUNK_TO_LEAGUE_MEAN")
    adjusted_difference = home_rating + float(rating["rating_home_advantage"]) - away_rating
    if min(home_history, away_history) == 0:
        adjusted_difference = float(np.clip(adjusted_difference, -180.0, 180.0))
        uncertainty = 1.0
        rating_home, rating_draw, rating_away = _rating_probabilities(adjusted_difference, uncertainty)
    else:
        uncertainty = float(rating["rating_uncertainty"])
        rating_home = float(rating["rating_home_probability"])
        rating_draw = float(rating["rating_draw_probability"])
        rating_away = float(rating["rating_away_probability"])
    season_history = int(
        (frame["season"].astype(str).eq(match.season)).sum()
    ) if len(frame) and "season" in frame else 0
    row = {
        "base_home_probability": primary_probabilities["HOME"],
        "base_draw_probability": primary_probabilities["DRAW"],
        "base_away_probability": primary_probabilities["AWAY"],
        "base_probability_edge": _probability_edge(primary_probabilities),
        "season_phase": min(1.0, season_history / 380.0),
        "history_quality_numeric": min(1.0, float(data_quality["minimum_team_history"]) / 20.0),
        "expected_home_goals": 0.0, "expected_away_goals": 0.0,
        "goal_home_probability": 1 / 3, "goal_draw_probability": 1 / 3,
        "goal_away_probability": 1 / 3,
        "model_agreement": 0, "maximum_model_probability_difference": 0.0,
        "rating_home_probability": rating_home, "rating_draw_probability": rating_draw,
        "rating_away_probability": rating_away, "rating_difference": adjusted_difference,
        "rating_home_advantage": rating["rating_home_advantage"],
        "rating_momentum_last5": rating["rating_momentum_last5"],
        "rating_momentum_last10": rating["rating_momentum_last10"],
        "rating_uncertainty": uncertainty, "history_count": min(home_history, away_history),
    }
    meta = meta_features(pd.DataFrame([row]), np.array([[1 / 3, 1 / 3, 1 / 3]]))
    probability = predict_meta_model(payload["model"], meta[payload["feature_columns"]])[0]
    values = {"HOME": float(probability[0]), "DRAW": float(probability[1]), "AWAY": float(probability[2])}
    ranking = sorted(values, key=values.get, reverse=True)
    unresolved = any(item["match_method"] == "UNRESOLVED" for item in team_resolution_audit)
    inconsistent = min(home_history, away_history) == 0 and abs(adjusted_difference) > 180.0
    alias_used = any(item["alias_used"] for item in team_resolution_audit)
    normalized_match = any(item["match_method"] == "NORMALIZED_EXACT" for item in team_resolution_audit)
    quality = (
        "INVALID_HISTORY" if unresolved or inconsistent
        else "LOW" if fallback_reason or min(home_history, away_history) < 5
        else "MEDIUM" if alias_used or normalized_match or min(home_history, away_history) < 15
        else "HIGH"
    )
    ineligibility = []
    if quality == "INVALID_HISTORY":
        ineligibility.append("INVALID_HISTORY")
    for index, item in enumerate(team_resolution_audit):
        item["final_prematch_rating"] = home_rating if index == 0 else away_rating
        item["rating_source"] = "LEAGUE_AVERAGE_FALLBACK" if item["history_count"] == 0 else "PRIOR_COMPETITION_HISTORY"
        item["fallback_used"] = item["history_count"] == 0
        if item["history_count"] == 0 and not item["fallback_reason"]:
            item["fallback_reason"] = fallback_reason[0] if fallback_reason else "LEAGUE_MEAN_FALLBACK"
    return {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_role": MODEL_ROLE,
        "home_probability": values["HOME"],
        "draw_probability": values["DRAW"],
        "away_probability": values["AWAY"],
        "top_outcome": ranking[0],
        "top_probability": values[ranking[0]],
        "probability_edge": values[ranking[0]] - values[ranking[1]],
        "authoritative_for_1x2": False,
        "prospective_status": "PROSPECTIVE_VALIDATION_REQUIRED",
        "known_limitations": KNOWN_LIMITATIONS,
        "shadow_prediction_quality": quality,
        "eligible_for_prospective_evaluation": quality != "INVALID_HISTORY",
        "ineligibility_reasons": ineligibility,
        "team_rating_audit": team_resolution_audit,
        "rating_audit": {
            "rating_config": FROZEN_RATING_CONFIG,
            "requested_home_team_name": team_resolution_audit[0]["requested_team_name"],
            "normalized_home_team_name": team_resolution_audit[0]["normalized_team_name"],
            "matched_home_history_team_name": team_resolution_audit[0]["matched_history_team_name"],
            "home_match_method": team_resolution_audit[0]["match_method"],
            "requested_away_team_name": team_resolution_audit[1]["requested_team_name"],
            "normalized_away_team_name": team_resolution_audit[1]["normalized_team_name"],
            "matched_away_history_team_name": team_resolution_audit[1]["matched_history_team_name"],
            "away_match_method": team_resolution_audit[1]["match_method"],
            "alias_used": alias_used,
            "home_alias_used": bool(team_resolution_audit[0]["alias_used"]),
            "away_alias_used": bool(team_resolution_audit[1]["alias_used"]),
            "rating_source": (
                "PRIOR_COMPETITION_HISTORY" if not fallback_reason
                else "LEAGUE_AVERAGE_FALLBACK" if home_history == 0 and away_history == 0
                else "PARTIAL_HISTORY_WITH_LEAGUE_SHRINKAGE"
            ),
            "rating_difference": adjusted_difference,
            "rating_momentum_last5": float(rating["rating_momentum_last5"]),
            "rating_momentum_last10": float(rating["rating_momentum_last10"]),
            "rating_uncertainty": uncertainty,
            "history_count": min(home_history, away_history),
            "home_history_count": home_history,
            "away_history_count": away_history,
            "fallback_used": bool(fallback_reason),
            "fallback_reason": "|".join(fallback_reason),
        },
    }


def compare_primary_shadow(primary: dict, shadow: dict) -> dict:
    primary_probabilities = dict(primary["probabilities"])
    shadow_probabilities = {
        "HOME": shadow["home_probability"], "DRAW": shadow["draw_probability"], "AWAY": shadow["away_probability"]
    }
    return {
        "primary_top_outcome": primary["top_outcome"],
        "shadow_top_outcome": shadow["top_outcome"],
        "top_outcome_agreement": primary["top_outcome"] == shadow["top_outcome"],
        "primary_probabilities": primary_probabilities,
        "shadow_probabilities": shadow_probabilities,
        "maximum_probability_difference": max(
            abs(primary_probabilities[outcome] - shadow_probabilities[outcome])
            for outcome in ("HOME", "DRAW", "AWAY")
        ),
        "primary_correctness_unknown": True,
        "probability_blending_applied": False,
    }


def _model_d_columns(frame: pd.DataFrame) -> list[str]:
    common = ["rating_difference", "base_probability_edge", "season_phase", "history_quality_numeric"]
    return list(dict.fromkeys(
        [column for column in frame if column.startswith(("primary_", "rating_"))] + common
    ))


def _probability_edge(probabilities: dict[str, float]) -> float:
    ranked = sorted(probabilities.values(), reverse=True)
    return ranked[0] - ranked[1]


def _rating_probabilities(difference: float, uncertainty: float) -> tuple[float, float, float]:
    home_non_draw = 1.0 / (1.0 + 10.0 ** (-difference / 400.0))
    draw = float(np.clip(0.28 - abs(difference) / 2200.0 + uncertainty * 0.03, 0.16, 0.34))
    return (1.0 - draw) * home_non_draw, draw, (1.0 - draw) * (1.0 - home_non_draw)
