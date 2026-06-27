# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_v20_real_match_autopilot import run_v20_real_match_autopilot  # noqa: E402


def run_v20_real_match_validation_batch(matches: str | Path, output_dir: str | Path, **kwargs: object) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    rows = _read_matches(matches)
    results = []
    for i, row in enumerate(rows):
        try:
            result = run_v20_real_match_autopilot(**{**kwargs, **row, "output_dir": out / f"match_{i+1}"})
            results.append({"match_id": result["match_context"]["match_id"], "status": result["v20_real_match_autopilot_status"], "decision_class": result["decision_class"], "source_quality_band": result["source_quality_band"], "error": ""})
        except Exception as exc:
            results.append({"match_id": row.get("home_team", "") + "_vs_" + row.get("away_team", ""), "status": "FAILED", "decision_class": "DATA_BLOCKED", "source_quality_band": "BLOCKED", "error": str(exc)})
    frame = pd.DataFrame(results)
    status = "READY" if not frame.empty and not frame["status"].eq("FAILED").all() else "BLOCKED"
    frame.to_csv(out / "v20_real_match_validation_batch_results.csv", index=False)
    (out / "v20_real_match_validation_batch_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    frame.groupby("source_quality_band").size().reset_index(name="count").to_csv(out / "v20_validation_source_coverage_summary.csv", index=False)
    frame.groupby("decision_class").size().reset_index(name="count").to_csv(out / "v20_validation_decision_summary.csv", index=False)
    (out / "v20_validation_missing_data_summary.md").write_text("# v2.0 Validation Missing Data Summary\n\nFailures are isolated per match.\n", encoding="utf-8")
    (out / "v20_real_match_validation_batch_dashboard.md").write_text(f"# v2.0 Validation Batch\n\n- status: {status}\n- matches_total: {len(rows)}\n", encoding="utf-8")
    return {"v20_real_match_validation_batch_status": status, "matches_total": len(rows), "matches_evaluated": len(results), "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--matches", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--mock-data-dir", default=""); p.add_argument("--cache-only", action="store_true"); p.add_argument("--enable-network", action="store_true"); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT))
    args = p.parse_args(argv)
    result = run_v20_real_match_validation_batch(args.matches, args.output_dir, source_profile=args.source_profile, mock_data_dir=args.mock_data_dir, cache_only=args.cache_only, enable_network=args.enable_network, base_dir=args.base_dir)
    for key in ["v20_real_match_validation_batch_status", "matches_total", "matches_evaluated", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        print(f"{key}={str(result.get(key)).lower() if isinstance(result.get(key), bool) else result.get(key)}")
    return 0


def _read_matches(path: str | Path) -> list[dict[str, str]]:
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".csv":
        return pd.read_csv(path, keep_default_na=False).to_dict("records")
    rows = []
    current: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            line = line[2:]
        if ":" in line:
            key, val = line.split(":", 1)
            current[key.strip()] = val.strip().strip('"')
    if current:
        rows.append(current)
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
