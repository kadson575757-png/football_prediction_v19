# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_api_football_optional_adapter import run_api_football_optional_adapter
from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
from football_prediction_v19.analysis.v20_odds_api_historical_adapter import run_odds_api_historical_adapter
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter


def run_v20_live_source_orchestrator(
    context: HistoricalMatchContext,
    output_dir: str | Path,
    *,
    source_profile: str | Path | None = None,
    enable_network: bool = False,
    cache_only: bool = False,
    cache_dir: str | Path | None = None,
    local_fallback_dir: str | Path | None = None,
) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    mapping = resolve_source_league(context.competition, context.season, out)
    fallback = Path(local_fallback_dir) if local_fallback_dir else None
    cache_root = Path(cache_dir or out / "cache")
    football = run_football_data_live_adapter(
        mapping, context, out, enable_network=enable_network and not cache_only, cache_dir=cache_root,
        mock_csv_path=(fallback / "football_data_live_mock.csv") if fallback and (fallback / "football_data_live_mock.csv").exists() and not cache_only else None,
    )
    xg = run_understat_live_adapter(
        mapping, context, out, enable_network=enable_network and not cache_only, cache_dir=cache_root,
        mock_json_path=(fallback / "understat_league_mock.json") if fallback and (fallback / "understat_league_mock.json").exists() and not cache_only else None,
        mock_players_json_path=(fallback / "understat_players_mock.json") if fallback and (fallback / "understat_players_mock.json").exists() and not cache_only else None,
    )
    odds = run_odds_api_historical_adapter(
        mapping, context, out, enable_network=enable_network and not cache_only, cache_dir=cache_root,
        mock_json_path=(fallback / "odds_api_historical_mock.json") if fallback and (fallback / "odds_api_historical_mock.json").exists() and not cache_only else None,
    )
    api_football = run_api_football_optional_adapter(
        mapping, context, out, enabled=False, enable_network=enable_network and not cache_only,
        mock_json_path=(fallback / "api_football_fixture_mock.json") if fallback and (fallback / "api_football_fixture_mock.json").exists() and not cache_only else None,
    )
    coverage = {
        "football_data_available": bool(football.get("table_available")),
        "xg_available": bool(xg.get("xg_available")),
        "odds_available": bool(odds.get("odds_1x2_available")),
        "lineups_available": bool(api_football.get("lineups_available")),
        "injuries_available": bool(api_football.get("injuries_available")),
    }
    if coverage["football_data_available"] and coverage["xg_available"] and coverage["odds_available"]:
        status = "LIVE_SOURCES_READY"
    elif any(coverage.values()):
        status = "LIVE_SOURCES_PARTIAL"
    else:
        status = "LIVE_SOURCES_BLOCKED"
    result = {
        "live_source_status": status,
        "source_profile": str(source_profile or ""),
        "enable_network": bool(enable_network),
        "cache_only": bool(cache_only),
        "cache_used": any(bool(src.get("cache_used")) for src in [football, xg, odds]),
        "source_league_mapping": mapping.to_dict(),
        "football": football,
        "xg": xg,
        "odds": odds,
        "api_football": api_football,
        **coverage,
    }
    _write_outputs(out, result)
    return result


def _write_outputs(out: Path, result: dict[str, object]) -> None:
    json_path = out / "live_source_results.json"
    csv_path = out / "live_source_results.csv"
    matrix_path = out / "live_source_coverage_matrix.csv"
    reliability_path = out / "live_source_reliability_report.md"
    dashboard_path = out / "live_source_orchestrator_dashboard.md"
    bundle_path = out / "live_source_bundle_index.csv"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([{"source": k, "available": v} for k, v in result.items() if k.endswith("_available")]).to_csv(matrix_path, index=False)
    pd.DataFrame([{"live_source_status": result["live_source_status"], "cache_used": result["cache_used"], "network_enabled": result["enable_network"]}]).to_csv(csv_path, index=False)
    reliability_path.write_text("# v2.0 Live Source Reliability\n\n" + json.dumps({k: result[k] for k in ["live_source_status", "cache_used", "football_data_available", "xg_available", "odds_available"]}, indent=2), encoding="utf-8")
    dashboard_path.write_text("# v2.0 Live Source Orchestrator Dashboard\n\n" + f"- live_source_status: {result['live_source_status']}\n- cache_used: {str(result['cache_used']).lower()}\n- football_data_available: {str(result['football_data_available']).lower()}\n- xg_available: {str(result['xg_available']).lower()}\n- odds_available: {str(result['odds_available']).lower()}\n", encoding="utf-8")
    pd.DataFrame([{"artifact_name": p.stem, "path": str(p.resolve())} for p in [json_path, csv_path, matrix_path, reliability_path, dashboard_path]]).to_csv(bundle_path, index=False)
    result.update({
        "live_source_results_json_path": str(json_path.resolve()),
        "live_source_results_csv_path": str(csv_path.resolve()),
        "live_source_coverage_matrix_path": str(matrix_path.resolve()),
        "live_source_reliability_report_path": str(reliability_path.resolve()),
        "live_source_orchestrator_dashboard_path": str(dashboard_path.resolve()),
        "live_source_bundle_index_path": str(bundle_path.resolve()),
    })
