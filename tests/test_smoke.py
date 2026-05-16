from pathlib import Path

import pandas as pd

from football_prediction_v19.cli import main
from football_prediction_v19.data import REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS, prepare_real_matches
from football_prediction_v19.features import build_features, build_fixture_features
from football_prediction_v19.model import predict_feature_rows, train_from_matches
from football_prediction_v19.odds import (
    best_value_side,
    bookmaker_overround,
    fair_probabilities,
    implied_probability,
    model_edges,
)
from football_prediction_v19.rules_v19 import assess_prediction


def test_pipeline_smoke():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_matches.csv"
    df = pd.read_csv(path)
    model, table, metrics, cols = train_from_matches(df, test_season=2023)
    assert len(table) > 10
    fixture = build_fixture_features(df, "Chelsea", "Arsenal", "2024-05-01")
    bundle = {"model": model, "feature_cols": cols, "metrics": metrics}
    pred = predict_feature_rows(bundle, fixture).iloc[0]
    assessment = assess_prediction(pred, {"H": pred.prob_home, "D": pred.prob_draw, "A": pred.prob_away})
    assert "probabilities" in assessment


def test_basic_dataset_still_trains_without_optional_columns():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_matches.csv"
    df = pd.read_csv(path)
    model, table, metrics, cols = train_from_matches(df, test_season=2023)

    assert len(table) > 10
    assert metrics["feature_count"] == len(cols)
    assert "home_w5_shots" not in cols


def test_predict_fixtures_command(tmp_path):
    root = Path(__file__).resolve().parents[1]
    history_path = root / "data" / "sample_matches.csv"
    fixtures_path = root / "data" / "upcoming_fixtures_template.csv"
    model_path = tmp_path / "sample_model.joblib"
    output_path = tmp_path / "outputs" / "predictions.csv"

    main(
        [
            "train",
            "--input",
            str(history_path),
            "--model",
            str(model_path),
            "--test-season",
            "2023",
        ]
    )
    main(
        [
            "predict-fixtures",
            "--history",
            str(history_path),
            "--fixtures",
            str(fixtures_path),
            "--model",
            str(model_path),
            "--output",
            str(output_path),
        ]
    )

    assert output_path.exists()
    result = pd.read_csv(output_path)
    expected_columns = [
        "date",
        "league",
        "home_team",
        "away_team",
        "prob_home",
        "prob_draw",
        "prob_away",
        "top_pick",
        "confidence",
        "control_score",
        "chaos_score",
        "tdi_home",
        "tdi_away",
        "odds_home",
        "odds_draw",
        "odds_away",
        "implied_home",
        "implied_draw",
        "implied_away",
        "fair_home",
        "fair_draw",
        "fair_away",
        "edge_home",
        "edge_draw",
        "edge_away",
        "value_pick",
        "value_edge",
        "bet_recommendation",
        "no_bet_reasons",
        "v19_flags",
    ]
    assert list(result.columns) == expected_columns
    assert len(result) >= 1
    assert "value_pick" in result.columns


def test_odds_conversion_and_overround_removal():
    odds = {"home": 2.0, "draw": 4.0, "away": 4.0}

    assert implied_probability(2.0) == 0.5
    assert round(bookmaker_overround(odds), 4) == 0.0
    assert fair_probabilities(odds) == {"home": 0.5, "draw": 0.25, "away": 0.25}


def test_positive_value_detection():
    odds = {"home": 2.20, "draw": 3.50, "away": 3.40}
    fair = fair_probabilities(odds)
    edges = model_edges({"H": 0.50, "D": 0.25, "A": 0.25}, fair)
    side, edge = best_value_side(edges, min_edge=0.03)

    assert side == "home"
    assert edge > 0.03


def test_no_bet_when_control_score_too_low():
    from football_prediction_v19.cli import _value_recommendation

    pred = pd.Series({"odds_home": 2.20, "odds_draw": 3.50, "odds_away": 3.40})
    probs = {"H": 0.50, "D": 0.25, "A": 0.25}
    assessment = {
        "control_model_score": 6.5,
        "chaos_score": 4.0,
        "locks": [],
        "no_bets": [],
    }

    value = _value_recommendation(pred, probs, assessment, min_edge=0.03, max_chaos=7.0, min_control=7.0)

    assert value["value_pick"] == "No Bet"
    assert value["bet_recommendation"] == "No bet"
    assert any("control score below 7" in reason for reason in value["no_bet_reasons"])


