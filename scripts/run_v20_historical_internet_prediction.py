# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_asof_feature_store import build_asof_feature_store  # noqa: E402
from football_prediction_v19.analysis.v20_asof_source_merger import merge_asof_sources  # noqa: E402
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff  # noqa: E402
from football_prediction_v19.analysis.v20_existing_source_inventory import build_existing_source_inventory  # noqa: E402
from football_prediction_v19.analysis.v20_final_historical_analyst_report import write_final_historical_analyst_report  # noqa: E402
from football_prediction_v19.analysis.v20_football_data_asof_adapter import build_football_data_asof  # noqa: E402
from football_prediction_v19.analysis.v20_historical_internet_prediction_dashboard import write_v20_dashboard  # noqa: E402
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context  # noqa: E402
from football_prediction_v19.analysis.v20_historical_model_engine import run_v20_model_engine  # noqa: E402
from football_prediction_v19.analysis.v20_leakage_guard import SourceSnapshot, run_leakage_guard  # noqa: E402
from football_prediction_v19.analysis.v20_odds_asof_adapter import build_odds_asof  # noqa: E402
from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine  # noqa: E402
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof  # noqa: E402

STATUS = "V20_HISTORICAL_INTERNET_PREDICTION_READY"


def run_v20_historical_internet_prediction(**kwargs: object) -> dict[str, object]:
    base = Path(kwargs.get("base_dir", ROOT)).resolve()
    out = _resolve(kwargs["output_dir"], base); out.mkdir(parents=True, exist_ok=True)
    mock = _resolve(kwargs["mock_data_dir"], base)
    context = resolve_analysis_cutoff(build_match_context(str(kwargs["home_team"]), str(kwargs["away_team"]), str(kwargs["competition"]), str(kwargs["season"]), str(kwargs["match_date"]), kickoff_time=str(kwargs.get("kickoff_time", "")), cutoff_policy=str(kwargs.get("cutoff_policy", "MATCH_DATE_START"))))
    inventory = build_existing_source_inventory(out, repo_root=base)
    football = build_football_data_asof(mock / "football_data_matches_mock.csv", context, out)
    xg = build_understat_xg_asof(mock / "understat_xg_matches_mock.csv", mock / "understat_player_xg_mock.csv", context, out)
    odds = build_odds_asof(mock / "historical_odds_mock.csv", mock / "historical_totals_odds_mock.csv", context, out)
    snapshots = [
        SourceSnapshot("football_data", "results", context.analysis_cutoff, football.get("matches_used", 0), True),
        SourceSnapshot("understat_xg", "xg", context.analysis_cutoff, 1, True),
        SourceSnapshot("historical_odds", "odds", context.analysis_cutoff, 1, True),
    ]
    leakage = run_leakage_guard(context, snapshots, out)
    merged = merge_asof_sources(football, xg, odds, leakage, out)
    store = build_asof_feature_store(context, football, xg, odds, merged, out)
    model = run_v20_model_engine(store["features"], out)
    decision = run_tip_decision_engine(model, merged["asof_status"], store["features"], out)
    analyst_report = write_final_historical_analyst_report(context, leakage, merged, store["features"], model, decision, out)
    artifact_paths = {
        "existing_source_inventory": inventory["existing_source_inventory_md_path"],
        "leakage_guard_report": leakage["leakage_guard_report_path"],
        "football_data_asof_report": football["football_data_asof_report_path"],
        "understat_xg_asof_report": xg["understat_xg_asof_report_path"],
        "odds_asof_report": odds["odds_asof_report_path"],
        "asof_feature_store_report": store["asof_feature_store_report_path"],
        "v20_model_report": model["v20_model_report_path"],
        "v20_tip_decision_card": decision["v20_tip_decision_card_path"],
        "v20_tip_decision_audit": decision["v20_tip_decision_audit_path"],
        "v20_final_historical_analyst_report": analyst_report,
    }
    payload = {"v20_historical_internet_prediction_status": STATUS, "match_context": context.to_dict(), "analysis_cutoff": context.analysis_cutoff, "existing_source_inventory_status": inventory["existing_source_inventory_status"], "asof_status": merged["asof_status"], "leakage_status": leakage["leakage_status"], "model_status": model["model_status"], "decision_class": decision["decision_class"], "primary_tip": decision["primary_tip"], "confidence": decision["confidence"], "coverage": {k: merged.get(k) for k in ["table_available", "xg_available", "odds_1x2_available", "odds_totals_available"]}, "features": store["features"], "probabilities": {"home": model["home_win_probability"], "draw": model["draw_probability"], "away": model["away_win_probability"]}, "artifact_paths": artifact_paths, "network_calls_enabled": bool(kwargs.get("enable_network", False)), "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    dashboard = write_v20_dashboard(out, payload); artifact_paths["dashboard"] = dashboard
    result_path = out / "v20_historical_internet_prediction_result.json"; result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    bundle = out / "v20_historical_internet_prediction_bundle_index.csv"; pd.DataFrame([{"artifact_name": k, "path": v, "status": "READY" if Path(v).exists() else "MISSING"} for k, v in artifact_paths.items()]).to_csv(bundle, index=False)
    return {**payload, "v20_historical_internet_prediction_dashboard_path": dashboard, "v20_historical_internet_prediction_result_json_path": str(result_path.resolve()), "v20_historical_internet_prediction_bundle_index_path": str(bundle.resolve()), "table_available": merged["table_available"], "xg_available": merged["xg_available"], "odds_available": merged["odds_1x2_available"]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--home-team", required=True); p.add_argument("--away-team", required=True); p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--match-date", required=True); p.add_argument("--kickoff-time", default="")
    p.add_argument("--cutoff-policy", default="MATCH_DATE_START"); p.add_argument("--mock-data-dir", required=True); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", required=True); p.add_argument("--enable-network", action="store_true"); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT))
    args = p.parse_args(argv)
    result = run_v20_historical_internet_prediction(**vars(args))
    for key in ["v20_historical_internet_prediction_status", "asof_status", "leakage_status", "model_status", "decision_class", "primary_tip", "confidence", "table_available", "xg_available", "odds_available", "network_calls_enabled", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        print(f"{key}={str(result.get(key)).lower() if isinstance(result.get(key), bool) else result.get(key)}")
    return 0


def _resolve(path: object, base: Path) -> Path:
    p = Path(str(path))
    return p.resolve() if p.is_absolute() else (base / p).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
