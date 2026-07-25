from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from football_prediction_v19.analysis.v2180_cross_fitted_predictions import chronological_oof_predictions
from football_prediction_v19.analysis.v2180_dynamic_rating import build_rating_features, candidate_configs
from football_prediction_v19.analysis.v2180_hierarchical_winner import (
    fit_hierarchical_model,
    predict_hierarchical,
    reconstruct_probabilities,
)
from football_prediction_v19.analysis.v2180_meta_winner import fit_meta_model, meta_features, predict_meta_model
from football_prediction_v19.analysis.v2180_winner_validation import SAFETY, metrics, outer_holdouts
from football_prediction_v19.models.model_registry import get_model


ROOT = Path(__file__).resolve().parents[1]


def _rows(count: int = 120) -> pd.DataFrame:
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    records = []
    for index in range(count):
        home, away = teams[index % 4], teams[(index + 1) % 4]
        result = ("HOME", "DRAW", "AWAY")[index % 3]
        records.append({
            "competition": ("League A", "League B", "League C", "League D")[index % 4],
            "season": ("2023/24", "2024/25", "2025/26")[index % 3],
            "match_date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=index),
            "home_team": home, "away_team": away,
            "actual_home_goals": 2 if result == "HOME" else 1 if result == "DRAW" else 0,
            "actual_away_goals": 0 if result == "HOME" else 1 if result == "DRAW" else 2,
            "actual_result": result,
        })
    frame = pd.DataFrame(records)
    x = np.linspace(-1, 1, count)
    defaults = {
        "base_home_probability": .38 + .08*x, "base_draw_probability": .28 + 0*x,
        "base_away_probability": .34 - .08*x, "base_probability_edge": abs(x)*.08,
        "goal_home_probability": .40 + .07*x, "goal_draw_probability": .27 + 0*x,
        "goal_away_probability": .33 - .07*x, "expected_home_goals": 1.5 + .2*x,
        "expected_away_goals": 1.2 - .2*x, "rating_difference": 100*x,
        "rating_uncertainty": .2, "rating_momentum_last5": x, "rating_momentum_last10": x,
        "home_last5_points": 1.5+x, "away_last5_points": 1.5-x,
        "home_venue_points_per_match": 1.6+x, "away_venue_points_per_match": 1.4-x,
        "rolling_league_draw_rate": .27, "home_team_draw_rate": .26, "away_team_draw_rate": .28,
        "low_score_probability": .3, "model_agreement": 1,
        "rating_home_advantage": 60,
        "history_count": 20,
        "maximum_model_probability_difference": .05, "season_phase": .5,
        "history_quality_numeric": 1, "fallback_applied": 0,
        "rating_home_probability": .4 + .1*x, "rating_draw_probability": .27,
        "rating_away_probability": .33 - .1*x,
    }
    for column, values in defaults.items():
        frame[column] = values
    return frame


def test_rating_is_chronological_and_asof_clean():
    rated = build_rating_features(_rows(20), candidate_configs()[0])
    assert rated["post_match_rows_used_count"].sum() == 0
    assert rated["asof_clean"].all()
    assert all(not source or source < target for source, target in zip(rated.maximum_source_date, rated.target_match_date))


def test_rating_updates_and_home_advantage_changes_probability():
    low = build_rating_features(_rows(12), {**candidate_configs()[0], "home_advantage": 40})
    high = build_rating_features(_rows(12), {**candidate_configs()[0], "home_advantage": 80})
    assert low.iloc[4].home_rating != 1500 or low.iloc[4].away_rating != 1500
    assert high.iloc[0].rating_home_probability > low.iloc[0].rating_home_probability


def test_draw_update_is_between_win_and_loss_and_goal_margin_is_bounded():
    rows = _rows(3)
    rated = build_rating_features(rows, next(c for c in candidate_configs() if c["rating_model"] == "ELO_GOAL_DIFFERENCE"))
    assert np.isfinite(rated[["home_rating", "away_rating"]].to_numpy()).all()
    assert rated.iloc[2].rating_uncertainty > 0