def test_prepare_real_matches_cleans_training_rows():
    raw = pd.DataFrame(
        [
            {
                "date": "2023-08-13",
                "season": "2023-2024",
                "league": "Premier League",
                "home_team": " Arsenal ",
                "away_team": "Nottingham Forest",
                "score": "2-1",
                "home_xg": "1.9",
                "away_xg": "0.8",
                "odds_home": "1.45",
                "odds_draw": "4.60",
                "odds_away": "7.20",
                "venue": "Emirates Stadium",
                "referee": "Michael Oliver",
            },
            {
                "date": "2023-08-12",
                "season": "2023-2024",
                "league": "Premier League",
                "home_team": "Chelsea",
                "away_team": "Liverpool",
                "score": "",
                "home_xg": "1.4",
                "away_xg": "1.3",
                "odds_home": "2.50",
                "odds_draw": "3.40",
                "odds_away": "2.80",
                "venue": "Stamford Bridge",
                "referee": "Anthony Taylor",
            },
        ]
    )

    clean = prepare_real_matches(raw)

    assert len(clean) == 1
    assert clean.loc[0, "home_team"] == "Arsenal"
    assert clean.loc[0, "home_goals"] == 2
    assert clean.loc[0, "away_goals"] == 1
    assert clean.loc[0, "home_xg"] == 1.9
    assert clean.attrs["rows_dropped"] == 1
    assert "home_xga" in clean.attrs["optional_missing"]


def test_prepare_real_matches_keeps_optional_columns():
    root = Path(__file__).resolve().parents[1]
    raw = pd.read_csv(root / "data" / "raw" / "real_matches_template.csv")

    clean = prepare_real_matches(raw)

    assert len(clean) == 2
    assert clean.attrs["optional_missing"] == []
    assert set(REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS).issubset(clean.columns)
    assert clean.loc[0, "home_shots"] == 11
    assert clean.loc[0, "away_market_value"] == 920000000


def test_optional_columns_create_advanced_rolling_features():
    raw = pd.DataFrame(
        [
            {
                "date": "2023-08-01",
                "season": "2023-2024",
                "league": "Premier League",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "score": "1-0",
                "home_xg": 1.3,
                "away_xg": 0.8,
                "odds_home": 2.2,
                "odds_draw": 3.4,
                "odds_away": 3.1,
                "venue": "Stamford Bridge",
                "referee": "Anthony Taylor",
                "home_xga": 0.7,
                "away_xga": 1.4,
                "home_shots": 12,
                "away_shots": 8,
                "home_shots_on_target": 5,
                "away_shots_on_target": 3,
                "home_big_chances": 3,
                "away_big_chances": 1,
                "home_rest_days": 6,
                "away_rest_days": 5,
                "home_injuries_count": 1,
                "away_injuries_count": 2,
            },
            {
                "date": "2023-08-08",
                "season": "2023-2024",
                "league": "Premier League",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "score": "2-2",
                "home_xg": 1.5,
                "away_xg": 1.2,
                "odds_home": 2.0,
                "odds_draw": 3.5,
                "odds_away": 3.6,
                "venue": "Emirates Stadium",
                "referee": "Michael Oliver",
                "home_xga": 1.1,
                "away_xga": 1.6,
                "home_shots": 15,
                "away_shots": 10,
                "home_shots_on_target": 6,
                "away_shots_on_target": 4,
                "home_big_chances": 2,
                "away_big_chances": 2,
                "home_rest_days": 7,
                "away_rest_days": 7,
                "home_injuries_count": 0,
                "away_injuries_count": 1,
            },
        ]
    )

    clean = prepare_real_matches(raw)
    features = build_features(clean, min_history=1)

    assert "home_w5_shots" in features.columns
    assert "away_w5_shots_on_target" in features.columns
    assert "edge_w5_big_chances" in features.columns
    assert features.loc[0, "home_w5_shots"] == 8
    assert features.loc[0, "away_w5_injuries_count"] == 1


def test_prepare_data_command_writes_clean_csv(tmp_path):
    input_path = tmp_path / "raw" / "real_matches.csv"
    output_path = tmp_path / "processed" / "real_matches_clean.csv"
    input_path.parent.mkdir(parents=True)
    input_path.write_text(
        "\n".join(
            [
                "date,season,league,home_team,away_team,score,home_xg,away_xg,odds_home,odds_draw,odds_away,venue,referee",
                "2023-08-12,2023-2024,Premier League,Chelsea,Liverpool,1-1,1.4,1.3,2.50,3.40,2.80,Stamford Bridge,Anthony Taylor",
                "2023-08-13,2023-2024,Premier League,Arsenal,Nottingham Forest,,1.9,0.8,1.45,4.60,7.20,Emirates Stadium,Michael Oliver",
            ]
        ),
        encoding="utf-8",
    )

    main(["prepare-data", "--input", str(input_path), "--output", str(output_path)])

    assert output_path.exists()
    clean = pd.read_csv(output_path)
    assert list(clean["home_team"]) == ["Chelsea"]
    assert clean.loc[0, "home_goals"] == 1
