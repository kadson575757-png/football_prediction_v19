from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_goal_distribution import (
    SAFETY_FLAGS,
    analyze_unified_goal_distribution,
    generate_candidate_predictions,
)
from football_prediction_v19.analysis.v2130_goal_model_evaluation import (
    build_holdout_summary,
    evaluate_predictions,
)
from football_prediction_v19.analysis.v2130_match_profile import derive_match_profile
from football_prediction_v19.analysis.v2130_poisson_models import expected_goals_for_model
from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features
from football_prediction_v19.analysis.v2130_score_matrix import (
    build_score_matrix,
    derive_distribution,
    dixon_coles_tau,
    poisson_pmf,
)


def _matches(competitions=("Premier League",), seasons=("2023/24",), rounds=12):
    rows = []
    date = pd.Timestamp("2023-08-01")
    for competition in competitions:
        for season in seasons:
            for index in range(rounds):
                rows.append({
                    "match_date": date, "competition": competition, "season": season,
                    "home_team": "Alpha" if index % 2 == 0 else "Beta",
                    "away_team": "Beta" if index % 2 == 0 else "Alpha",
                    "actual_home_goals": index % 4, "actual_away_goals": (index + 1) % 3,
                })
                date += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def test_rolling_features_are_strictly_prematch_and_fallback_then_ready():
    features = build_rolling_goal_features(_matches(rounds=22))
    first, last = features.iloc[0], features.iloc[-1]
    assert first["league_prior_matches_count"] == 0
    assert first["fallback_applied"]
    assert first["maximum_source_date"] == ""
    assert last["history_quality"] == "READY"
    assert pd.Timestamp(last["maximum_source_date"]) < last["match_date"]
    assert features["post_match_rows_used_count"].sum() == 0
    assert features["asof_clean"].all()


def test_matches_on_same_date_do_not_see_each_other():
    matches = _matches(rounds=2)
    matches.loc[:, "match_date"] = pd.Timestamp("2023-08-01")
    features = build_rolling_goal_features(matches)
    assert features["league_prior_matches_count"].tolist() == [0, 0]
    assert features["maximum_source_date"].tolist() == ["", ""]


def test_attack_defense_form_and_venue_models_produce_positive_expected_goals():
    features = build_rolling_goal_features(_matches(rounds=22))
    row = features.iloc[-1]
    for model in (
        "ROLLING_ATTACK_DEFENSE_POISSON",
        "ROLLING_ATTACK_DEFENSE_FORM_5_POISSON",
        "ROLLING_ATTACK_DEFENSE_FORM_10_POISSON",
        "VENUE_ATTACK_DEFENSE_POISSON",
    ):
        home, away, rho = expected_goals_for_model(row, model)
        assert home > 0 and away > 0 and rho == 0


def test_poisson_dixon_coles_score_matrix_and_all_derivations_are_consistent():
    assert poisson_pmf(0, 1.5) > 0
    assert dixon_coles_tau(0, 0, 1.5, 1.1, -0.1) != 1.0
    independent, _ = build_score_matrix(1.5, 1.1, max_goals=12)
    corrected, residual = build_score_matrix(1.5, 1.1, max_goals=12, rho=-0.1)
    assert not np.allclose(independent[:2, :2], corrected[:2, :2])
    distribution = derive_distribution(corrected)
    assert abs(corrected.sum() - 1.0) <= 1e-12
    assert abs(distribution["probability_sum"] - 1.0) <= 1e-12
    assert abs(distribution["btts_yes_probability"] + distribution["btts_no_probability"] - 1) <= 1e-12
    assert abs(distribution["over_2_5_probability"] + distribution["under_2_5_probability"] - 1) <= 1e-12
    assert abs(
        distribution["total_goals_0_1_probability"]
        + distribution["total_goals_2_3_probability"]
        + distribution["total_goals_4_plus_probability"] - 1
    ) <= 1e-12
    assert len(distribution["top_3_scorelines"]) == 3
    assert len(distribution["top_5_scorelines"]) == 5
    assert residual < 1e-6


def test_match_profiles_cover_distribution_driven_cases():
    low = {"home_win_probability": 0.36, "away_win_probability": 0.31, "btts_yes_probability": 0.35, "total_goals_4_plus_probability": 0.1}
    home = {"home_win_probability": 0.60, "away_win_probability": 0.18, "btts_yes_probability": 0.45, "total_goals_4_plus_probability": 0.2}
    open_game = {"home_win_probability": 0.45, "away_win_probability": 0.35, "btts_yes_probability": 0.65, "total_goals_4_plus_probability": 0.4}
    assert derive_match_profile(low, 1.0, 0.9) == "LOW_SCORING_BALANCED"
    assert derive_match_profile(home, 2.0, 0.8) == "HOME_CONTROL"
    assert derive_match_profile(open_game, 1.8, 1.4) == "OPEN_HIGH_SCORING"


def test_holdouts_select_on_training_only_and_metrics_are_available():
    features = build_rolling_goal_features(_matches(
        competitions=("Premier League", "La Liga"), seasons=("2023/24", "2024/25"), rounds=6,
    ))
    predictions = generate_candidate_predictions(features)
    holdouts, best = build_holdout_summary(predictions)
    metrics = evaluate_predictions(predictions, best)
    assert not holdouts["holdout_used_for_selection"].any()
    assert holdouts["selection_source"].eq("TRAINING_ONLY").all()
    assert (holdouts["training_rows"] > 0).all()
    loso = holdouts[holdouts["fold_type"].eq("LOSO")]
    assert (loso["training_rows"] < holdouts[holdouts["fold_type"].eq("LOCO")]["training_rows"].max()).all()
    for key in ("home_goals_mae", "multiclass_brier_score", "btts_brier_score", "over_2_5_brier_score", "exact_score_top5_hit_rate"):
        assert key in metrics


def test_full_analysis_outputs_and_safety_flags(tmp_path):
    matches = _matches(
        competitions=("Premier League", "La Liga", "Bundesliga"),
        seasons=("2023/24", "2024/25"), rounds=5,
    )
    result = analyze_unified_goal_distribution(matches, output_dir=tmp_path)
    assert result["v2130_unified_goal_distribution_status"] == "READY"
    assert result["post_match_rows_used_count"] == 0
    assert result["probability_output_rate"] == 1.0
    assert SAFETY_FLAGS == {
        "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }
    for filename in (
        "v2130_feature_availability.csv", "v2130_match_predictions.csv",
        "v2130_scoreline_predictions.jsonl", "v2130_model_comparison.csv",
        "v2130_holdout_summary.csv", "v2130_competition_summary.csv",
        "v2130_season_summary.csv", "v2130_asof_audit.csv",
        "v2130_summary.json", "v2130_report.md",
    ):
        assert (tmp_path / filename).exists()


def test_script_and_all_core_modules_exist():
    assert Path("scripts/run_v2130_unified_goal_distribution_analysis.py").exists()
    for filename in (
        "v2130_goal_distribution.py", "v2130_rolling_goal_features.py", "v2130_poisson_models.py",
        "v2130_score_matrix.py", "v2130_goal_model_evaluation.py", "v2130_match_profile.py",
    ):
        assert Path("src/football_prediction_v19/analysis", filename).exists()
