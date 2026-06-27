# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def write_calibration_dataset(backtest_results_csv: str | Path, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(backtest_results_csv, keep_default_na=False)
    rows = []
    for _, row in df.iterrows():
        actual = str(row.get("actual_result", ""))
        probs = {"H": float(row.get("home_win_probability", 0) or 0), "D": float(row.get("draw_probability", 0) or 0), "A": float(row.get("away_win_probability", 0) or 0)}
        predicted = {"HOME": "H", "DRAW": "D", "AWAY": "A"}.get(str(row.get("predicted_winner", "")), "")
        rows.append({
            "league": row.get("competition", ""),
            "match_id": row.get("match_id", ""),
            "prediction_date": row.get("match_date", ""),
            "result_1x2": actual,
            "predicted_winner": row.get("predicted_winner", ""),
            "decision_class": row.get("decision_class", ""),
            "home_win_probability": probs["H"],
            "draw_probability": probs["D"],
            "away_win_probability": probs["A"],
            "confidence": row.get("confidence", 0),
            "source_quality_band": row.get("source_quality_band", ""),
            "xg_available": row.get("xg_available", ""),
            "odds_available": row.get("odds_available", ""),
            "league_prediction_tier": row.get("league_prediction_tier", ""),
            "correct_top1": bool(predicted and predicted == actual),
            "probability_assigned_to_actual_result": probs.get(actual, 0.0),
            "brier_components": json.dumps({k: (probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ["H", "D", "A"]}),
        })
    dataset = pd.DataFrame(rows)
    csv_path = out / "calibration_dataset.csv"
    json_path = out / "calibration_dataset.json"
    pvr_path = out / "model_prediction_vs_result.csv"
    dataset.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    dataset.to_csv(pvr_path, index=False)
    return {"v22_calibration_export_status": "READY", "calibration_dataset_csv_path": str(csv_path.resolve()), "calibration_dataset_json_path": str(json_path.resolve()), "model_prediction_vs_result_path": str(pvr_path.resolve())}
