# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_real_match_diagnostics import write_debug_reports  # noqa: E402
from scripts.run_v20_real_match_autopilot import run_v20_real_match_autopilot  # noqa: E402


def run_debug_v20_real_match_sources(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs.get("output_dir") or "outputs/analysis_preview/v20_debug_real_match"))
    result = run_v20_real_match_autopilot(**{**kwargs, "output_dir": out})
    result.update(write_debug_reports(result, out))
    status = "READY" if result.get("source_readiness") == "READY_FOR_MODEL" else ("PARTIAL" if result.get("source_readiness") in {"READY_FOR_ANALYST_LEAN", "NO_BET_REQUIRED"} else "BLOCKED")
    source_status = result.get("source_status", {})
    result["v20_real_source_debug_status"] = status
    result["cache_write_status"] = "WRITTEN" if any(v.get("cache_written") for v in source_status.values()) else "NOT_WRITTEN"
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--home-team", required=True); p.add_argument("--away-team", required=True); p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--match-date", required=True); p.add_argument("--kickoff-time", default="")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--mock-data-dir", default=""); p.add_argument("--output-dir", required=True); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT))
    args = p.parse_args(argv)
    result = run_debug_v20_real_match_sources(**vars(args))
    sources = result.get("source_status", {})
    for key, value in [
        ("v20_real_source_debug_status", result.get("v20_real_source_debug_status")),
        ("fixture_resolution_status", result.get("fixture_resolution_status")),
        ("football_data_status", sources.get("football_data", {}).get("status")),
        ("understat_status", sources.get("understat", {}).get("status")),
        ("odds_api_status", sources.get("odds_api", {}).get("status")),
        ("cache_write_status", result.get("cache_write_status")),
        ("main_block_reason", result.get("main_block_reason")),
        ("recommended_fix", result.get("recommended_fix")),
    ]:
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
