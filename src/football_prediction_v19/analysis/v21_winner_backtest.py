# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v21_predict_winner import run_v21_predict_winner
from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus


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
            "match_id": row.get("match_id", f"match_{idx+1}"),
            "match_date": row.get("match_date", ""),
            "home_team": row.get("home_team", ""),
            "away_team": row.get("away_team", ""),
            "actual_result": actual,
            "leakage_status": "CLEAN",
        }
        try:
            result = run_v21_predict_winner(home_team=row["home_team"], away_team=row["away_team"], competition=row["competition"], season=row["season"], match_date=row["match_date"], source_profile=source_profile, mock_data_dir=mock_data_dir, cache_only=cache_only and not bool(mock_data_dir), output_dir=out / f"match_{idx+1}")
            rows.append({**base, **{k: result[k] for k in ["decision_class", "predicted_winner", "home_win_probability", "draw_probability", "away_win_probability", "confidence", "source_quality_band"]}, "xg_available": "xg" not in result["winner_model"].get("missing_inputs", []), "odds_available": "odds" not in result["winner_model"].get("missing_inputs", []), "match_error": ""})
        except Exception as exc:  # noqa: BLE001 - per-match failures should not invalidate corpus diagnostics.
            rows.append({**base, "decision_class": "DATA_BLOCKED", "predicted_winner": "", "home_win_probability": 0.0, "draw_probability": 0.0, "away_win_probability": 0.0, "confidence": 0.0, "source_quality_band": "BLOCKED", "xg_available": False, "odds_available": False, "match_error": type(exc).__name__})
    metrics = _metrics(rows)
    metrics.update(_sample_status(matches_requested, matches_available, len(rows), min_matches_required, fallback_data_used, allow_small_sample))
    metrics["corpus_source"] = corpus_source
    pd.DataFrame(rows).to_csv(out / "v21_winner_backtest_results.csv", index=False)
    (out / "v21_winner_backtest_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "v21_winner_backtest_report.md").write_text("# v2.1 Winner Backtest\n\n" + json.dumps(metrics, indent=2) + "\n\nNo ROI. No stake. No profit.\n", encoding="utf-8")
    status = "READY" if metrics["corpus_status"] == "READY" else ("BLOCKED" if metrics["corpus_status"] == "EMPTY" else "INSUFFICIENT_CORPUS")
    return {**metrics, "v21_winner_backtest_status": status, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _load_backtest_frame(matches: str | Path | None, out: Path, competition: str, season: str, corpus_path: str | Path | None, source_profile: str, mock_data_dir: str, cache_only: bool, enable_network: bool) -> tuple[pd.DataFrame, bool, str]:
    if corpus_path:
        return _frame_from_corpus(corpus_path), False, str(corpus_path)
    if matches:
        return pd.read_csv(matches, keep_default_na=False), False, str(matches)
    default_corpus = Path(f"outputs/corpus/v22/{competition.replace(' ', '_')}/{season.replace('/', '-')}/real_season_corpus.csv")
    if default_corpus.exists():
        return _frame_from_corpus(default_corpus), False, str(default_corpus)
    if enable_network or mock_data_dir:
        built = build_real_season_corpus(competition, season, out / "auto_corpus", source_profile=source_profile, enable_network=enable_network, cache_only=cache_only and not bool(mock_data_dir), mock_data_dir=mock_data_dir or None)
        return _frame_from_corpus(built["real_season_corpus_csv_path"]), bool(mock_data_dir), built["real_season_corpus_csv_path"]
    return pd.DataFrame(columns=["home_team", "away_team", "competition", "season", "match_date", "actual_result"]), False, ""


def _frame_from_corpus(path: str | Path) -> pd.DataFrame:
    corpus = pd.read_csv(path, keep_default_na=False)
    if "can_backtest" in corpus.columns:
        corpus = corpus[corpus["can_backtest"].astype(str).str.lower().isin(["true", "1"])]
    return pd.DataFrame({
        "home_team": corpus.get("home_team", pd.Series(dtype=str)),
        "away_team": corpus.get("away_team", pd.Series(dtype=str)),
        "competition": corpus.get("competition", pd.Series(dtype=str)),
        "season": corpus.get("season", pd.Series(dtype=str)),
        "match_date": corpus.get("match_date", pd.Series(dtype=str)),
        "actual_result": corpus.get("result_1x2", corpus.get("actual_result", pd.Series(dtype=str))),
    })


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
    return {
        "matches_total": total,
        "matches_evaluated": len(eval_rows),
        "winner_pick_count": len(picks),
        "winner_lean_count": sum(1 for r in rows if r["decision_class"] == "WINNER_LEAN"),
        "no_clear_winner_count": sum(1 for r in rows if r["decision_class"] == "NO_CLEAR_WINNER"),
        "no_decision_count": sum(1 for r in rows if r["decision_class"] == "NO_DECISION"),
        "data_blocked_count": sum(1 for r in rows if r["decision_class"] == "DATA_BLOCKED"),
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
