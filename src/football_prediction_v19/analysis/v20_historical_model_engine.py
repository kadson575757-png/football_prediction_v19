# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


def run_v20_model_engine(features: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    if features.get("leakage_status") != "CLEAN":
        probs = {"HOME": 0, "DRAW": 0, "AWAY": 0}; status = "MODEL_BLOCKED"; confidence = 0.0; risk = 1.0
    else:
        market = [float(features.get("home_odds_implied_probability_asof", 0)), float(features.get("draw_odds_implied_probability_asof", 0)), float(features.get("away_odds_implied_probability_asof", 0))]
        if sum(market) > 0:
            market = [p / sum(market) for p in market]
        else:
            market = [0.34, 0.30, 0.36]
        edge = float(features.get("xg_diff_edge_asof", 0)) * 0.03 + (float(features.get("home_recent_form_points_5", 0)) - float(features.get("away_recent_form_points_5", 0))) * 0.01
        home = max(0.05, market[0] + edge); away = max(0.05, market[2] - edge); draw = max(0.05, market[1])
        total = home + draw + away
        probs = {"HOME": round(home / total, 4), "DRAW": round(draw / total, 4), "AWAY": round(away / total, 4)}
        quality = float(features.get("data_quality_score", 0)); confidence = round(min(0.9, 0.35 + quality * 0.45), 3); risk = round(1 - confidence, 3)
        status = "MODEL_READY" if quality >= 0.9 else "MODEL_PARTIAL"
    result = {"model_status": status, "home_win_probability": probs["HOME"], "draw_probability": probs["DRAW"], "away_win_probability": probs["AWAY"], "over_2_5_probability": float(features.get("over25_implied_probability_asof", 0) or 0), "model_confidence": confidence, "model_risk_score": risk, "model_data_quality_score": features.get("data_quality_score", 0), "warnings": [], "missing_inputs": [], "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    pd.DataFrame([{"selection": k, "probability": v} for k, v in probs.items()]).to_csv(out / "v20_model_probability_table.csv", index=False)
    (out / "v20_model_prediction_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "v20_model_report.md").write_text("# v2.0 Model Report\n\n" + str(result) + "\n", encoding="utf-8")
    result.update({"v20_model_prediction_result_path": str((out / "v20_model_prediction_result.json").resolve()), "v20_model_probability_table_path": str((out / "v20_model_probability_table.csv").resolve()), "v20_model_report_path": str((out / "v20_model_report.md").resolve())})
    return result
