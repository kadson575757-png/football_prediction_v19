# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame


def write_calibration_dataset(backtest_results_csv: str | Path, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        df = pd.read_csv(backtest_results_csv, keep_default_na=False)
    except EmptyDataError:
        df = pd.DataFrame()
    dataset = enrich_prediction_frame(df)
    if dataset.empty:
        dataset = pd.DataFrame(columns=["league", "match_id", "prediction_date", "result_1x2", "predicted_winner", "decision_class", "home_win_probability", "draw_probability", "away_win_probability", "top_edge", "confidence", "confidence_cap_applied", "no_decision_reason"])
    else:
        dataset["league"] = dataset["competition"]
        dataset["match_id"] = dataset["canonical_match_id"]
        dataset["prediction_date"] = dataset["match_date"]
        dataset["predicted_winner"] = dataset["predicted_top_class"]
        dataset["league_prediction_tier"] = dataset["prediction_tier"]
        dataset["correct_top1"] = dataset["top1_correct"]
        dataset["brier_components"] = dataset.apply(lambda row: json.dumps({
            "H": (row["home_win_probability"] - (1.0 if row["result_1x2"] == "H" else 0.0)) ** 2,
            "D": (row["draw_probability"] - (1.0 if row["result_1x2"] == "D" else 0.0)) ** 2,
            "A": (row["away_win_probability"] - (1.0 if row["result_1x2"] == "A" else 0.0)) ** 2,
        }), axis=1)
    csv_path = out / "calibration_dataset.csv"
    json_path = out / "calibration_dataset.json"
    pvr_path = out / "model_prediction_vs_result.csv"
    dataset.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(dataset.to_dict(orient="records"), indent=2, default=str), encoding="utf-8")
    dataset.to_csv(pvr_path, index=False)
    return {"v22_calibration_export_status": "READY", "calibration_dataset_csv_path": str(csv_path.resolve()), "calibration_dataset_json_path": str(json_path.resolve()), "model_prediction_vs_result_path": str(pvr_path.resolve())}
