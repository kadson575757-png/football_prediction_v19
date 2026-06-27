# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff  # noqa: E402
from football_prediction_v19.analysis.v20_football_data_live_adapter import football_data_candidate_matches, run_football_data_live_adapter  # noqa: E402
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context  # noqa: E402
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league  # noqa: E402
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter, understat_candidate_matches  # noqa: E402


def run_search_v20_real_fixtures(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs["output_dir"])); out.mkdir(parents=True, exist_ok=True)
    team = str(kwargs["team"])
    opponent = str(kwargs.get("opponent", ""))
    match_date = str(kwargs.get("date_from") or "2026-02-14")
    context = resolve_analysis_cutoff(build_match_context(team, opponent or team, str(kwargs["competition"]), str(kwargs["season"]), match_date))
    mapping = resolve_source_league(str(kwargs["competition"]), str(kwargs["season"]), out)
    fallback = Path(str(kwargs.get("mock_data_dir") or "")) if kwargs.get("mock_data_dir") else None
    cache_root = Path(str(kwargs.get("cache_dir") or "")) if kwargs.get("cache_dir") else out / "cache"
    football = run_football_data_live_adapter(mapping, context, out, enable_network=bool(kwargs.get("enable_network")), cache_dir=cache_root, mock_csv_path=(fallback / "football_data_live_mock.csv") if fallback and (fallback / "football_data_live_mock.csv").exists() else None)
    understat = run_understat_live_adapter(mapping, context, out, enable_network=bool(kwargs.get("enable_network")), cache_dir=cache_root, mock_json_path=(fallback / "understat_league_mock.json") if fallback and (fallback / "understat_league_mock.json").exists() else None)
    rows = []
    if Path(football.get("football_data_live_normalized_path", "")).exists():
        df = pd.read_csv(football["football_data_live_normalized_path"], keep_default_na=False)
        rows.extend(_filter_candidates(football_data_candidate_matches(df, team, opponent or "", match_date), kwargs))
    if Path(understat.get("understat_live_matches_normalized_path", "")).exists():
        df = pd.read_csv(understat["understat_live_matches_normalized_path"], keep_default_na=False)
        rows.extend(_filter_candidates(understat_candidate_matches(df, team, opponent or "", match_date), kwargs))
    status = "READY" if rows else ("PARTIAL" if football.get("records_count") or understat.get("records_count") else "BLOCKED")
    pd.DataFrame(rows).to_csv(out / "fixture_search_results.csv", index=False)
    (out / "fixture_search_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "fixture_search_report.md").write_text(f"# v2.0 Fixture Search\n\n- status: {status}\n- matches_found: {len(rows)}\n- football_data_status: {football.get('football_data_live_status')}\n- understat_status: {understat.get('understat_live_status')}\n", encoding="utf-8")
    return {"fixture_search_status": status, "matches_found": len(rows), "football_data_status": football.get("football_data_live_status"), "understat_status": understat.get("understat_live_status"), "cache_used": bool(football.get("cache_used") or understat.get("cache_used")), "network_calls_enabled": bool(kwargs.get("enable_network"))}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--team", required=True); p.add_argument("--opponent", default=""); p.add_argument("--date-from", default=""); p.add_argument("--date-to", default="")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", required=True); p.add_argument("--mock-data-dir", default=""); p.add_argument("--cache-dir", default=""); p.add_argument("--enable-network", action="store_true"); p.add_argument("--emit-all", action="store_true")
    args = p.parse_args(argv)
    result = run_search_v20_real_fixtures(**vars(args))
    for key in ["fixture_search_status", "matches_found", "football_data_status", "understat_status", "cache_used", "network_calls_enabled"]:
        print(f"{key}={str(result.get(key)).lower() if isinstance(result.get(key), bool) else result.get(key)}")
    return 0


def _filter_candidates(rows: list[dict[str, object]], kwargs: dict[str, object]) -> list[dict[str, object]]:
    date_from = pd.to_datetime(kwargs.get("date_from"), errors="coerce") if kwargs.get("date_from") else None
    date_to = pd.to_datetime(kwargs.get("date_to"), errors="coerce") if kwargs.get("date_to") else None
    filtered = []
    for row in rows:
        dt = pd.to_datetime(row.get("date"), errors="coerce", format="%Y-%m-%d")
        if pd.isna(dt):
            dt = pd.to_datetime(row.get("date"), errors="coerce", dayfirst=True)
        if date_from is not None and pd.notna(dt) and dt < date_from:
            continue
        if date_to is not None and pd.notna(dt) and dt > date_to:
            continue
        filtered.append(row)
    return filtered


if __name__ == "__main__":
    raise SystemExit(main())
