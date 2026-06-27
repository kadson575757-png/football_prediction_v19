# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest  # noqa: E402

DEFAULT_LEAGUES = ["Premier League", "Bundesliga", "Serie A", "La Liga", "Ligue 1"]


def run_v22_multileague_winner_backtest(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs.get("output_dir") or "outputs/backtests/v22/multileague_preview"))
    out.mkdir(parents=True, exist_ok=True)
    leagues = [c.strip() for c in str(kwargs.get("competitions") or ",".join(DEFAULT_LEAGUES)).split(",") if c.strip()]
    rows = []
    for league in leagues:
        result = run_v21_winner_backtest(None, out / league.replace(" ", "_"), competition=league, season=str(kwargs["season"]), max_matches=int(kwargs.get("max_matches_per_league") or 50), mock_data_dir=str(kwargs.get("mock_data_dir") or ""), cache_only=bool(kwargs.get("cache_only")), enable_network=bool(kwargs.get("enable_network")), source_profile=str(kwargs.get("source_profile", "")))
        rows.append({"competition": league, **result})
    frame = pd.DataFrame(rows)
    evaluated = int(frame["matches_evaluated"].sum()) if not frame.empty else 0
    status = "READY" if evaluated >= 10 else ("INSUFFICIENT_SAMPLE" if evaluated > 0 else "FAILED")
    result = {
        "v22_multileague_backtest_status": status,
        "v22_multileague_winner_backtest_status": status,
        "leagues_total": len(leagues),
        "leagues_ready": int(frame["corpus_status"].eq("READY").sum()) if not frame.empty else 0,
        "leagues_insufficient_sample": int(frame["corpus_status"].eq("INSUFFICIENT_SAMPLE").sum()) if not frame.empty else len(leagues),
        "matches_requested_total": int(frame["matches_requested"].sum()) if not frame.empty else 0,
        "matches_available_total": int(frame["matches_available"].sum()) if not frame.empty else 0,
        "matches_evaluated_total": evaluated,
        "total_matches_available": int(frame["matches_available"].sum()) if not frame.empty else 0,
        "evaluated_matches": evaluated,
        "winner_pick_count": int(frame["winner_pick_count"].sum()) if not frame.empty else 0,
        "winner_lean_count": int(frame["winner_lean_count"].sum()) if not frame.empty else 0,
        "no_clear_winner_count": int(frame["no_clear_winner_count"].sum()) if not frame.empty else 0,
        "no_decision_count": int(frame["no_decision_count"].sum()) if not frame.empty else 0,
        "data_blocked_count": int(frame["data_blocked_count"].sum()) if not frame.empty else 0,
        "top1_accuracy": round(float(frame["top1_accuracy"].mean()), 4) if not frame.empty else 0.0,
        "brier_score_1x2": round(float(frame["brier_score_1x2"].mean()), 4) if not frame.empty else 0.0,
        "statistical_validity": "HIGH" if evaluated >= 100 else ("MEDIUM" if evaluated >= 30 else "LOW"),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    frame.to_csv(out / "league_level_metrics.csv", index=False)
    frame.to_csv(out / "multileague_winner_backtest_results.csv", index=False)
    pd.DataFrame([result]).to_csv(out / "decision_class_breakdown.csv", index=False)
    pd.DataFrame([result]).to_csv(out / "source_coverage_breakdown.csv", index=False)
    pd.DataFrame(columns=["bin", "n", "accuracy"]).to_csv(out / "calibration_bins.csv", index=False)
    (out / "insufficient_sample_report.md").write_text("# Insufficient Sample\n\n" + frame.to_csv(index=False), encoding="utf-8")
    (out / "no_decision_report.md").write_text("# No Decision\n\n", encoding="utf-8")
    (out / "data_blocked_report.md").write_text("# Data Blocked\n\n", encoding="utf-8")
    (out / "multileague_winner_backtest_dashboard.md").write_text("# v2.2 Multileague Winner Backtest\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--season", required=True); p.add_argument("--competitions", default=""); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", default=""); p.add_argument("--mock-data-dir", default=""); p.add_argument("--max-matches-per-league", type=int, default=50); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true")
    result = run_v22_multileague_winner_backtest(**vars(p.parse_args(argv)))
    for key in ["v22_multileague_backtest_status", "leagues_total", "leagues_ready", "leagues_insufficient_sample", "matches_requested_total", "matches_available_total", "matches_evaluated_total", "winner_pick_count", "winner_lean_count", "no_clear_winner_count", "no_decision_count", "data_blocked_count", "top1_accuracy", "brier_score_1x2", "statistical_validity", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
