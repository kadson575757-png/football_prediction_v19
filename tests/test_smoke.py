from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from football_prediction_v19.cli import main
from football_prediction_v19.backtest import build_betting_report
from football_prediction_v19.data import REAL_MATCH_OPTIONAL_NUMERIC_COLUMNS, prepare_real_matches
from football_prediction_v19.features import build_features, build_fixture_features
from football_prediction_v19.excel_report import create_predictions_excel_report
from football_prediction_v19.model import predict_feature_rows, train_from_matches
from football_prediction_v19.odds import (
    best_value_side,
    bookmaker_overround,
    fair_probabilities,
    grade_flat_stake_bet,
    implied_probability,
    model_edges,
)
from football_prediction_v19.rules_v19 import assess_prediction
from football_prediction_v19.team_names import normalize_team_name


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


def test_excel_report_creation_and_sheets(tmp_path):
    predictions_path = tmp_path / "predictions.csv"
    output_path = tmp_path / "predictions_report.xlsx"
    pd.DataFrame(
        [
            {
                "date": "2024-05-01",
                "league": "Premier League",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "prob_home": 0.38,
                "prob_draw": 0.36,
                "prob_away": 0.26,
                "odds_home": 2.4,
                "odds_draw": 3.4,
                "odds_away": 2.9,
                "fair_home": 0.39,
                "fair_draw": 0.28,
                "fair_away": 0.33,
                "edge_home": -0.01,
                "edge_draw": 0.08,
                "edge_away": -0.07,
                "value_pick": "No Bet",
                "value_edge": 0.08,
                "bet_recommendation": "No bet",
                "control_score": 2.4,
                "chaos_score": 6.0,
                "tdi_home": 1,
                "tdi_away": 0,
                "no_bet_reasons": "No value bet: control score below 7",
                "v19_flags": "",
            },
            {
                "date": "2024-05-04",
                "league": "Premier League",
                "home_team": "Liverpool",
                "away_team": "Tottenham",
                "prob_home": 0.60,
                "prob_draw": 0.21,
                "prob_away": 0.19,
                "odds_home": 1.95,
                "odds_draw": 3.7,
                "odds_away": 3.85,
                "fair_home": 0.49,
                "fair_draw": 0.26,
                "fair_away": 0.25,
                "edge_home": 0.11,
                "edge_draw": -0.05,
                "edge_away": -0.06,
                "value_pick": "Home",
                "value_edge": 0.11,
                "bet_recommendation": "Value bet: Home 1X2",
                "control_score": 8.6,
                "chaos_score": 3.4,
                "tdi_home": 0,
                "tdi_away": 1,
                "no_bet_reasons": "",
                "v19_flags": "sample_flag",
            },
        ]
    ).to_csv(predictions_path, index=False)

    create_predictions_excel_report(predictions_path, output_path)

    assert output_path.exists()
    wb = load_workbook(output_path)
    assert set(["Summary", "Predictions", "Value Bets", "No Bets", "High Chaos", "v19 Flags"]).issubset(wb.sheetnames)
    headers = [cell.value for cell in wb["Predictions"][1]]
    assert "prob_home" in headers
    assert "bet_recommendation" in headers
    assert wb["Predictions"].freeze_panes == "A2"


def test_export_excel_command_runs_on_sample_predictions(tmp_path):
    root = Path(__file__).resolve().parents[1]
    history_path = root / "data" / "sample_matches.csv"
    fixtures_path = root / "data" / "upcoming_fixtures_template.csv"
    model_path = tmp_path / "sample_model.joblib"
    predictions_path = tmp_path / "predictions.csv"
    output_path = tmp_path / "predictions_report.xlsx"

    main(["train", "--input", str(history_path), "--model", str(model_path), "--test-season", "2023"])
    main([
        "predict-fixtures",
        "--history",
        str(history_path),
        "--fixtures",
        str(fixtures_path),
        "--model",
        str(model_path),
        "--output",
        str(predictions_path),
    ])
    main(["export-excel", "--predictions", str(predictions_path), "--output", str(output_path)])

    wb = load_workbook(output_path)
    assert "Summary" in wb.sheetnames
    assert "Value Bets" in wb.sheetnames


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


def test_bet_grading_and_profit_calculation():
    stake, profit = grade_flat_stake_bet("Home", "H", 2.40)
    assert stake == 1.0
    assert profit == 1.4

    stake, profit = grade_flat_stake_bet("Away", "H", 2.90)
    assert stake == 1.0
    assert profit == -1.0

    stake, profit = grade_flat_stake_bet("No Bet", "H", 2.40)
    assert stake == 0.0
    assert profit == 0.0