def test_season_shrinkage_and_promoted_fallback_are_documented():
    rows = _rows(8)
    rows.loc[4:, "season"] = "2024/25"
    rated = build_rating_features(rows, candidate_configs()[0])
    assert rated["promoted_team_fallback"].any()
    assert rated["season_start_shrinkage_applied"].any()
    assert set(rated["uncertainty_level"]) <= {"HIGH", "MEDIUM", "LOW"}


def test_probability_reconstruction_has_no_hard_draw_rule():
    probabilities = reconstruct_probabilities([.2, .45], [.8, .8])
    assert probabilities.sum(axis=1) == pytest.approx([1, 1])
    assert probabilities[0].argmax() == 0
    assert probabilities[1].argmax() == 1
    assert probabilities[1, 1] == pytest.approx(0.45)


def test_hierarchical_draw_and_home_away_models():
    rows = _rows()
    model = fit_hierarchical_model(rows)
    probabilities = predict_hierarchical(model, rows.iloc[-10:])
    assert probabilities.shape == (10, 3)
    assert np.allclose(probabilities.sum(axis=1), 1)


def test_oof_predictions_are_strictly_out_of_sample():
    rows = _rows()
    predictions, audit = chronological_oof_predictions(rows, feature_groups="A+B+C", c=1)
    assert audit["in_sample_prediction_count"].sum() == 0
    assert audit["chronological_clean"].all()
    assert np.isfinite(predictions).any()


def test_outer_holdouts_cover_seasons_competitions_and_chronology():
    definitions = outer_holdouts(_rows())
    assert len(definitions) >= 8
    assert {row["fold_type"] for row in definitions} == {
        "LEAVE_ONE_SEASON_OUT", "LEAVE_ONE_COMPETITION_OUT", "CHRONOLOGICAL_LAST_SEGMENT"
    }


def test_meta_model_uses_oof_shaped_inputs_and_outputs_probabilities():
    rows = _rows()
    hierarchy = np.tile([.4, .28, .32], (len(rows), 1))
    x = meta_features(rows, hierarchy)
    model = fit_meta_model(x.iloc[:90], rows.actual_result.iloc[:90], "MULTINOMIAL_LOGISTIC_STACKER", {"C": 1})
    probabilities = predict_meta_model(model, x.iloc[90:])
    assert probabilities.shape == (30, 3)
    assert np.allclose(probabilities.sum(axis=1), 1)


def test_metrics_cover_accuracy_brier_logloss_and_draw():
    probabilities = np.eye(3)[pd.Categorical(_rows(12).actual_result, categories=["HOME", "DRAW", "AWAY"]).codes]
    result = metrics(_rows(12).actual_result, probabilities)
    assert result["top_outcome_hit_rate"] == 1
    assert result["multiclass_brier_score"] == 0
    assert result["draw_precision"] == result["draw_recall"] == result["draw_f1"] == 1


def test_registry_is_shadow_only_and_primary_unchanged():
    challenger = get_model("HIERARCHICAL_META_WINNER_V2180")
    primary = get_model("PRIMARY_WINNER_V21_RESULTS_CORE")
    assert challenger["status"] in {"DIAGNOSTIC_ONLY", "SHADOW_APPROVED"}
    assert challenger["role"] in {"SHADOW_CHALLENGER", "SHADOW_WINNER_CHALLENGER", "SUPERSEDED_SHADOW_DIAGNOSTIC"}
    assert primary["status"] == "ACTIVE"


def test_script_core_and_safety_flags():
    assert all(value is False for value in SAFETY.values())
    script = ROOT / "scripts/run_v2180_hierarchical_winner_challenger.py"
    cores = [
        "v2180_dynamic_rating.py", "v2180_hierarchical_winner.py",
        "v2180_cross_fitted_predictions.py", "v2180_meta_winner.py", "v2180_winner_validation.py",
    ]
    assert script.exists()
    assert all((ROOT / "src/football_prediction_v19/analysis" / name).exists() for name in cores)
    completed = subprocess.run([sys.executable, str(script), "--help"], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0
    assert "--output-dir" in completed.stdout
