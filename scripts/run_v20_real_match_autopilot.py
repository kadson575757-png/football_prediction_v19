# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction  # noqa: E402
from football_prediction_v19.analysis.v20_final_real_match_report import write_v20_final_real_match_report  # noqa: E402
from football_prediction_v19.analysis.v20_real_fixture_resolver import resolve_real_fixture  # noqa: E402
from football_prediction_v19.analysis.v20_real_match_autopilot_dashboard import write_v20_real_match_autopilot_dashboard  # noqa: E402
from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality  # noqa: E402
from football_prediction_v19.analysis.v20_source_readiness_gate import evaluate_source_readiness  # noqa: E402


def run_v20_real_match_autopilot(**kwargs: object) -> dict[str, object]:
    base = Path(kwargs.get("base_dir", ROOT)).resolve()
    out = _resolve(kwargs.get("output_dir") or _default_output(kwargs), base); out.mkdir(parents=True, exist_ok=True)
    engine = run_v20_historical_internet_prediction(**{**kwargs, "output_dir": out, "base_dir": base})
    live = engine.get("live_sources", {})
    source_paths = {
        "football_data": live.get("football", {}).get("football_data_live_normalized_path") or engine.get("artifact_paths", {}).get("football_data_asof_report", ""),
        "understat": live.get("xg", {}).get("understat_live_matches_normalized_path", ""),
        "odds_api": live.get("odds", {}).get("odds_api_normalized_path", ""),
    }
    context_obj = _context_from_engine(engine)
    fixture = resolve_real_fixture(context_obj, source_paths, out)
    coverage = {"table_available": engine.get("table_available"), "form_available": engine.get("table_available"), "xg_available": engine.get("xg_available"), "player_xg_available": engine.get("coverage", {}).get("player_xg_available", False), "odds_available": engine.get("odds_available")}
    readiness = evaluate_source_readiness(fixture.fixture_resolution_status, str(engine.get("asof_status")), str(engine.get("leakage_status")), coverage, out)
    quality = compute_real_source_quality(fixture.fixture_resolution_status, coverage, str(engine.get("leakage_status")), bool(engine.get("cache_used")), output_dir=out)
    status = "READY" if readiness["source_readiness"] == "READY_FOR_MODEL" else ("PARTIAL" if readiness["source_readiness"] in {"READY_FOR_ANALYST_LEAN", "NO_BET_REQUIRED"} else "BLOCKED")
    result = {
        **engine,
        **fixture.to_dict(),
        **readiness,
        **quality,
        "v20_real_match_autopilot_status": status,
        "source_league_mapping": live.get("source_league_mapping", {}),
        "missing_data": ", ".join(readiness.get("readiness_reasons", [])),
        "no_bet_reasons": ", ".join(readiness.get("readiness_reasons", [])) if engine.get("decision_class") in {"NO_BET", "DATA_BLOCKED"} else "",
    }
    report = write_v20_final_real_match_report(result, out)
    dashboard = write_v20_real_match_autopilot_dashboard(result, out)
    result["v20_final_real_match_report_path"] = report
    result["v20_real_match_autopilot_dashboard_path"] = dashboard
    result_path = out / "v20_real_match_autopilot_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([{"artifact_name": k, "path": v} for k, v in result.get("artifact_paths", {}).items()] + [{"artifact_name": "final_real_match_report", "path": report}, {"artifact_name": "dashboard", "path": dashboard}]).to_csv(out / "v20_real_match_autopilot_artifact_index.csv", index=False)
    result["v20_real_match_autopilot_result_json_path"] = str(result_path.resolve())
    return result


def main(argv: list[str] | None = None) -> int:
    p = _parser()
    args = p.parse_args(argv)
    result = run_v20_real_match_autopilot(**vars(args))
    for key in ["v20_real_match_autopilot_status", "fixture_resolution_status", "source_readiness", "source_quality_band", "asof_status", "leakage_status", "model_status", "decision_class", "primary_tip", "confidence", "network_calls_enabled", "cache_used", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        print(f"{key}={_fmt(result.get(key))}")
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--home-team", required=True); p.add_argument("--away-team", required=True); p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--match-date", required=True); p.add_argument("--kickoff-time", default="")
    p.add_argument("--cutoff-policy", default="MATCH_DATE_START"); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--mock-data-dir", default=""); p.add_argument("--output-dir", default=""); p.add_argument("--cache-dir", default=""); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT))
    return p


def _context_from_engine(engine: dict[str, object]):
    from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
    data = engine["match_context"]
    return HistoricalMatchContext(**data)


def _default_output(kwargs: dict[str, object]) -> str:
    safe = "_".join(str(kwargs.get(k, "")).lower().replace(" ", "_") for k in ["home_team", "away_team", "match_date"])
    return f"outputs/analysis_preview/v20_real_match_autopilot_{safe}"


def _resolve(path: object, base: Path) -> Path:
    p = Path(str(path))
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def _fmt(value: object) -> object:
    return str(value).lower() if isinstance(value, bool) else value


if __name__ == "__main__":
    raise SystemExit(main())
