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
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context  # noqa: E402
from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality  # noqa: E402
from football_prediction_v19.analysis.v21_canonical_match_resolver import resolve_canonical_match  # noqa: E402
from football_prediction_v19.analysis.v21_prediction_eligibility import evaluate_prediction_eligibility  # noqa: E402
from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog  # noqa: E402
from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy  # noqa: E402
from football_prediction_v19.analysis.v21_winner_feature_store import build_winner_feature_store  # noqa: E402
from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core  # noqa: E402


def run_v21_predict_winner(**kwargs: object) -> dict[str, object]:
    context = build_match_context(str(kwargs["home_team"]), str(kwargs["away_team"]), str(kwargs["competition"]), str(kwargs["season"]), str(kwargs["match_date"]), kickoff_time=str(kwargs.get("kickoff_time", "")))
    out = Path(str(kwargs.get("output_dir") or f"outputs/analysis_preview/v21_winner_{context.match_id}"))
    out.mkdir(parents=True, exist_ok=True)
    catalog_dir = out / "catalog"
    catalog = build_v21_season_fixture_catalog(
        context.competition,
        context.season,
        catalog_dir,
        source_profile=str(kwargs.get("source_profile", "config/v20_internet_sources.yaml")),
        enable_network=bool(kwargs.get("enable_network", False)),
        cache_only=bool(kwargs.get("cache_only", False)),
        cache_dir=kwargs.get("cache_dir") or None,
        mock_data_dir=kwargs.get("mock_data_dir") or None,
    )
    resolution = resolve_canonical_match(context.home_team, context.away_team, context.competition, context.season, context.match_date, catalog_path=catalog["season_fixture_catalog_csv_path"], output_dir=out)
    engine = run_v20_historical_internet_prediction(**{**kwargs, "match_date": context.match_date, "output_dir": out / "v20_asof", "base_dir": ROOT})
    coverage = {
        "prediction_tier": (resolution.selected_match or {}).get("prediction_tier", "UNSUPPORTED"),
        "table_available": engine.get("table_available"),
        "xg_available": engine.get("xg_available"),
        "odds_available": engine.get("odds_available"),
        "prior_matches_count": 5,
    }
    eligibility = evaluate_prediction_eligibility(resolution.to_dict(), coverage, {"leakage_status": engine.get("leakage_status")}, out)
    quality = compute_real_source_quality(resolution.status if resolution.status == "RESOLVED" else "PARTIAL", {"table_available": engine.get("table_available"), "form_available": engine.get("table_available"), "xg_available": engine.get("xg_available"), "odds_available": engine.get("odds_available")}, str(engine.get("leakage_status")), bool(engine.get("cache_used")), output_dir=out)
    selected = resolution.selected_match or {"canonical_match_id": context.match_id, "match_date": context.match_date, "home_team": context.home_team, "away_team": context.away_team, "prediction_tier": coverage["prediction_tier"]}
    store = build_winner_feature_store(selected, engine.get("features", {}), eligibility, quality, out)
    model = run_winner_model_core(store["features"], eligibility, out)
    decision = apply_winner_decision_policy(model, eligibility, store["features"], out)
    result = {
        "v21_winner_prediction_status": "READY" if decision["decision_class"] not in {"DATA_BLOCKED"} else "BLOCKED",
        "canonical_fixture_status": resolution.status,
        "eligibility_class": eligibility["eligibility_class"],
        "model_status": model["model_status"],
        "decision_class": decision["decision_class"],
        "predicted_winner": decision["predicted_winner"],
        "winner_team": decision["winner_team"],
        "home_win_probability": decision["home_win_probability"],
        "draw_probability": decision["draw_probability"],
        "away_win_probability": decision["away_win_probability"],
        "confidence": decision["confidence"],
        "source_quality_band": quality["source_quality_band"],
        "network_calls_enabled": bool(kwargs.get("enable_network", False)) and not bool(kwargs.get("cache_only", False)),
        "cache_used": bool(catalog.get("cache_used") or engine.get("cache_used")),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "canonical_resolution": resolution.to_dict(),
        "eligibility": eligibility,
        "winner_model": model,
        "winner_decision": decision,
    }
    _write_final_outputs(out, result)
    return result


def _write_final_outputs(out: Path, result: dict[str, object]) -> None:
    (out / "v21_winner_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "final_winner_report.md").write_text("# v2.1 Final Winner Report\n\n" + json.dumps({k: result[k] for k in ["decision_class", "predicted_winner", "winner_team", "confidence", "source_quality_band"]}, indent=2) + "\n\nNo automatic betting. No stake. No ROI.\n", encoding="utf-8")
    pd.DataFrame([{"artifact_name": p.name, "path": str(p.resolve())} for p in out.iterdir() if p.is_file()]).to_csv(out / "artifact_index.csv", index=False)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--home-team", required=True); p.add_argument("--away-team", required=True); p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--match-date", required=True); p.add_argument("--kickoff-time", default="")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", default=""); p.add_argument("--mock-data-dir", default=""); p.add_argument("--cache-dir", default=""); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true")
    result = run_v21_predict_winner(**vars(p.parse_args(argv)))
    for key in ["v21_winner_prediction_status", "canonical_fixture_status", "eligibility_class", "model_status", "decision_class", "predicted_winner", "winner_team", "home_win_probability", "draw_probability", "away_win_probability", "confidence", "source_quality_band", "network_calls_enabled", "cache_used", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
