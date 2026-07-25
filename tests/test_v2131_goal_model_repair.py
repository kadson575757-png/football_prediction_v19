from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features
from football_prediction_v19.analysis.v2131_goal_model_failure_audit import (
    failure_audit, model_difference_audit, select_training_only_holdouts,
)
from football_prediction_v19.analysis.v2131_repaired_goal_models import (
    BASELINE, candidate_configurations, generate_repaired_predictions, repaired_lambdas, shrunk_rate,
)
from scripts.run_v2131_goal_model_repair_and_revalidation import (
    SAFETY, run_v2131_goal_model_repair_and_revalidation,
)


def _matches(rounds=12, competitions=("Premier League",), seasons=("2023/24",)):
    rows, date = [], pd.Timestamp("2023-08-01")
    for competition in competitions:
        for season in seasons:
            for i in range(rounds):
                rows.append({
                    "match_date": date, "competition": competition, "season": season,
                    "home_team": "Alpha" if i % 2 == 0 else "Beta",
                    "away_team": "Beta" if i % 2 == 0 else "Alpha",
                    "actual_home_goals": i % 4, "actual_away_goals": (i + 1) % 3,
                })
                date += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def test_shrinkage_moves_observed_rate_toward_league_mean():
    value = shrunk_rate(3.0, 5, 1.5, 10)
    assert 1.5 < value < 3.0
    assert shrunk_rate(3.0, 0, 1.5, 10) == 1.5


def test_venue_opponent_form_and_early_season_sources_are_explicit():
    features = build_rolling_goal_features(_matches(rounds=22))
    early, ready = features.iloc[0], features.iloc[-1]
    configs = {row["family"]: row for row in candidate_configurations()}
    early_result = repaired_lambdas(early, configs["SHRUNK_ATTACK_DEFENSE"])
    venue_result = repaired_lambdas(ready, configs["SHRUNK_ATTACK_DEFENSE_VENUE"])
    opponent_result = repaired_lambdas(ready, configs["SHRUNK_ATTACK_DEFENSE_OPPONENT"])
    assert early_result["fallback_reason"] == "LOW_OR_MISSING_TEAM_HISTORY"
    assert venue_result["home_feature_source"] == "VENUE_TEAM_HISTORY"
    assert opponent_result["opponent_adjustment_available"]


def test_lambda_clipping_and_dynamic_score_outputs():
    feature = build_rolling_goal_features(_matches(rounds=2)).iloc[-1].copy()
    feature["home_attack_strength"] = 100.0
    config = next(row for row in candidate_configurations() if row["family"] == "SHRUNK_ATTACK_DEFENSE")
    result = repaired_lambdas(feature, config)
    assert .15 <= result["expected_home_goals"] <= 4.5
    predictions = generate_repaired_predictions(pd.DataFrame([feature]))
    assert predictions["probability_valid"].all()
    assert predictions["probability_sum"].sub(1).abs().max() <= 1e-12
    assert predictions["top_3_scorelines"].map(len).eq(3).all()
    assert {"home_win_probability", "btts_yes_probability", "over_2_5_probability"}.issubset(predictions)


def test_failure_and_model_difference_audits_are_populated():
    predictions = generate_repaired_predictions(build_rolling_goal_features(_matches(rounds=6)))
    audit = failure_audit(predictions)
    differences = model_difference_audit(predictions, BASELINE)
    assert set(["fallback_rate", "invalid_lambda_count", "team_strength_available_rate"]).issubset(audit.columns)
    assert len(audit) == len(candidate_configurations())
    assert differences.loc[differences["model_name"].eq(BASELINE), "identical_lambda_pair_count"].iloc[0] == 6
    assert differences["different_lambda_pair_count"].gt(0).any()


def test_holdouts_never_select_parameters_on_holdout():
    features = build_rolling_goal_features(_matches(
        rounds=4, competitions=("Premier League", "La Liga", "Bundesliga"),
        seasons=("2023/24", "2024/25"),
    ))
    holdouts = select_training_only_holdouts(generate_repaired_predictions(features), BASELINE)
    assert holdouts["selection_source"].eq("TRAINING_ONLY").all()
    assert not holdouts["holdout_used_for_selection"].any()
    assert set(holdouts["fold_type"]) == {"LOSO", "LOCO"}


def test_full_runner_outputs_safety_dominance_and_asof(tmp_path):
    matches = _matches(
        rounds=4, competitions=("Premier League", "La Liga", "Bundesliga"),
        seasons=("2023/24", "2024/25"),
    )
    result = run_v2131_goal_model_repair_and_revalidation(matches=matches, output_dir=tmp_path)
    assert result["v2131_goal_model_repair_status"] == "READY"
    assert result["post_match_rows_used_count"] == 0
    assert 0 <= result["dominant_competition_share"] <= 1
    assert 0 <= result["dominant_team_share"] <= 1
    assert SAFETY == {"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    for name in (
        "v2131_failure_audit.csv", "v2131_feature_source_audit.csv", "v2131_lambda_audit.csv",
        "v2131_model_difference_audit.csv", "v2131_match_predictions.csv", "v2131_model_comparison.csv",
        "v2131_holdout_summary.csv", "v2131_competition_summary.csv", "v2131_season_summary.csv",
        "v2131_asof_audit.csv", "v2131_summary.json", "v2131_report.md",
    ):
        assert (tmp_path / name).exists()


def test_script_and_core_files_exist():
    assert Path("scripts/run_v2131_goal_model_repair_and_revalidation.py").exists()
    assert Path("src/football_prediction_v19/analysis/v2131_goal_model_failure_audit.py").exists()
    assert Path("src/football_prediction_v19/analysis/v2131_repaired_goal_models.py").exists()


def test_subthreshold_holdout_result_is_not_kept_as_component(tmp_path):
    result = run_v2131_goal_model_repair_and_revalidation(
        matches=_matches(
            rounds=4, competitions=("Premier League", "La Liga", "Bundesliga"),
            seasons=("2023/24", "2024/25"),
        ),
        output_dir=tmp_path,
    )
    if result["positive_holdout_rate"] < 0.60 or result["relative_total_goals_mae_improvement"] < 0.02:
        assert result["recommendation"] == "SWITCH_TO_ALTERNATIVE_GOAL_MODEL_CLASS"
