# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus


def run_v24_winner_calibration_gate(output_dir: str | Path, diagnostics_dir: str | Path | None = None, metrics: dict[str, object] | None = None, *, min_calibration_matches_required: int = 50, allow_insufficient_corpus: bool = False, enable_network: bool = False) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    auto_corpus_build_status = "NOT_REQUESTED"
    if enable_network:
        built = build_real_season_corpus("Premier League", "2025/26", out / "auto_corpus", enable_network=True, cache_only=False)
        auto_corpus_build_status = str(built.get("v22_real_season_corpus_status", "UNKNOWN"))
    diag = Path(diagnostics_dir) if diagnostics_dir else Path("outputs/analysis_preview/v21_winner_backtest/calibration")
    explicit_metrics = metrics is not None
    metrics = metrics or _discover_metrics()
    multileague_metrics = {} if explicit_metrics else _discover_multileague_metrics()
    real_requested = int(metrics.get("matches_requested", metrics.get("matches_requested_total", 0)) or 0)
    real_available = int(metrics.get("matches_available", metrics.get("matches_available_total", 0)) or 0)
    real_evaluated = int(metrics.get("matches_evaluated", metrics.get("matches_evaluated_total", 0)) or 0)
    multi_requested = int(multileague_metrics.get("matches_requested_total", 0) or 0)
    multi_available = int(multileague_metrics.get("matches_available_total", 0) or 0)
    multi_evaluated = int(multileague_metrics.get("matches_evaluated_total", 0) or 0)
    sufficient_sample = real_evaluated >= min_calibration_matches_required and real_available >= min_calibration_matches_required
    insufficient_warning = not sufficient_sample or str(metrics.get("corpus_status", "")).upper() == "INSUFFICIENT_SAMPLE" or str(metrics.get("v21_winner_backtest_status", "")).upper() == "INSUFFICIENT_CORPUS"
    probability_status = _diagnostic_status(diag / "probability_distribution_diagnostics.json", "diagnostics_status")
    confidence_status = _diagnostic_status(diag / "confidence_calibration_summary.json", "confidence_calibration_status")
    checks = {
        "calibration_dataset_status": _exists(diag / "calibration_dataset.csv"),
        "no_decision_diagnostics_status": _exists(diag / "no_decision_diagnostics.csv"),
        "probability_diagnostics_status": _status_to_gate(probability_status),
        "threshold_simulation_status": _exists(diag / "threshold_simulation_results.csv"),
        "confidence_calibration_status": _status_to_gate(confidence_status),
        "decision_policy_config_status": "PASSED" if Path("config/v24_winner_decision_policy.yaml").exists() else "FAILED",
        "real_backtest_status": _real_backtest_status(metrics, min_calibration_matches_required, allow_insufficient_corpus),
        "multileague_calibration_status": _multileague_status(multileague_metrics, min_calibration_matches_required, allow_insufficient_corpus),
        "safety_status": "PASSED",
    }
    if _contains_forbidden_terms(diag):
        checks["safety_status"] = "FAILED"
    hard_ready = all(value == "PASSED" for value in checks.values()) and sufficient_sample
    warning_ready = allow_insufficient_corpus and all(value in {"PASSED", "WARNING"} for value in checks.values())
    status = "V24_READY_TO_TAG" if hard_ready else ("V24_READY_WITH_WARNINGS" if warning_ready else "V24_NOT_READY")
    result = {
        "v24_winner_calibration_gate_status": status,
        **checks,
        "real_matches_requested": real_requested,
        "real_matches_available": real_available,
        "real_matches_evaluated": real_evaluated,
        "multileague_matches_requested": multi_requested,
        "multileague_matches_available": multi_available,
        "multileague_matches_evaluated": multi_evaluated,
        "min_calibration_matches_required": int(min_calibration_matches_required),
        "auto_corpus_build_status": auto_corpus_build_status,
        "sufficient_calibration_sample": bool(sufficient_sample),
        "insufficient_corpus_warning": bool(insufficient_warning),
        "recommendation": "V24_READY_TO_TAG" if status == "V24_READY_TO_TAG" else ("BUILD_OR_WARM_V22_CORPUS" if insufficient_warning and not allow_insufficient_corpus else "FIX_REQUIRED"),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    (out / "v24_winner_calibration_gate_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([result]).to_csv(out / "v24_winner_calibration_gate_summary.csv", index=False)
    (out / "v24_winner_calibration_gate.md").write_text("# v2.4 Winner Calibration Gate\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()) + "\n\nNo automatic betting. No stake. No ROI.\n", encoding="utf-8")
    return result


def _exists(path: Path) -> str:
    return "PASSED" if path.exists() else "FAILED"


def _real_backtest_status(metrics: dict[str, object], min_required: int = 50, allow_insufficient: bool = False) -> str:
    evaluated = int(metrics.get("matches_evaluated", 0) or metrics.get("matches_evaluated_total", 0) or 0)
    available = int(metrics.get("matches_available", 0) or metrics.get("matches_available_total", 0) or 0)
    blocked = int(metrics.get("data_blocked_count", 0) or 0)
    probs = int(metrics.get("probabilities_created_count", 0) or 0)
    if evaluated and blocked >= evaluated:
        return "FAILED"
    if evaluated and probs == 0:
        return "FAILED"
    if evaluated < min_required or available < min_required or str(metrics.get("corpus_status", "")).upper() == "INSUFFICIENT_SAMPLE":
        return "WARNING" if allow_insufficient else "FAILED"
    return "PASSED" if evaluated else "WARNING"


def _discover_metrics() -> dict[str, object]:
    path = Path("outputs/analysis_preview/v21_winner_backtest/v21_winner_backtest_metrics.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _discover_multileague_metrics() -> dict[str, object]:
    for path in [Path("outputs/backtests/v22/multileague_preview/decision_class_breakdown.csv"), Path("outputs/backtests/v22/multileague_smoke/decision_class_breakdown.csv")]:
        if path.exists():
            frame = pd.read_csv(path, keep_default_na=False)
            if not frame.empty:
                return frame.iloc[0].to_dict()
    return {}


def _multileague_status(metrics: dict[str, object], min_required: int, allow_insufficient: bool) -> str:
    if not metrics:
        return "PASSED"
    evaluated = int(metrics.get("matches_evaluated_total", metrics.get("evaluated_matches", 0)) or 0)
    available = int(metrics.get("matches_available_total", metrics.get("total_matches_available", 0)) or 0)
    blocked = int(metrics.get("data_blocked_count", 0) or 0)
    if evaluated and blocked >= evaluated:
        return "FAILED"
    if evaluated < min_required or available < min_required or str(metrics.get("v22_multileague_backtest_status", "")).upper() == "INSUFFICIENT_SAMPLE":
        return "WARNING" if allow_insufficient else "FAILED"
    return "PASSED"


def _diagnostic_status(path: Path, key: str) -> str:
    if not path.exists():
        return "MISSING"
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get(key, "PASSED"))
    except json.JSONDecodeError:
        return "FAILED"


def _status_to_gate(status: str) -> str:
    if status == "PASSED":
        return "PASSED"
    if status in {"INSUFFICIENT_SAMPLE", "EMPTY_DATASET"}:
        return "WARNING"
    return "FAILED"


def _contains_forbidden_terms(path: Path) -> bool:
    forbidden = ["roi", "stake", "profit", "yield", "bankroll"]
    for file in path.glob("*"):
        if file.is_file() and file.suffix.lower() in {".csv", ".json"}:
            text = file.read_text(encoding="utf-8", errors="ignore").lower()
            if any(term in text for term in forbidden):
                return True
    return False
