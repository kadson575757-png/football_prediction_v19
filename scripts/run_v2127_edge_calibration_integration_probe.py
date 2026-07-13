# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2127_edge_calibration_integration import analyze_edge_calibration_integration  # noqa: E402

DEFAULT_PREMIER_ROWS = "outputs/v2124_pl_multi_season_robustness/v2124_combined_rows.csv"
DEFAULT_EXTERNAL_ROWS = "outputs/v2126_external_league_edge_calibration/v2126_external_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2127_edge_calibration_integration_probe"


def run_v2127_edge_calibration_integration_probe(
    *,
    premier_rows: str | Path = DEFAULT_PREMIER_ROWS,
    external_rows: str | Path = DEFAULT_EXTERNAL_ROWS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    premier_path = Path(premier_rows)
    external_path = Path(external_rows)
    premier = pd.read_csv(premier_path, keep_default_na=False) if premier_path.exists() else pd.DataFrame()
    external = pd.read_csv(external_path, keep_default_na=False) if external_path.exists() else pd.DataFrame()
    return analyze_edge_calibration_integration(premier, external, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run isolated v2.12.7 edge calibration integration probe.")
    parser.add_argument("--premier-rows", default=DEFAULT_PREMIER_ROWS)
    parser.add_argument("--external-rows", default=DEFAULT_EXTERNAL_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true", help="Emit all probe artifacts (currently always enabled).")
    args = parser.parse_args(argv)
    result = run_v2127_edge_calibration_integration_probe(
        premier_rows=args.premier_rows, external_rows=args.external_rows, output_dir=args.output_dir,
    )
    keys = [
        "v2127_edge_calibration_integration_probe_status", "rows_loaded", "evaluable_count",
        "adjustment_applied_count", "baseline_hit_rate", "calibrated_hit_rate", "hit_rate_delta",
        "baseline_brier_score", "calibrated_brier_score", "brier_improvement",
        "premier_league_brier_improvement", "external_league_brier_improvement",
        "top_outcome_change_count", "newly_corrected_count", "newly_broken_count",
        "net_corrected_count", "base_probability_parity_mismatch_count",
        "unchanged_row_mismatch_count", "calibration_formula_mismatch_count",
        "invalid_probability_count", "maximum_probability_sum_error",
        "maximum_source_probability_sum_error", "maximum_unchanged_introduced_sum_error",
        "maximum_applied_calibrated_sum_error", "source_sum_warning_count",
        "applied_sum_failure_count", "unchanged_sum_regression_count", "integration_probe_status",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
