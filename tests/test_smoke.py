from pathlib import Path

import pandas as pd

from football_prediction_v19.cli import main
from football_prediction_v19.features import build_features, build_fixture_features
from football_prediction_v19.model import predict_feature_rows, train_from_matches
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
        "no_bet_reasons",
        "v19_flags",
    ]
    assert list(result.columns) == expected_columns
    assert len(result) >= 1
