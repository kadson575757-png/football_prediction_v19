# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_v21_predict_winner import run_v21_predict_winner  # noqa: E402


def run_v21_predict_winners_batch(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs.get("output_dir") or "outputs/analysis_preview/v21_winner_batch"))
    out.mkdir(parents=True, exist_ok=True)
    matches = _matches(kwargs)
    rows = []
    for idx, match in enumerate(matches, start=1):
        result = run_v21_predict_winner(**{**kwargs, **match, "output_dir": out / f"match_{idx}"})
        rows.append({
            "match_id": result["canonical_resolution"].get("canonical_match_id", ""),
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "match_date": match["match_date"],
            "decision_class": result["decision_class"],
            "predicted_winner": result["predicted_winner"],
            "winner_team": result["winner_team"],
            "home_win_probability": result["home_win_probability"],
            "draw_probability": result["draw_probability"],
            "away_win_probability": result["away_win_probability"],
            "confidence": result["confidence"],
            "source_quality_band": result["source_quality_band"],
            "eligibility_class": result["eligibility_class"],
            "missing_data": result["winner_model"].get("missing_inputs", []),
            "no_decision_reason": result["winner_decision"].get("why_not_stronger", ""),
        })
    frame = pd.DataFrame(rows)
    frame.to_csv(out / "v21_winner_batch_results.csv", index=False)
    (out / "v21_winner_batch_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    frame[frame["decision_class"].isin(["NO_DECISION", "DATA_BLOCKED", "NO_CLEAR_WINNER"])].to_csv(out / "v21_winner_batch_no_decision_report.csv", index=False)
    (out / "v21_winner_batch_no_decision_report.md").write_text("# v2.1 Winner Batch No Decision Report\n\n" + frame.to_csv(index=False), encoding="utf-8")
    frame[["match_id", "source_quality_band", "eligibility_class"]].to_csv(out / "v21_winner_batch_source_coverage.csv", index=False)
    (out / "v21_winner_batch_dashboard.md").write_text(f"# v2.1 Winner Batch\n\n- matches_total: {len(frame)}\n- winner_pick_count: {int(frame['decision_class'].eq('WINNER_PICK').sum()) if not frame.empty else 0}\n", encoding="utf-8")
    return {"v21_winner_batch_status": "READY" if rows else "BLOCKED", "matches_total": len(rows), "winner_pick_count": int(frame["decision_class"].eq("WINNER_PICK").sum()) if not frame.empty else 0, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _matches(kwargs: dict[str, object]) -> list[dict[str, str]]:
    if kwargs.get("matches"):
        path = Path(str(kwargs["matches"]))
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return list(data.get("matches", data))
        return pd.read_csv(path, keep_default_na=False).to_dict(orient="records")
    return [{"home_team": "Demo Home", "away_team": "Demo Away", "competition": str(kwargs["competition"]), "season": str(kwargs["season"]), "match_date": str(kwargs["date"])}]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--competition", default="Demo League"); p.add_argument("--season", default="2025/26"); p.add_argument("--date", default="2026-02-15"); p.add_argument("--matches", default="")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", default=""); p.add_argument("--mock-data-dir", default=""); p.add_argument("--cache-dir", default=""); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true")
    result = run_v21_predict_winners_batch(**vars(p.parse_args(argv)))
    for key in ["v21_winner_batch_status", "matches_total", "winner_pick_count", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
