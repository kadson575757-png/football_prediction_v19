# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_backtest_leakage_audit import write_backtest_leakage_audit
from football_prediction_v19.analysis.v20_backtest_report import write_backtest_report
from football_prediction_v19.analysis.v20_no_leakage_backtest_metrics import calibration_bins, compute_backtest_metrics
from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction


def run_no_leakage_backtest(matches_csv: str | Path, output_dir: str | Path, *, mock_data_dir: str = "", source_profile: str = "config/v20_internet_sources.yaml", max_matches: int | None = None) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    matches = pd.read_csv(matches_csv, keep_default_na=False)
    if max_matches:
        matches = matches.head(max_matches)
    rows = []
    for i, match in matches.iterrows():
        result = run_v20_historical_internet_prediction(home_team=match["home_team"], away_team=match["away_team"], competition=match["competition"], season=match["season"], match_date=match["match_date"], cutoff_policy="MATCH_DATE_START", mock_data_dir=mock_data_dir, source_profile=source_profile, output_dir=out / f"match_{i+1}", base_dir=Path.cwd())
        rows.append({"match_id": result["match_context"]["match_id"], "decision_class": result["decision_class"], "confidence": result["confidence"], "home_probability": result["probabilities"]["home"], "draw_probability": result["probabilities"]["draw"], "away_probability": result["probabilities"]["away"], "actual_result": match.get("actual_result", ""), "leakage_status": result["leakage_status"], "analysis_cutoff": result["analysis_cutoff"]})
    metrics = compute_backtest_metrics(rows)
    leakage = write_backtest_leakage_audit(rows, out)
    metrics.update(leakage)
    pd.DataFrame(rows).to_csv(out / "v20_no_leakage_backtest_results.csv", index=False)
    pd.DataFrame(calibration_bins(rows)).to_csv(out / "v20_backtest_calibration_bins.csv", index=False)
    (out / "v20_no_leakage_backtest_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    report = write_backtest_report(metrics, out)
    (out / "v20_no_leakage_backtest_dashboard.md").write_text(f"# v2.0 No-Leakage Backtest\n\n- status: READY\n- matches_total: {metrics['matches_total']}\n", encoding="utf-8")
    return {"v20_no_leakage_backtest_status": "READY" if rows else "BLOCKED", **metrics, "v20_no_leakage_backtest_report_path": report, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
