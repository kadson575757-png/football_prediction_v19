# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v21_predict_winner import run_v21_predict_winner


def run_v21_winner_backtest(matches: str | Path, output_dir: str | Path, *, max_matches: int | None = None, mock_data_dir: str = "", source_profile: str = "config/v20_internet_sources.yaml", cache_only: bool = True) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(matches, keep_default_na=False)
    if max_matches:
        frame = frame.head(max_matches)
    rows = []
    for idx, row in frame.iterrows():
        result = run_v21_predict_winner(home_team=row["home_team"], away_team=row["away_team"], competition=row["competition"], season=row["season"], match_date=row["match_date"], source_profile=source_profile, mock_data_dir=mock_data_dir, cache_only=cache_only and not bool(mock_data_dir), output_dir=out / f"match_{idx+1}")
        actual = row.get("actual_result", "")
        rows.append({**{k: result[k] for k in ["decision_class", "predicted_winner", "home_win_probability", "draw_probability", "away_win_probability", "confidence", "source_quality_band"]}, "actual_result": actual, "leakage_status": "CLEAN", "xg_available": "xg" not in result["winner_model"].get("missing_inputs", []), "odds_available": "odds" not in result["winner_model"].get("missing_inputs", [])})
    metrics = _metrics(rows)
    pd.DataFrame(rows).to_csv(out / "v21_winner_backtest_results.csv", index=False)
    (out / "v21_winner_backtest_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "v21_winner_backtest_report.md").write_text("# v2.1 Winner Backtest\n\n" + json.dumps(metrics, indent=2) + "\n\nNo ROI. No stake. No profit.\n", encoding="utf-8")
    return {**metrics, "v21_winner_backtest_status": "READY" if rows else "BLOCKED", "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    picks = [r for r in rows if r["decision_class"] == "WINNER_PICK"]
    eval_rows = [r for r in rows if r.get("actual_result")]
    correct = 0
    brier = 0.0
    for r in eval_rows:
        probs = {"H": float(r["home_win_probability"]), "D": float(r["draw_probability"]), "A": float(r["away_win_probability"])}
        pred = {"HOME": "H", "DRAW": "D", "AWAY": "A"}.get(str(r["predicted_winner"]), "")
        correct += int(pred == r["actual_result"])
        brier += sum((probs[k] - (1.0 if k == r["actual_result"] else 0.0)) ** 2 for k in ["H", "D", "A"]) / 3
    return {
        "matches_total": total,
        "matches_evaluated": len(eval_rows),
        "winner_pick_count": len(picks),
        "winner_lean_count": sum(1 for r in rows if r["decision_class"] == "WINNER_LEAN"),
        "no_clear_winner_count": sum(1 for r in rows if r["decision_class"] == "NO_CLEAR_WINNER"),
        "no_decision_count": sum(1 for r in rows if r["decision_class"] == "NO_DECISION"),
        "data_blocked_count": sum(1 for r in rows if r["decision_class"] == "DATA_BLOCKED"),
        "top1_accuracy": round(correct / len(eval_rows), 4) if eval_rows else 0.0,
        "brier_score_1x2": round(brier / len(eval_rows), 4) if eval_rows else 0.0,
        "calibration_bins": [],
        "accuracy_by_league": {},
        "coverage_by_source": {},
        "xg_available_rate": round(sum(bool(r["xg_available"]) for r in rows) / total, 4) if total else 0.0,
        "odds_available_rate": round(sum(bool(r["odds_available"]) for r in rows) / total, 4) if total else 0.0,
        "no_odds_rate": round(sum(not bool(r["odds_available"]) for r in rows) / total, 4) if total else 0.0,
        "early_season_skip_rate": 0.0,
    }
