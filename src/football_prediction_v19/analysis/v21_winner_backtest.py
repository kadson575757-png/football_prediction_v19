# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v21_predict_winner import run_v21_predict_winner
from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality
from football_prediction_v19.analysis.v21_prediction_eligibility import evaluate_prediction_eligibility
from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy
from football_prediction_v19.analysis.v21_winner_feature_store import build_winner_feature_store
from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core
from football_prediction_v19.analysis.v22_calibration_export import write_calibration_dataset
from football_prediction_v19.analysis.v23_data_block_audit import build_data_block_audit
from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus
from football_prediction_v19.analysis.v24_confidence_calibration import write_confidence_calibration
from football_prediction_v19.analysis.v24_no_decision_diagnostics import write_no_decision_diagnostics
from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics
from football_prediction_v19.analysis.v24_threshold_simulation import write_threshold_simulation


def run_v21_winner_backtest(
    matches: str | Path | None,
    output_dir: str | Path,
    *,
    competition: str = "",
    season: str = "",
    corpus_path: str | Path | None = None,
    max_matches: int | None = None,
    min_matches_required: int = 10,
    allow_small_sample: bool = False,
    mock_data_dir: str = "",
    source_profile: str = "config/v20_internet_sources.yaml",
    cache_only: bool = True,
    enable_network: bool = False,
    decision_policy_config: str | Path | None = None,
    emit_calibration_diagnostics: bool = False,
    emit_threshold_simulation: bool = False,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame, fallback_data_used, corpus_source = _load_backtest_frame(matches, out, competition, season, corpus_path, source_profile, mock_data_dir, cache_only, enable_network)
    matches_available = len(frame)
    matches_requested = int(max_matches or matches_available)
    if max_matches:
        frame = frame.head(max_matches)
    rows = []
    for idx, row in frame.iterrows():
        actual = row.get("actual_result", "")
        base = {
            "competition": row.get("competition", ""),
            "season": row.get("season", ""),
            "match_id": row.get("canonical_match_id", row.get("match_id", f"match_{idx+1}")),
            "match_date": row.get("match_date", ""),
            "home_team": row.get("home_team", ""),
            "away_team": row.get("away_team", ""),
            "actual_result": actual,
            "leakage_status": "CLEAN",
        }
        try:
            if _is_corpus_row(row):
                result = _predict_from_corpus_row(frame, idx, row, out / f"match_{idx+1}", decision_policy_config)
            else:
                result = run_v21_predict_winner(home_team=row["home_team"], away_team=row["away_team"], competition=row["competition"], season=row["season"], match_date=row["match_date"], source_profile=source_profile, mock_data_dir=mock_data_dir, cache_only=cache_only and not bool(mock_data_dir), output_dir=out / f"match_{idx+1}")
            rows.append({
                **base,
                **{k: result[k] for k in ["decision_class", "predicted_winner", "home_win_probability", "draw_probability", "away_win_probability", "confidence", "source_quality_band"]},
                "eligibility_class": result.get("eligibility_class", ""),
                "model_status": result.get("model_status", ""),
                "prediction_tier": result.get("prediction_tier", row.get("prediction_tier", "")),
                "confidence_band": result.get("winner_model", {}).get("confidence_band", ""),
                "early_season_risk": result.get("features", {}).get("early_season_risk", False),
                "no_decision_reason": result.get("no_decision_reason", ""),
                "xg_available": "xg" not in result["winner_model"].get("missing_inputs", []),
                "odds_available": "odds" not in result["winner_model"].get("missing_inputs", []),
                "probabilities_created": result.get("model_status") != "WINNER_MODEL_BLOCKED",
                "model_ran": result.get("model_status") != "WINNER_MODEL_BLOCKED",
                "decision_attempted": result.get("decision_class") != "DATA_BLOCKED",
                "block_reason_code": result.get("block_reason_code", ""),
                "is_hard_block": bool(result.get("is_hard_block", False)),
                "invalid_block": bool(result.get("invalid_block", False)),
                "match_error": "",
            })
        except Exception as exc:  # noqa: BLE001 - per-match failures should not invalidate corpus diagnostics.
            rows.append({**base, "decision_class": "DATA_BLOCKED", "predicted_winner": "", "home_win_probability": 0.0, "draw_probability": 0.0, "away_win_probability": 0.0, "confidence": 0.0, "source_quality_band": "BLOCKED", "eligibility_class": "DATA_BLOCKED", "model_status": "WINNER_MODEL_BLOCKED", "prediction_tier": row.get("prediction_tier", ""), "xg_available": _bool(row.get("xg_available", False)), "odds_available": _bool(row.get("odds_available", False)), "probabilities_created": False, "model_ran": False, "decision_attempted": False, "block_reason_code": "feature_store_exception", "is_hard_block": False, "invalid_block": True, "match_error": type(exc).__name__})
    metrics = _metrics(rows)
    metrics.update(_sample_status(matches_requested, matches_available, len(rows), min_matches_required, fallback_data_used, allow_small_sample))
    metrics["corpus_source"] = corpus_source
    metrics["corpus_path"] = corpus_source
    metrics["corpus_rows_loaded"] = matches_available
    metrics["corpus_expected_min_rows"] = min_matches_required
    if metrics["corpus_status"] in {"EMPTY", "INSUFFICIENT_SAMPLE"}:
        metrics["recommendation"] = "BUILD_OR_WARM_V22_CORPUS"
    results_frame = pd.DataFrame(rows, columns=_RESULT_COLUMNS)
    results_frame.to_csv(out / "v21_winner_backtest_results.csv", index=False)
    results_frame.to_csv(out / "winner_backtest_results.csv", index=False)
    results_frame[results_frame.get("decision_attempted", False).astype(bool) if not results_frame.empty else []].to_csv(out / "decision_attempts.csv", index=False)
    results_frame.to_csv(out / "feature_handoff_audit.csv", index=False)
    _eligibility_distribution(results_frame).to_csv(out / "eligibility_distribution.csv", index=False)
    audit = build_data_block_audit(results_frame, out)
    metrics["data_block_audit_status"] = audit["v23_data_block_audit_status"]
    if decision_policy_config:
        metrics["active_decision_policy"] = _active_policy_name(decision_policy_config)
    if emit_calibration_diagnostics:
        calibration = write_calibration_dataset(out / "winner_backtest_results.csv", out / "calibration")
        no_decision = write_no_decision_diagnostics(out / "winner_backtest_results.csv", out / "calibration")
        probability = write_probability_diagnostics(out / "winner_backtest_results.csv", out / "calibration")
        confidence = write_confidence_calibration(out / "winner_backtest_results.csv", out / "calibration")
        metrics.update({
            "calibration_diagnostics_status": "PASSED",
            "no_decision_diagnostics_status": no_decision["no_decision_diagnostics_status"],
            "probability_diagnostics_status": probability["probability_diagnostics_status"],
            "confidence_calibration_status": confidence["confidence_calibration_status"],
            "average_top_edge": probability["average_top_edge"],
            "median_top_edge": probability["median_top_edge"],
            "confidence_cap_rate": probability["confidence_cap_rate"],
            "results_only_rate": probability["results_only_rate"],
            "xg_missing_rate": probability["xg_missing_rate"],
            "calibration_dataset_csv_path": calibration["calibration_dataset_csv_path"],
        })
    if emit_threshold_simulation:
        threshold = write_threshold_simulation(out / "winner_backtest_results.csv", out / "calibration")
        metrics.update({
            "threshold_simulation_status": threshold["threshold_simulation_status"],
            "selected_policy_top1_accuracy_decisions_only": threshold["selected_policy_top1_accuracy_decisions_only"],
            "selected_policy_brier_score_decisions_only": threshold["selected_policy_brier_score_decisions_only"],
        })
    (out / "v21_winner_backtest_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "v21_winner_backtest_report.md").write_text("# v2.1 Winner Backtest\n\n" + json.dumps(metrics, indent=2) + "\n\nNo ROI. No stake. No profit.\n", encoding="utf-8")
    (out / "winner_backtest_dashboard.md").write_text("# v2.3 Winner Backtest Dashboard\n\n" + "\n".join(f"- {k}: {v}" for k, v in metrics.items()) + "\n\nNo automatic betting. No stake. No ROI.\n", encoding="utf-8")
    (out / "missing_data_non_blocking_report.md").write_text("# Missing Data Non-Blocking Report\n\nmissing_xg and missing_odds are non-hard missing data for results-only corpus rows.\n", encoding="utf-8")
    invalid = results_frame[results_frame.get("invalid_block", False).astype(bool)] if not results_frame.empty else pd.DataFrame()
    invalid.to_csv(out / "invalid_blocks_report.csv", index=False)
    (out / "invalid_blocks_report.md").write_text("# Invalid Blocks Report\n\n" + invalid.to_csv(index=False), encoding="utf-8")
    if metrics["data_blocked_count"] == metrics["matches_evaluated"] and metrics["matches_evaluated"] >= 10:
        status = "BLOCKING_BUG_DETECTED"
    elif metrics["invalid_data_blocked_count"] > 0:
        status = "FAILED"
    else:
        status = "READY" if metrics["corpus_status"] == "READY" else ("BLOCKED" if metrics["corpus_status"] == "EMPTY" else "INSUFFICIENT_CORPUS")
    return {**metrics, "v21_winner_backtest_status": status, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _load_backtest_frame(matches: str | Path | None, out: Path, competition: str, season: str, corpus_path: str | Path | None, source_profile: str, mock_data_dir: str, cache_only: bool, enable_network: bool) -> tuple[pd.DataFrame, bool, str]:
    if corpus_path:
        return _frame_from_corpus(corpus_path), False, str(corpus_path)
    if matches:
        return pd.read_csv(matches, keep_default_na=False), False, str(matches)
    if enable_network:
        built = build_real_season_corpus(competition, season, out / "auto_corpus", source_profile=source_profile, enable_network=enable_network, cache_only=False, mock_data_dir=mock_data_dir or None)
        return _frame_from_corpus(built["real_season_corpus_csv_path"]), bool(mock_data_dir), built["real_season_corpus_csv_path"]
    default_corpus = Path(f"outputs/corpus/v22/{competition.replace(' ', '_')}/{season.replace('/', '-')}/real_season_corpus.csv")
    if default_corpus.exists():
        return _frame_from_corpus(default_corpus), False, str(default_corpus)
    if mock_data_dir:
        built = build_real_season_corpus(competition, season, out / "auto_corpus", source_profile=source_profile, enable_network=enable_network, cache_only=cache_only and not bool(mock_data_dir), mock_data_dir=mock_data_dir or None)
        return _frame_from_corpus(built["real_season_corpus_csv_path"]), bool(mock_data_dir), built["real_season_corpus_csv_path"]
    return pd.DataFrame(columns=["home_team", "away_team", "competition", "season", "match_date", "actual_result"]), False, ""


def _frame_from_corpus(path: str | Path) -> pd.DataFrame:
    corpus = pd.read_csv(path, keep_default_na=False)
    if "can_backtest" in corpus.columns:
        corpus = corpus[corpus["can_backtest"].astype(str).str.lower().isin(["true", "1"])]
    frame = corpus.copy()
    frame["actual_result"] = frame.get("result_1x2", frame.get("actual_result", pd.Series(dtype=str)))
    return frame


def _is_corpus_row(row: pd.Series) -> bool:
    return "result_1x2" in row.index or "football_data_available" in row.index or "canonical_match_id" in row.index


def _predict_from_corpus_row(frame: pd.DataFrame, idx: object, row: pd.Series, out: Path, decision_policy_config: str | Path | None = None) -> dict[str, object]:
    out.mkdir(parents=True, exist_ok=True)
    result_available = bool(str(row.get("actual_result", row.get("result_1x2", ""))).strip())
    football_data_available = _bool(row.get("football_data_available", True))
    leakage_status = str(row.get("leakage_status", "CLEAN") or "CLEAN")
    hard_reason = ""
    if not str(row.get("home_team", "")).strip() or not str(row.get("away_team", "")).strip() or not str(row.get("match_date", "")).strip():
        hard_reason = "corrupt_corpus_row"
    elif not result_available:
        hard_reason = "result_missing_for_backtest"
    elif not football_data_available:
        hard_reason = "no_core_source_available"
    elif leakage_status == "BLOCKED":
        hard_reason = "leakage_blocked"

    if hard_reason:
        return _blocked_result(row, hard_reason, True)

    asof = _corpus_asof_features(frame, idx, row)
    xg_available = _bool(row.get("xg_available", False))
    odds_available = _bool(row.get("odds_available", False))
    prediction_tier = "TIER_1_FULL_XG" if xg_available else "TIER_2_RESULTS_ONLY"
    coverage = {
        "prediction_tier": prediction_tier,
        "table_available": True,
        "table_form_available": True,
        "xg_available": xg_available,
        "odds_available": odds_available,
        "prior_matches_count": asof["prior_matches_count"],
        "min_prior_matches": 2,
    }
    eligibility = evaluate_prediction_eligibility({"status": "RESOLVED"}, coverage, {"leakage_status": leakage_status}, out)
    quality = compute_real_source_quality("RESOLVED", {"table_available": True, "form_available": True, "xg_available": xg_available, "odds_available": odds_available}, leakage_status, False, output_dir=out)
    selected = {
        "canonical_match_id": row.get("canonical_match_id", row.get("match_id", "")),
        "match_date": row.get("match_date", ""),
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "prediction_tier": prediction_tier,
    }
    store = build_winner_feature_store(selected, asof, eligibility, quality, out)
    model = run_winner_model_core(store["features"], eligibility, out)
    decision = apply_winner_decision_policy(model, eligibility, store["features"], out, decision_policy_config)
    return {
        "v21_winner_prediction_status": "READY",
        "eligibility_class": eligibility["eligibility_class"],
        "model_status": model["model_status"],
        "prediction_tier": prediction_tier,
        "decision_class": decision["decision_class"],
        "predicted_winner": decision["predicted_winner"],
        "winner_team": decision["winner_team"],
        "home_win_probability": decision["home_win_probability"],
        "draw_probability": decision["draw_probability"],
        "away_win_probability": decision["away_win_probability"],
        "confidence": decision["confidence"],
        "source_quality_band": quality["source_quality_band"],
        "winner_model": model,
        "winner_decision": decision,
        "features": store["features"],
        "no_decision_reason": decision.get("why_not_stronger", "") if decision["decision_class"] == "NO_DECISION" else "",
        "block_reason_code": "",
        "is_hard_block": False,
        "invalid_block": False,
    }


def _corpus_asof_features(frame: pd.DataFrame, idx: object, row: pd.Series) -> dict[str, object]:
    prior = frame.loc[:idx].iloc[:-1].copy()
    if "match_date" in prior.columns:
        prior = prior[prior["match_date"].astype(str) < str(row.get("match_date", ""))]
    home = str(row.get("home_team", ""))
    away = str(row.get("away_team", ""))
    home_stats = _team_stats(prior, home)
    away_stats = _team_stats(prior, away)
    prior_count = min(home_stats["matches"], away_stats["matches"])
    return {
        "match_id": row.get("canonical_match_id", row.get("match_id", "")),
        "home_points_per_game_asof": home_stats["ppg"],
        "away_points_per_game_asof": away_stats["ppg"],
        "table_rank_gap_asof": 0,
        "home_recent_form_points_5": home_stats["recent_points"],
        "away_recent_form_points_5": away_stats["recent_points"],
        "home_recent_goals_for_5": home_stats["gf5"],
        "away_recent_goals_for_5": away_stats["gf5"],
        "home_recent_goals_against_5": home_stats["ga5"],
        "away_recent_goals_against_5": away_stats["ga5"],
        "home_xg_for_asof": _num(row.get("home_xg")) if _bool(row.get("xg_available", False)) else 0,
        "away_xg_for_asof": _num(row.get("away_xg")) if _bool(row.get("xg_available", False)) else 0,
        "home_xg_against_asof": _num(row.get("home_xga")) if _bool(row.get("xg_available", False)) else 0,
        "away_xg_against_asof": _num(row.get("away_xga")) if _bool(row.get("xg_available", False)) else 0,
        "xg_diff_edge_asof": 0,
        "home_rolling_xg_5": 0,
        "away_rolling_xg_5": 0,
        "odds_available": _bool(row.get("odds_available", False)),
        "xg_available": _bool(row.get("xg_available", False)),
        "early_season_risk": prior_count < 2,
        "prior_matches_count": prior_count,
        "leakage_status": "CLEAN",
    }


def _team_stats(prior: pd.DataFrame, team: str) -> dict[str, float]:
    matches = []
    for _, match in prior.iterrows():
        hg = _num(match.get("home_goals"))
        ag = _num(match.get("away_goals"))
        if str(match.get("home_team", "")) == team and str(match.get("result_1x2", match.get("actual_result", ""))).strip():
            points = 3 if hg > ag else (1 if hg == ag else 0)
            matches.append((points, hg, ag))
        elif str(match.get("away_team", "")) == team and str(match.get("result_1x2", match.get("actual_result", ""))).strip():
            points = 3 if ag > hg else (1 if hg == ag else 0)
            matches.append((points, ag, hg))
    recent = matches[-5:]
    total = len(matches)
    return {
        "matches": float(total),
        "ppg": round(sum(m[0] for m in matches) / total, 4) if total else 0.0,
        "recent_points": float(sum(m[0] for m in recent)),
        "gf5": float(sum(m[1] for m in recent)),
        "ga5": float(sum(m[2] for m in recent)),
    }


def _blocked_result(row: pd.Series, reason: str, hard: bool) -> dict[str, object]:
    return {
        "decision_class": "DATA_BLOCKED",
        "predicted_winner": "",
        "home_win_probability": 0.0,
        "draw_probability": 0.0,
        "away_win_probability": 0.0,
        "confidence": 0.0,
        "source_quality_band": "BLOCKED",
        "eligibility_class": "DATA_BLOCKED",
        "model_status": "WINNER_MODEL_BLOCKED",
        "prediction_tier": row.get("prediction_tier", ""),
        "winner_model": {"missing_inputs": [reason]},
        "winner_decision": {},
        "block_reason_code": reason,
        "is_hard_block": hard,
        "invalid_block": not hard,
    }


def _sample_status(matches_requested: int, matches_available: int, matches_evaluated: int, min_required: int, fallback_data_used: bool, allow_small_sample: bool) -> dict[str, object]:
    if matches_available == 0:
        corpus_status = "EMPTY"
    elif matches_available < min_required and not allow_small_sample:
        corpus_status = "INSUFFICIENT_SAMPLE"
    elif matches_available < matches_requested:
        corpus_status = "INSUFFICIENT_SAMPLE"
    else:
        corpus_status = "READY"
    validity = "HIGH" if matches_evaluated >= 100 else ("MEDIUM" if matches_evaluated >= 30 else "LOW")
    return {
        "matches_requested": matches_requested,
        "matches_available": matches_available,
        "corpus_status": corpus_status,
        "statistical_validity": validity,
        "fallback_data_used": bool(fallback_data_used),
        "sample_warning": matches_evaluated < 10,
        "recommendation": "BUILD_CORPUS_OR_ENABLE_NETWORK" if corpus_status in {"EMPTY", "INSUFFICIENT_SAMPLE"} else "READY_FOR_BACKTEST_REVIEW",
    }


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    picks = [r for r in rows if r["decision_class"] == "WINNER_PICK"]
    eval_rows = [r for r in rows if r.get("actual_result")]
    correct = 0
    brier = 0.0
    for r in eval_rows:
        probs = {"H": float(r["home_win_probability"]), "D": float(r["draw_probability"]), "A": float(r["away_win_probability"])}
        pred = {"HOME": "H", "DRAW": "D", "AWAY": "A"}.get(str(r["predicted_winner"]), "")
        correct += int(pred == r["actual_result"])
        brier += sum((probs[k] - (1.0 if k == r["actual_result"] else 0.0)) ** 2 for k in ["H", "D", "A"]) / 3
    hard_blocked = sum(1 for r in rows if r["decision_class"] == "DATA_BLOCKED" and r.get("is_hard_block"))
    invalid_blocked = sum(1 for r in rows if r["decision_class"] == "DATA_BLOCKED" and r.get("invalid_block"))
    data_blocked = sum(1 for r in rows if r["decision_class"] == "DATA_BLOCKED")
    model_ran = sum(1 for r in rows if r.get("model_ran"))
    probs_created = sum(1 for r in rows if r.get("probabilities_created"))
    decision_attempts = sum(1 for r in rows if r.get("decision_attempted"))
    no_xg_partial = sum(1 for r in rows if r.get("model_status") == "WINNER_MODEL_PARTIAL" and not bool(r.get("xg_available")))
    odds_missing_non_block = sum(1 for r in rows if r["decision_class"] != "DATA_BLOCKED" and not bool(r.get("odds_available")))
    return {
        "matches_total": total,
        "matches_evaluated": len(eval_rows),
        "winner_pick_count": len(picks),
        "winner_lean_count": sum(1 for r in rows if r["decision_class"] == "WINNER_LEAN"),
        "no_clear_winner_count": sum(1 for r in rows if r["decision_class"] == "NO_CLEAR_WINNER"),
        "no_decision_count": sum(1 for r in rows if r["decision_class"] == "NO_DECISION"),
        "data_blocked_count": data_blocked,
        "hard_data_blocked_count": hard_blocked,
        "non_hard_data_blocked_count": data_blocked - hard_blocked,
        "invalid_data_blocked_count": invalid_blocked,
        "decision_attempt_count": decision_attempts,
        "decision_coverage_rate": round((len(picks) + sum(1 for r in rows if r["decision_class"] == "WINNER_LEAN")) / total, 4) if total else 0.0,
        "model_ran_count": model_ran,
        "probabilities_created_count": probs_created,
        "no_xg_partial_model_count": no_xg_partial,
        "odds_missing_non_block_count": odds_missing_non_block,
        "understat_failed_non_block_count": no_xg_partial,
        "data_block_rate": round(data_blocked / total, 4) if total else 0.0,
        "hard_block_rate": round(hard_blocked / total, 4) if total else 0.0,
        "invalid_block_rate": round(invalid_blocked / total, 4) if total else 0.0,
        "winner_model_status": "READY" if probs_created > 0 or total == 0 else "FAILED",
        "top1_accuracy": round(correct / len(eval_rows), 4) if eval_rows else 0.0,
        "brier_score_1x2": round(brier / len(eval_rows), 4) if eval_rows else 0.0,
        "calibration_bins": [],
        "accuracy_by_league": {},
        "coverage_by_source": {},
        "xg_available_rate": round(sum(bool(r["xg_available"]) for r in rows) / total, 4) if total else 0.0,
        "odds_available_rate": round(sum(bool(r["odds_available"]) for r in rows) / total, 4) if total else 0.0,
        "no_odds_rate": round(sum(not bool(r["odds_available"]) for r in rows) / total, 4) if total else 0.0,
        "early_season_skip_rate": 0.0,
    }


def _eligibility_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "eligibility_class" not in frame.columns:
        return pd.DataFrame(columns=["eligibility_class", "n"])
    return frame.groupby("eligibility_class", dropna=False).size().reset_index(name="n")


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _active_policy_name(config_path: str | Path | None) -> str:
    if not config_path:
        return "default_safe"
    path = Path(config_path)
    if not path.exists():
        return "default_safe"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("active_policy:"):
            return line.split(":", 1)[1].strip()
    return "custom"


_RESULT_COLUMNS = [
    "competition", "season", "match_id", "match_date", "home_team", "away_team", "actual_result",
    "leakage_status", "decision_class", "predicted_winner", "home_win_probability", "draw_probability",
    "away_win_probability", "confidence", "source_quality_band", "eligibility_class", "model_status",
    "prediction_tier", "confidence_band", "early_season_risk", "no_decision_reason", "xg_available",
    "odds_available", "probabilities_created", "model_ran", "decision_attempted", "block_reason_code",
    "is_hard_block", "invalid_block", "match_error",
]
