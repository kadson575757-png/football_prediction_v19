# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v25_practical_decision_summary import build_practical_decision_summary  # noqa: E402
from football_prediction_v19.analysis.v25_winner_report import write_winner_report  # noqa: E402
from football_prediction_v19.analysis.v26_asof_guard import evaluate_asof_guard  # noqa: E402
from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date  # noqa: E402
from football_prediction_v19.analysis.v291_home_away_ppg_indicator import build_home_away_ppg_indicator  # noqa: E402
from football_prediction_v19.analysis.v291_ppg_probability_adjustment import apply_home_away_ppg_adjustment  # noqa: E402
from football_prediction_v19.analysis.v292_last5_form_indicator import build_last5_form_indicator  # noqa: E402
from football_prediction_v19.analysis.v292_last5_probability_adjustment import apply_last5_form_shadow_adjustment  # noqa: E402
from scripts.run_v21_predict_winner import run_v21_predict_winner  # noqa: E402


def run_match_winner_analysis(**kwargs: object) -> dict[str, object]:
    home = str(kwargs.get("home") or kwargs.get("home_team") or "")
    away = str(kwargs.get("away") or kwargs.get("away_team") or "")
    competition = str(kwargs.get("competition") or "")
    season = str(kwargs.get("season") or "")
    match_date = str(kwargs.get("match_date") or "")
    out = _output_dir(kwargs.get("output_dir"), home, away)
    resolver = {"resolver_status": "SKIPPED", "source_used": "explicit_match_date", "candidates_count": 0, "reason": "explicit match_date provided", "reversed_fixture_found": False, "alias_matched": False, "match_date": match_date}
    if not match_date:
        resolver = resolve_fixture_date(competition, season, home, away, source_profile=str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"), cache_only=bool(kwargs.get("cache_only", False)), enable_network=bool(kwargs.get("enable_network", False)), corpus_path=kwargs.get("corpus_path") or None)
        if resolver["resolver_status"] == "RESOLVED":
            match_date = str(resolver["match_date"])
        else:
            result = _blocked_result(competition, season, home, away, match_date, "fixture_missing_or_ambiguous", str(resolver["reason"]))
            result.update(_default_ppg_fields(result))
            result.update(_default_last5_fields(result))
            result.update(_resolver_fields(resolver))
            paths = write_winner_report(result, out)
            return {**result, **paths}
    guard = evaluate_asof_guard(match_date, str(kwargs.get("as_of_date") or "") or None, bool(kwargs.get("allow_post_match_analysis", False)))
    if guard["asof_guard_status"] == "BLOCKED":
        result = _blocked_result(competition, season, home, away, match_date, "asof_guard_blocked", str(guard["asof_guard_reason"]))
        result.update(_default_ppg_fields(result))
        result.update(_default_last5_fields(result))
        result.update(_resolver_fields(resolver))
        result.update(guard)
    else:
        try:
            raw = run_v21_predict_winner(
                home_team=home,
                away_team=away,
                competition=competition,
                season=season,
                match_date=match_date,
                source_profile=str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"),
                cache_only=bool(kwargs.get("cache_only", False)),
                enable_network=bool(kwargs.get("enable_network", False)),
                mock_data_dir=kwargs.get("mock_data_dir") or None,
                output_dir=out / "core",
            )
            result = _practical_result(raw, competition, season, home, away, match_date)
            result.update(_ppg_adjustment_fields(result, competition, season, home, away, match_date, kwargs))
            result.update(_last5_adjustment_fields(result, competition, season, home, away, match_date, kwargs))
            result.update(_resolver_fields(resolver))
            result.update(guard)
            if guard["post_match_analysis"]:
                result["recommendation_summary"] = f"{result['recommendation_summary']} Post-match analysis, not pre-match prediction."
        except Exception as exc:  # noqa: BLE001 - practical runner should report readable hard blocks.
            result = _blocked_result(competition, season, home, away, match_date, "fixture_missing_or_ambiguous", f"Winner core could not complete analysis: {type(exc).__name__}.")
            result.update(_default_ppg_fields(result))
            result.update(_default_last5_fields(result))
            result.update(_resolver_fields(resolver))
            result.update(guard)
    paths = write_winner_report(result, out)
    return {**result, **paths}


def _resolver_fields(resolver: dict[str, object]) -> dict[str, object]:
    return {
        "fixture_resolver_status": resolver.get("resolver_status", ""),
        "fixture_resolver_source": resolver.get("source_used", ""),
        "fixture_candidates_count": resolver.get("candidates_count", 0),
        "resolved_match_date": resolver.get("match_date", ""),
        "resolver_reason": resolver.get("reason", ""),
        "reversed_fixture_found": resolver.get("reversed_fixture_found", False),
        "alias_matched": resolver.get("alias_matched", False),
        "fixture_candidates": resolver.get("candidates", []),
    }


def _ppg_adjustment_fields(result: dict[str, object], competition: str, season: str, home: str, away: str, match_date: str, kwargs: dict[str, object]) -> dict[str, object]:
    indicator = build_home_away_ppg_indicator(
        competition,
        season,
        home,
        away,
        match_date,
        source_profile=str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"),
        cache_only=bool(kwargs.get("cache_only", False)),
        enable_network=bool(kwargs.get("enable_network", False)),
    )
    adjusted = apply_home_away_ppg_adjustment(
        result.get("home_win_probability", 0.0),
        result.get("draw_probability", 0.0),
        result.get("away_win_probability", 0.0),
        indicator,
    )
    return {
        **adjusted,
        "ppg_adjusted_home_win_probability": adjusted["adjusted_home_win_probability"],
        "ppg_adjusted_draw_probability": adjusted["adjusted_draw_probability"],
        "ppg_adjusted_away_probability": adjusted["adjusted_away_win_probability"],
        "home_win_probability": adjusted["adjusted_home_win_probability"] if bool(kwargs.get("apply_ppg_adjustment", False)) else adjusted["base_home_win_probability"],
        "draw_probability": adjusted["adjusted_draw_probability"] if bool(kwargs.get("apply_ppg_adjustment", False)) else adjusted["base_draw_probability"],
        "away_win_probability": adjusted["adjusted_away_win_probability"] if bool(kwargs.get("apply_ppg_adjustment", False)) else adjusted["base_away_probability"],
    }


def _default_ppg_fields(result: dict[str, object]) -> dict[str, object]:
    adjusted = apply_home_away_ppg_adjustment(
        result.get("home_win_probability", 0.0),
        result.get("draw_probability", 0.0),
        result.get("away_win_probability", 0.0),
        {"indicator_quality": "LOW", "home_away_ppg_diff": 0.0},
    )
    return {
        **adjusted,
        "ppg_adjusted_home_win_probability": adjusted["adjusted_home_win_probability"],
        "ppg_adjusted_draw_probability": adjusted["adjusted_draw_probability"],
        "ppg_adjusted_away_probability": adjusted["adjusted_away_win_probability"],
        "home_win_probability": adjusted["base_home_win_probability"],
        "draw_probability": adjusted["base_draw_probability"],
        "away_win_probability": adjusted["base_away_probability"],
    }


def _last5_adjustment_fields(result: dict[str, object], competition: str, season: str, home: str, away: str, match_date: str, kwargs: dict[str, object]) -> dict[str, object]:
    indicator = build_last5_form_indicator(
        competition,
        season,
        home,
        away,
        match_date,
        source_profile=str(kwargs.get("source_profile") or "config/v20_internet_sources.yaml"),
        cache_only=bool(kwargs.get("cache_only", False)),
        enable_network=bool(kwargs.get("enable_network", False)),
    )
    return apply_last5_form_shadow_adjustment(
        result.get("base_home_win_probability", result.get("home_win_probability", 0.0)),
        result.get("base_draw_probability", result.get("draw_probability", 0.0)),
        result.get("base_away_probability", result.get("away_win_probability", 0.0)),
        indicator,
    )


def _default_last5_fields(result: dict[str, object]) -> dict[str, object]:
    return apply_last5_form_shadow_adjustment(
        result.get("base_home_win_probability", result.get("home_win_probability", 0.0)),
        result.get("base_draw_probability", result.get("draw_probability", 0.0)),
        result.get("base_away_probability", result.get("away_win_probability", 0.0)),
        {"last5_indicator_quality": "LOW", "last5_points_diff": 0},
    )


def _practical_result(raw: dict[str, object], competition: str, season: str, home: str, away: str, match_date: str) -> dict[str, object]:
    model = raw.get("winner_model", {}) if isinstance(raw.get("winner_model"), dict) else {}
    decision = raw.get("winner_decision", {}) if isinstance(raw.get("winner_decision"), dict) else {}
    missing = [str(x) for x in model.get("missing_inputs", [])] if isinstance(model, dict) else []
    xg_available = "xg" not in missing
    odds_available = "odds" not in missing
    prediction_tier = "TIER_1_FULL" if xg_available else "TIER_2_RESULTS_ONLY"
    risk_notes = []
    if not xg_available:
        risk_notes.append("xG missing; this caps confidence but does not block analysis.")
    if not odds_available:
        risk_notes.append("Odds missing; market context is unavailable but optional.")
    if raw.get("eligibility_class") == "LEAN_ONLY":
        risk_notes.append("Lean-only eligibility limits decision strength.")
    confidence = _num(raw.get("confidence"))
    result = {
        "winner_analysis_status": "READY" if raw.get("decision_class") != "DATA_BLOCKED" else "DATA_BLOCKED",
        "competition": competition,
        "season": season,
        "home_team": home,
        "away_team": away,
        "match_date": match_date,
        "decision_class": raw.get("decision_class", "NO_DECISION"),
        "predicted_winner": raw.get("predicted_winner", "NO_CLEAR_WINNER"),
        "home_win_probability": raw.get("home_win_probability", 0),
        "draw_probability": raw.get("draw_probability", 0),
        "away_win_probability": raw.get("away_win_probability", 0),
        "confidence": confidence,
        "risk_level": "HIGH" if confidence < 0.50 or len(risk_notes) >= 2 else ("MEDIUM" if confidence < 0.65 or risk_notes else "LOW"),
        "source_quality_band": raw.get("source_quality_band", "LOW"),
        "prediction_tier": prediction_tier,
        "xg_available": xg_available,
        "odds_available": odds_available,
        "model_status": raw.get("model_status", "WINNER_MODEL_PARTIAL").replace("READY", "FULL"),
        "primary_reasons": model.get("main_edges", []) or ["Winner model evaluated as-of form and source-quality signals."],
        "risk_notes": risk_notes or model.get("main_risks", []),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "productive_betting_enabled": False,
    }
    summary = build_practical_decision_summary(result)
    result["recommendation_summary"] = f"{summary['final_label']}: {summary['short_reason']} {summary['main_risk']}"
    result["final_label"] = summary["final_label"]
    return result


def _blocked_result(competition: str, season: str, home: str, away: str, match_date: str, code: str, text: str) -> dict[str, object]:
    return {
        "winner_analysis_status": "DATA_BLOCKED",
        "competition": competition,
        "season": season,
        "home_team": home,
        "away_team": away,
        "match_date": match_date,
        "decision_class": "DATA_BLOCKED",
        "predicted_winner": "NO_CLEAR_WINNER",
        "home_win_probability": 0.0,
        "draw_probability": 0.0,
        "away_win_probability": 0.0,
        "confidence": 0.0,
        "risk_level": "HIGH",
        "source_quality_band": "LOW",
        "prediction_tier": "TIER_3_LIMITED",
        "xg_available": False,
        "odds_available": False,
        "model_status": "WINNER_MODEL_BLOCKED",
        "primary_reasons": [],
        "risk_notes": [text],
        "block_reason_code": code,
        "block_reason_text": text,
        "recommendation_summary": f"Data Blocked: {text}",
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "productive_betting_enabled": False,
    }


def _output_dir(base: object, home: str, away: str) -> Path:
    if base:
        out = Path(str(base))
    else:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", f"{home}_vs_{away}".lower()).strip("_")
        out = Path("outputs/winner_analysis") / f"{stamp}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
    parser.add_argument("--apply-ppg-adjustment", action="store_true")
    parser.add_argument("--decision-policy-config", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--emit-all", action="store_true")
    result = run_match_winner_analysis(**vars(parser.parse_args(argv)))
    for key in ["winner_analysis_status", "competition", "season", "home_team", "away_team", "match_date", "fixture_resolver_status", "fixture_resolver_source", "fixture_candidates_count", "resolved_match_date", "resolver_reason", "reversed_fixture_found", "alias_matched", "as_of_date", "post_match_analysis", "leakage_warning", "asof_guard_status", "asof_guard_reason", "decision_class", "predicted_winner", "base_home_win_probability", "base_draw_probability", "base_away_probability", "home_win_probability", "draw_probability", "away_win_probability", "ppg_adjusted_home_win_probability", "ppg_adjusted_draw_probability", "ppg_adjusted_away_probability", "ppg_adjustment_applied", "ppg_adjustment_strength", "ppg_adjustment_reason", "home_home_ppg_before_match", "away_away_ppg_before_match", "home_away_ppg_diff", "ppg_indicator_quality", "last5_adjusted_home_win_probability", "last5_adjusted_draw_probability", "last5_adjusted_away_probability", "last5_adjustment_applied", "last5_adjustment_strength", "last5_adjustment_reason", "home_last5_points", "away_last5_points", "home_last5_points_per_match", "away_last5_points_per_match", "last5_points_diff", "last5_indicator_quality", "confidence", "risk_level", "source_quality_band", "prediction_tier", "xg_available", "odds_available", "model_status", "primary_reasons", "risk_notes", "recommendation_summary", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
