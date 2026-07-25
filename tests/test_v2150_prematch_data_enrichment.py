from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v2140_goal_ml_dataset import build_goal_ml_dataset
from football_prediction_v19.analysis.v2150_enriched_challenger import (
    ablation_definitions, fit_enriched_pair, predict_enriched_pair,
)
from football_prediction_v19.analysis.v2150_enriched_dataset import build_enriched_dataset
from football_prediction_v19.analysis.v2150_enriched_validation import enriched_outer_folds
from football_prediction_v19.analysis.v2150_enriched_validation import _contribution_shares
from football_prediction_v19.analysis.v2150_feature_coverage import (
    feature_coverage, group_coverage_gates,
)
from football_prediction_v19.analysis.v2150_prematch_data_sources import source_inventory
from scripts.run_v2150_prematch_data_enrichment import SAFETY, _dominance


def _matches(rounds=8, competitions=("Premier League", "La Liga", "Bundesliga"), seasons=("2023/24", "2024/25")):
    rows, date = [], pd.Timestamp("2023-08-01")
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


def _base():
    matches = _matches()
    context = matches[["competition", "season", "match_date", "home_team", "away_team"]].copy()
    context["base_home_probability"] = .42
    context["base_draw_probability"] = .29
    context["base_away_probability"] = .29
    context["base_probability_edge"] = .13
    return build_goal_ml_dataset(matches, probability_context=context)


def _chance_events(base):
    events = base[["competition", "season", "match_date", "home_team", "away_team", "actual_home_goals", "actual_away_goals"]].rename(
        columns={"actual_home_goals": "home_goals", "actual_away_goals": "away_goals"}
    ).copy()
    for column, value in {
        "home_shots": 12, "away_shots": 10, "home_shots_on_target": 5, "away_shots_on_target": 4,
        "home_corners": 6, "away_corners": 4, "home_odds": 2.0, "draw_odds": 3.4, "away_odds": 3.8,
    }.items():
        events[column] = value
    events["source_name"] = "STUB"
    return events


def _xg_events(base):
    events = base[base["competition"].eq("Bundesliga")][
        ["competition", "season", "match_date", "home_team", "away_team"]
    ].copy()
    events["home_xg"] = 1.5
    events["away_xg"] = 1.1
    events["source_name"] = "STUB_XG"
    return events


def _enriched():
    base = _base()
    return build_enriched_dataset(base, _chance_events(base), _xg_events(base))


def test_source_inventory_is_explicit_and_offline():
    inventory = source_inventory(".")
    assert {"EXPECTED_GOALS", "CHANCE_CREATION", "SQUAD_AVAILABILITY", "MARKET_CONTEXT"}.issubset(set(inventory["data_group"]))
    assert not inventory["network_required"].any()
    market = inventory[inventory["data_group"].eq("MARKET_CONTEXT")].iloc[0]
    assert not market["prematch_timestamp_available"]


def test_feature_coverage_and_gates_reject_unverifiable_groups():
    enriched = _enriched()
    coverage = feature_coverage(enriched)
    gates = group_coverage_gates(enriched, coverage).set_index("feature_group")
    assert gates.loc["CHANCE_CREATION", "passes_main_coverage_gate"]
    assert not gates.loc["EXPECTED_GOALS", "passes_main_coverage_gate"]
    assert not gates.loc["SQUAD_AVAILABILITY", "passes_main_coverage_gate"]
    assert not gates.loc["MARKET_CONTEXT", "passes_main_coverage_gate"]
    assert gates.loc["MARKET_CONTEXT", "asof_failed_count"] > 0


def test_rolling_xg_uses_only_prior_matches():
    enriched = _enriched()
    bundesliga = enriched[enriched["competition"].eq("Bundesliga")]
    first = bundesliga.iloc[0]
    later = bundesliga.iloc[2]
    assert pd.isna(first["home_rolling_xg_for"])
    assert pd.notna(later["home_rolling_xg_for"])
    assert pd.Timestamp(later["home_rolling_xg_for_source_date"]) < later["match_date"]


def test_squad_missing_and_market_timestamp_failure_are_not_fabricated():
    enriched = _enriched()
    assert enriched["home_confirmed_absence_count"].isna().all()
    assert enriched["home_confirmed_absence_count_missing_indicator"].eq(1).all()
    available_market = enriched["market_home_implied_probability"].notna()
    assert available_market.any()
    assert not enriched.loc[available_market, "market_home_implied_probability_asof_clean"].any()


def test_target_exclusion_and_asof_audit():
    enriched = _enriched()
    assert enriched["post_match_rows_used_count"].sum() == 0
    assert enriched["asof_clean"].all()
    assert (
        pd.to_datetime(enriched.loc[enriched["maximum_feature_source_date"].ne(""), "maximum_feature_source_date"])
        < enriched.loc[enriched["maximum_feature_source_date"].ne(""), "match_date"]
    ).all()


def test_training_only_preprocessing_with_chance_ablation():
    enriched = _enriched()
    definition = next(
        item for item in ablation_definitions(["CHANCE_CREATION"])
        if item["model_class"] == "GRADIENT_BOOSTING"
    )
    train, holdout = enriched.iloc[:32], enriched.iloc[32:]
    models = fit_enriched_pair(train, definition)
    home, away, clipped = predict_enriched_pair(models, holdout, definition["feature_groups"])
    assert len(home) == len(holdout)
    assert ((home >= .1) & (home <= 5)).all()
    assert clipped.dtype == bool


def test_ablation_and_outer_holdouts_are_separate():
    enriched = _enriched()
    definitions = ablation_definitions(["CHANCE_CREATION"])
    assert any(item["model_name"] == "MODEL_5_ALL_PASSING" for item in definitions)
    folds = enriched_outer_folds(enriched)
    assert {"LOSO", "LOCO", "CHRONO_LATE_SEASON"}.issubset({fold["fold_type"] for fold in folds})
    for fold in folds:
        assert not (fold["train_mask"] & fold["holdout_mask"]).any()


def test_dominance_audit_is_bounded():
    from football_prediction_v19.analysis.v2140_goal_probability_outputs import attach_probability_outputs
    enriched = _enriched().iloc[:12]
    baseline = attach_probability_outputs(enriched, [1.4] * 12, [1.1] * 12, model_name="B", model_parameters="{}")
    best = attach_probability_outputs(enriched, [1.5] * 12, [1.2] * 12, model_name="C", model_parameters="{}")
    result = _dominance(best, baseline)
    assert 0 <= result["dominant_competition_share"] <= 1
    assert 0 <= result["dominant_team_share"] <= 1
    contribution = _contribution_shares(best, baseline)
    assert 0 <= contribution["competition_contribution_share"] <= 1
    assert 0 <= contribution["team_contribution_share"] <= 1


def test_script_core_files_and_safety_flags():
    for path in (
        "scripts/run_v2150_prematch_data_enrichment.py",
        "src/football_prediction_v19/analysis/v2150_prematch_data_sources.py",
        "src/football_prediction_v19/analysis/v2150_feature_coverage.py",
        "src/football_prediction_v19/analysis/v2150_enriched_dataset.py",
        "src/football_prediction_v19/analysis/v2150_enriched_challenger.py",
        "src/football_prediction_v19/analysis/v2150_enriched_validation.py",
    ):
        assert Path(path).exists()
    assert SAFETY == {
        "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }
