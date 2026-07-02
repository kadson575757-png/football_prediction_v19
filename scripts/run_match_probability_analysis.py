# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2102_probability_output_schema import PROBABILITY_RUNNER_OUTPUT_FIELDS  # noqa: E402
from football_prediction_v19.analysis.v2104_draw_tendency_indicator import build_draw_tendency_indicator  # noqa: E402
from football_prediction_v19.analysis.v2104_goal_margin_profile_indicator import build_goal_margin_profile_indicator  # noqa: E402
from football_prediction_v19.analysis.v2104_indicator_shadow_mix import build_indicator_shadow_mix  # noqa: E402
from football_prediction_v19.analysis.v2104_venue_result_rate_indicator import build_venue_result_rate_indicator  # noqa: E402
from football_prediction_v19.analysis.v2104_venue_scoring_balance_indicator import build_venue_scoring_balance_indicator  # noqa: E402
from football_prediction_v19.analysis.v2105_clean_sheet_failed_to_score_indicator import build_clean_sheet_failed_to_score_indicator  # noqa: E402
from football_prediction_v19.analysis.v2105_comeback_blown_lead_indicator import build_comeback_blown_lead_indicator  # noqa: E402
from football_prediction_v19.analysis.v2105_combined_indicator_shadow_mix import build_combined_indicator_shadow_mix  # noqa: E402
from football_prediction_v19.analysis.v2105_further_indicator_shadow_mix import build_v2105_further_indicator_shadow_mix  # noqa: E402
from football_prediction_v19.analysis.v2105_rest_days_congestion_indicator import build_rest_days_congestion_indicator  # noqa: E402
from football_prediction_v19.analysis.v2105_table_strength_gap_indicator import build_table_strength_gap_indicator  # noqa: E402
from scripts.run_match_winner_analysis import run_match_winner_analysis  # noqa: E402


PROBABILITY_OUTPUT_KEYS = PROBABILITY_RUNNER_OUTPUT_FIELDS


def run_match_probability_analysis(**kwargs: object) -> dict[str, object]:
    output_dir = kwargs.get("output_dir") or ROOT / "outputs" / "probability_analysis"
    result = run_match_winner_analysis(**{**kwargs, "output_dir": output_dir})
    result.update(_v2104_indicator_fields(result, kwargs))
    result.update(_v2105_indicator_fields(result, kwargs))
    probability = {key: result.get(key) for key in PROBABILITY_OUTPUT_KEYS if key != "probability_analysis_status"}
    probability["probability_analysis_status"] = "READY"
    probability["automatic_betting_enabled"] = False
    probability["staking_logic_enabled"] = False
    probability["roi_logic_enabled"] = False
    return probability


def _v2104_indicator_fields(result: dict[str, object], kwargs: dict[str, object]) -> dict[str, object]:
    base_home = float(result.get("base_home_win_probability", result.get("home_win_probability", 0.0)) or 0.0)
    base_draw = float(result.get("base_draw_probability", result.get("draw_probability", 0.0)) or 0.0)
    base_away = float(result.get("base_away_probability", result.get("away_win_probability", 0.0)) or 0.0)
    common = {
        "competition": str(result.get("competition", kwargs.get("competition", ""))),
        "season": str(result.get("season", kwargs.get("season", ""))),
        "home_team": str(result.get("home_team", kwargs.get("home", ""))),
        "away_team": str(result.get("away_team", kwargs.get("away", ""))),
        "match_date": str(result.get("match_date", kwargs.get("match_date", ""))),
        "base_home_probability": base_home,
        "base_draw_probability": base_draw,
        "base_away_probability": base_away,
        "source_profile": str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"),
        "cache_only": bool(kwargs.get("cache_only", False)),
        "enable_network": bool(kwargs.get("enable_network", False)),
    }
    indicator_results = [
        build_draw_tendency_indicator(**common),
        build_venue_result_rate_indicator(**common),
        build_goal_margin_profile_indicator(**common),
        build_venue_scoring_balance_indicator(**common),
    ]
    fields: dict[str, object] = {}
    for indicator in indicator_results:
        fields.update(indicator)
    fields.update(build_indicator_shadow_mix(base_home, base_draw, base_away, indicator_results))
    return fields


def _v2105_indicator_fields(result: dict[str, object], kwargs: dict[str, object]) -> dict[str, object]:
    base_home = float(result.get("base_home_win_probability", result.get("home_win_probability", 0.0)) or 0.0)
    base_draw = float(result.get("base_draw_probability", result.get("draw_probability", 0.0)) or 0.0)
    base_away = float(result.get("base_away_probability", result.get("away_win_probability", 0.0)) or 0.0)
    common = {
        "competition": str(result.get("competition", kwargs.get("competition", ""))),
        "season": str(result.get("season", kwargs.get("season", ""))),
        "home_team": str(result.get("home_team", kwargs.get("home", ""))),
        "away_team": str(result.get("away_team", kwargs.get("away", ""))),
        "match_date": str(result.get("match_date", kwargs.get("match_date", ""))),
        "base_home_probability": base_home,
        "base_draw_probability": base_draw,
        "base_away_probability": base_away,
        "source_profile": str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"),
        "cache_only": bool(kwargs.get("cache_only", False)),
        "enable_network": bool(kwargs.get("enable_network", False)),
    }
    indicator_results = [
        build_clean_sheet_failed_to_score_indicator(**common),
        build_rest_days_congestion_indicator(**common),
        build_table_strength_gap_indicator(**common),
        build_comeback_blown_lead_indicator(**common),
    ]
    fields: dict[str, object] = {}
    for indicator in indicator_results:
        fields.update(indicator)
    fields.update(build_v2105_further_indicator_shadow_mix(base_home, base_draw, base_away, indicator_results))
    v2104_indicators = [
        _slice_indicator_fields(result, "dt", "DRAW_TENDENCY"),
        _slice_indicator_fields(result, "vr", "VENUE_RESULT_RATE"),
        _slice_indicator_fields(result, "gm", "GOAL_MARGIN_PROFILE"),
        _slice_indicator_fields(result, "vsb", "VENUE_SCORING_BALANCE"),
    ]
    fields.update(build_combined_indicator_shadow_mix(base_home, base_draw, base_away, v2104_indicators + indicator_results))
    return fields


def _slice_indicator_fields(source: dict[str, object], prefix: str, name: str) -> dict[str, object]:
    out = {key: value for key, value in source.items() if key.startswith(f"{prefix}_")}
    out["indicator_name"] = name
    out["indicator_quality"] = source.get(f"{prefix}_indicator_quality", "LOW")
    out["adjustment_applied"] = source.get(f"{prefix}_adjustment_applied", False)
    out["adjusted_home_win_probability"] = source.get(f"{prefix}_adjusted_home_win_probability", 0.0)
    out["adjusted_draw_probability"] = source.get(f"{prefix}_adjusted_draw_probability", 0.0)
    out["adjusted_away_probability"] = source.get(f"{prefix}_adjusted_away_probability", 0.0)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--match-date", default="")
    parser.add_argument("--as-of-date", default="")
    parser.add_argument("--allow-post-match-analysis", action="store_true")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--emit-all", action="store_true")
    result = run_match_probability_analysis(**vars(parser.parse_args(argv)))
    for key in PROBABILITY_OUTPUT_KEYS:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
