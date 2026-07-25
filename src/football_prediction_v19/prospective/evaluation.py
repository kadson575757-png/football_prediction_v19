"""Prospective primary-versus-shadow evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2180_winner_validation import metrics
from football_prediction_v19.prospective.prediction_store import read_locked_predictions, verify_prediction_locks
from football_prediction_v19.prospective.result_import import _read_results


OUTCOMES = np.array(["HOME", "DRAW", "AWAY"])


def evaluate_prospective(output_dir: str | Path) -> dict:
    out = Path(output_dir)
    locks = {row["fixture_key"]: row for row in read_locked_predictions(out)}
    results = _read_results(out)
    joined = []
    for key in sorted(set(locks) & set(results)):
        lock, actual = locks[key], results[key]
        eligible = bool(
            lock.get("locked")
            and not lock.get("result_known_at_prediction_time", False)
            and lock.get("prediction_timing_status") != "AFTER_KICKOFF_INVALID"
            and lock.get("eligible_for_prospective_evaluation", False)
            and int(lock.get("post_match_rows_used_count", 0)) == 0
            and actual.get("result_verified", False)
        )
        if not eligible:
            continue
        primary = lock["primary_winner_prediction"]
        shadow = lock["shadow_winner_prediction"]
        joined.append({
            **lock["match"], "fixture_key": key, "actual_result": actual["actual_result"],
            "primary_home_probability": primary["home_probability"],
            "primary_draw_probability": primary["draw_probability"],
            "primary_away_probability": primary["away_probability"],
            "shadow_home_probability": shadow["home_probability"],
            "shadow_draw_probability": shadow["draw_probability"],
            "shadow_away_probability": shadow["away_probability"],
            "primary_top_outcome": lock["primary_top_outcome"],
            "shadow_top_outcome": lock["shadow_top_outcome"],
            "agreement": lock["primary_shadow_agreement"],
            "confidence_band": lock["primary_confidence_band"],
            "data_quality_grade": lock["data_quality_grade"],
            "post_match_rows_used_count": lock["post_match_rows_used_count"],
        })
    frame = pd.DataFrame(joined)
    summary = _summary(frame, verify_prediction_locks(out))
    frame.to_csv(out / "prospective_primary_vs_shadow.csv", index=False)
    _breakdown(frame, "competition").to_csv(out / "prospective_shadow_by_competition.csv", index=False)
    _breakdown(frame, "agreement").to_csv(out / "prospective_shadow_by_agreement.csv", index=False)
    pd.DataFrame([{
        "draw_top_count": summary["shadow_draw_top_count"],
        "draw_precision": summary["shadow_draw_precision"],
        "draw_recall": summary["shadow_draw_recall"],
        "draw_f1": summary["shadow_draw_f1"],
    }]).to_csv(out / "prospective_shadow_draw_metrics.csv", index=False)
    (out / "prospective_shadow_evaluation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "prospective_shadow_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _summary(frame: pd.DataFrame, lock_audit: dict) -> dict:
    count = len(frame)
    if not count:
        return {
            "prospective_primary_shadow_evaluation_status": "READY",
            "evaluatable_count": 0, "prospective_gate": "PROSPECTIVE_SAMPLE_TOO_SMALL",
            "prediction_hash_mismatch_count": lock_audit["prediction_hash_mismatch_count"],
            **_empty_metrics(),
        }
    primary = frame[["primary_home_probability", "primary_draw_probability", "primary_away_probability"]].to_numpy()
    shadow = frame[["shadow_home_probability", "shadow_draw_probability", "shadow_away_probability"]].to_numpy()
    pm, sm = metrics(frame["actual_result"], primary), metrics(frame["actual_result"], shadow)
    actual = frame["actual_result"].to_numpy()
    ptop, stop = OUTCOMES[primary.argmax(axis=1)], OUTCOMES[shadow.argmax(axis=1)]
    corrected = int(np.sum((ptop != actual) & (stop == actual)))
    broken = int(np.sum((ptop == actual) & (stop != actual)))
    agree = ptop == stop
    return {
        "prospective_primary_shadow_evaluation_status": "READY",
        "evaluatable_count": count,
        "prospective_gate": _sample_gate(count),
        "primary_hit_rate": pm["top_outcome_hit_rate"], "shadow_hit_rate": sm["top_outcome_hit_rate"],
        "shadow_hit_rate_delta": sm["top_outcome_hit_rate"] - pm["top_outcome_hit_rate"],
        "primary_brier_score": pm["multiclass_brier_score"], "shadow_brier_score": sm["multiclass_brier_score"],
        "primary_log_loss": pm["multiclass_log_loss"], "shadow_log_loss": sm["multiclass_log_loss"],
        "primary_draw_precision": pm["draw_precision"], "shadow_draw_precision": sm["draw_precision"],
        "primary_draw_recall": pm["draw_recall"], "shadow_draw_recall": sm["draw_recall"],
        "shadow_draw_f1": sm["draw_f1"], "shadow_draw_top_count": sm["draw_top_count"],
        "newly_corrected": corrected, "newly_broken": broken, "net_corrected": corrected - broken,
        "agreement_count": int(agree.sum()), "disagreement_count": int((~agree).sum()),
        "primary_hit_rate_when_agree": float(np.mean(ptop[agree] == actual[agree])) if agree.any() else 0.0,
        "shadow_hit_rate_when_disagree": float(np.mean(stop[~agree] == actual[~agree])) if (~agree).any() else 0.0,
        "competitions_evaluated": int(frame["competition"].nunique()),
        "post_match_rows_used_count": int(frame["post_match_rows_used_count"].sum()),
        "prediction_hash_mismatch_count": lock_audit["prediction_hash_mismatch_count"],
    }


def _breakdown(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=[column, "evaluatable_count", "primary_hit_rate", "shadow_hit_rate", "hit_rate_delta"])
    records = []
    for value, group in frame.groupby(column):
        primary_hit = group["primary_top_outcome"].eq(group["actual_result"]).mean()
        shadow_hit = group["shadow_top_outcome"].eq(group["actual_result"]).mean()
        records.append({column: value, "evaluatable_count": len(group), "primary_hit_rate": primary_hit, "shadow_hit_rate": shadow_hit, "hit_rate_delta": shadow_hit - primary_hit})
    return pd.DataFrame(records)


def _sample_gate(count: int) -> str:
    if count < 50:
        return "PROSPECTIVE_SAMPLE_TOO_SMALL"
    if count < 100:
        return "EARLY_PROSPECTIVE_SIGNAL"
    if count < 250:
        return "PROSPECTIVE_VALIDATION_IN_PROGRESS"
    return "PROSPECTIVE_SAMPLE_REVIEWABLE"


def _empty_metrics() -> dict:
    keys = [
        "primary_hit_rate", "shadow_hit_rate", "shadow_hit_rate_delta",
        "primary_brier_score", "shadow_brier_score", "primary_log_loss", "shadow_log_loss",
        "primary_draw_precision", "shadow_draw_precision", "primary_draw_recall",
        "shadow_draw_recall", "shadow_draw_f1", "shadow_draw_top_count",
        "newly_corrected", "newly_broken", "net_corrected", "agreement_count",
        "disagreement_count", "primary_hit_rate_when_agree", "shadow_hit_rate_when_disagree",
        "competitions_evaluated", "post_match_rows_used_count",
    ]
    return {key: 0 for key in keys}


def _report(summary: dict) -> str:
    return f"""# Prospective Primary vs Shadow Report

- Evaluatable matches: {summary['evaluatable_count']}
- Gate: **{summary['prospective_gate']}**
- Primary hit rate: {summary['primary_hit_rate']:.4f}
- Shadow hit rate: {summary['shadow_hit_rate']:.4f}
- Delta: {summary['shadow_hit_rate_delta']:+.4f}
- Net corrected: {summary['net_corrected']}
- Shadow draw precision: {summary['shadow_draw_precision']:.4f}
- Shadow draw recall: {summary['shadow_draw_recall']:.4f}
- Shadow draw F1: {summary['shadow_draw_f1']:.4f}

The primary model remains authoritative. The shadow model is monitored without probability blending.
"""