def test_betting_report_creation():
    rows = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "league": "Premier League",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "result": "H",
                "prob_home": 0.55,
                "prob_draw": 0.25,
                "prob_away": 0.20,
                "odds_home": 2.20,
                "odds_draw": 3.40,
                "odds_away": 3.30,
                "value_pick": "Home",
                "value_edge": 0.05,
                "stake": 1.0,
                "profit": 1.2,
                "no_bet_reasons": "",
            },
            {
                "date": "2024-01-02",
                "league": "Premier League",
                "home_team": "Liverpool",
                "away_team": "Spurs",
                "result": "D",
                "prob_home": 0.40,
                "prob_draw": 0.35,
                "prob_away": 0.25,
                "odds_home": 1.90,
                "odds_draw": 3.60,
                "odds_away": 4.20,
                "value_pick": "No Bet",
                "value_edge": 0.01,
                "stake": 0.0,
                "profit": 0.0,
                "no_bet_reasons": "No value bet: control score below 7",
            },
        ]
    )

    report = build_betting_report(rows)

    assert "# Betting Backtest Report" in report
    assert "Total matches: 2" in report
    assert "Total bets: 1" in report
    assert "No value bet: control score below 7" in report


def test_backtest_bets_command_runs_on_sample_data(tmp_path):
    root = Path(__file__).resolve().parents[1]
    history_path = root / "data" / "sample_matches.csv"
    model_path = tmp_path / "sample_model.joblib"
    output_path = tmp_path / "outputs" / "backtest_bets.csv"
    report_path = tmp_path / "outputs" / "backtest_report.md"

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
            "backtest-bets",
            "--history",
            str(history_path),
            "--model",
            str(model_path),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
            "--min-edge",
            "0.03",
            "--max-chaos",
            "7.0",
            "--min-control",
            "7.0",
        ]
    )

    assert output_path.exists()
    assert report_path.exists()
    results = pd.read_csv(output_path)
    assert "profit" in results.columns
    assert "cumulative_profit" in results.columns
    assert (results["stake"] == 0).any()
    assert "ROI" in report_path.read_text(encoding="utf-8")


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


def test_team_alias_normalization():
    assert normalize_team_name(" Man Utd ") == "Manchester United"
    assert normalize_team_name("Spurs") == "Tottenham Hotspur"
    assert normalize_team_name("Unknown FC") == "Unknown FC"


def test_prepare_real_matches_native_format_auto_detects():
    raw = pd.DataFrame(
        [
            {
                "date": "2023-08-12",
                "season": "2023-2024",
                "league": "Premier League",
                "home_team": "Man Utd",
                "away_team": "Wolves",
                "score": "1-0",
                "home_xg": 1.2,
                "away_xg": 0.7,
                "odds_home": 1.8,
                "odds_draw": 3.5,
                "odds_away": 4.8,
                "venue": "Old Trafford",
                "referee": "Unknown",
            }
        ]
    )

    clean = prepare_real_matches(raw, input_format="auto")

    assert clean.attrs["detected_format"] == "native"
    assert clean.loc[0, "home_team"] == "Manchester United"
    assert clean.loc[0, "away_team"] == "Wolverhampton Wanderers"


def test_prepare_real_matches_fbref_format():
    raw = pd.DataFrame(
        [
            {
                "Date": "2023-08-12",
                "Season": "2023-2024",
                "Comp": "Premier League",
                "Home": "Brighton",
                "Away": "Newcastle",
                "Score": "2-1",
                "xG": 1.7,
                "xG.1": 1.0,
                "odds_home": 2.1,
                "odds_draw": 3.4,
                "odds_away": 3.5,
                "Venue": "Amex Stadium",
                "Referee": "Unknown",
            }
        ]
    )

    clean = prepare_real_matches(raw, input_format="fbref")

    assert clean.attrs["detected_format"] == "fbref"
    assert clean.loc[0, "home_team"] == "Brighton & Hove Albion"
    assert clean.loc[0, "away_team"] == "Newcastle United"
    assert clean.loc[0, "home_xg"] == 1.7


def test_prepare_real_matches_football_data_format_auto_detects():
    raw = pd.DataFrame(
        [
            {
                "Date": "12/08/2023",
                "HomeTeam": "Tottenham",
                "AwayTeam": "Man United",
                "FTHG": 2,
                "FTAG": 0,
                "FTR": "H",
                "B365H": 2.4,
                "B365D": 3.3,
                "B365A": 2.9,
            }
        ]
    )

    clean = prepare_real_matches(raw, input_format="auto")

    assert clean.attrs["detected_format"] == "football-data"
    assert clean.loc[0, "home_team"] == "Tottenham Hotspur"
    assert clean.loc[0, "away_team"] == "Manchester United"
    assert clean.loc[0, "score"] == "2-0"
    assert clean.loc[0, "league"] == "Unknown"


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
