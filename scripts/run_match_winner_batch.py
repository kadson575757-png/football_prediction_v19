# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_match_winner_analysis import run_match_winner_analysis  # noqa: E402


def run_match_winner_batch(**kwargs: object) -> dict[str, object]:
    input_path = Path(str(kwargs.get("input") or "config/v25_match_batch_template.csv"))
    out = Path(str(kwargs.get("output_dir") or Path("outputs/winner_analysis_batch") / datetime.now(UTC).strftime("%Y%m%d_%H%M%S")))
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(input_path, keep_default_na=False)
    rows: list[dict[str, object]] = []
    for idx, row in frame.iterrows():
        result = run_match_winner_analysis(
            competition=row.get("competition", ""),
            season=row.get("season", ""),
            home=row.get("home_team", ""),
            away=row.get("away_team", ""),
            match_date=row.get("match_date", ""),
            source_profile=kwargs.get("source_profile") or "config/v20_internet_sources.yaml",
            cache_only=bool(kwargs.get("cache_only", False)),
            enable_network=bool(kwargs.get("enable_network", False)),
            output_dir=out / f"match_{idx+1}",
        )
        rows.append({k: v for k, v in result.items() if not str(k).endswith("_path")})
    result_frame = pd.DataFrame(rows)
    result_frame.to_csv(out / "winner_batch_results.csv", index=False)
    (out / "winner_batch_results.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    blocked = result_frame[result_frame["decision_class"].astype(str).eq("DATA_BLOCKED")] if not result_frame.empty else pd.DataFrame()
    no_clear = result_frame[result_frame["decision_class"].astype(str).eq("NO_CLEAR_WINNER")] if not result_frame.empty else pd.DataFrame()
    blocked.to_csv(out / "data_blocked_matches.csv", index=False)
    no_clear.to_csv(out / "no_clear_winner_matches.csv", index=False)
    summary = _summary(result_frame, len(frame))
    (out / "winner_batch_report.md").write_text("# v2.5 Winner Batch Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in summary.items()) + "\n\nNo automatic action, no stake, no ROI.\n", encoding="utf-8")
    return {**summary, "winner_batch_results_csv_path": str((out / "winner_batch_results.csv").resolve()), "winner_batch_report_path": str((out / "winner_batch_report.md").resolve())}


def _summary(frame: pd.DataFrame, requested: int) -> dict[str, object]:
    if frame.empty:
        return {"v25_winner_batch_status": "READY", "matches_requested": requested, "matches_analyzed": 0, "winner_pick_count": 0, "winner_lean_count": 0, "no_clear_winner_count": 0, "no_decision_count": 0, "data_blocked_count": 0, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    return {
        "v25_winner_batch_status": "READY",
        "matches_requested": requested,
        "matches_analyzed": int(len(frame)),
        "winner_pick_count": int(frame["decision_class"].eq("WINNER_PICK").sum()),
        "winner_lean_count": int(frame["decision_class"].eq("WINNER_LEAN").sum()),
        "no_clear_winner_count": int(frame["decision_class"].eq("NO_CLEAR_WINNER").sum()),
        "no_decision_count": int(frame["decision_class"].eq("NO_DECISION").sum()),
        "data_blocked_count": int(frame["decision_class"].eq("DATA_BLOCKED").sum()),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="config/v25_match_batch_template.csv")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--emit-all", action="store_true")
    result = run_match_winner_batch(**vars(parser.parse_args(argv)))
    for key in ["v25_winner_batch_status", "matches_requested", "matches_analyzed", "winner_pick_count", "winner_lean_count", "no_clear_winner_count", "no_decision_count", "data_blocked_count", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
