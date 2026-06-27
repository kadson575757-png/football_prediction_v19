# -*- coding: utf-8 -*-
from __future__ import annotations

import math


def compute_backtest_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    evaluated = [r for r in rows if r.get("actual_result") in {"HOME", "DRAW", "AWAY"}]
    correct = 0
    brier = 0.0
    for row in evaluated:
        actual = row["actual_result"]
        probs = {k: float(row.get(f"{k.lower()}_probability", 0) or 0) for k in ["HOME", "DRAW", "AWAY"]}
        if max(probs, key=probs.get) == actual:
            correct += 1
        brier += sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in probs) / 3
    n = len(evaluated)
    return {
        "matches_total": len(rows),
        "matches_evaluated": n,
        "model_tip_count": sum(1 for r in rows if r.get("decision_class") == "MODEL_TIP"),
        "analyst_lean_count": sum(1 for r in rows if r.get("decision_class") == "ANALYST_LEAN"),
        "no_bet_count": sum(1 for r in rows if r.get("decision_class") == "NO_BET"),
        "data_blocked_count": sum(1 for r in rows if r.get("decision_class") == "DATA_BLOCKED"),
        "accuracy_1x2": round(correct / n, 4) if n else 0.0,
        "brier_score": round(brier / n, 4) if n else 0.0,
        "average_confidence": round(sum(float(r.get("confidence", 0) or 0) for r in rows) / len(rows), 4) if rows else 0.0,
    }


def calibration_bins(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    bins = {}
    for row in rows:
        conf = float(row.get("confidence", 0) or 0)
        bucket = f"{math.floor(conf * 10) / 10:.1f}"
        bins.setdefault(bucket, {"confidence_bin": bucket, "n": 0})
        bins[bucket]["n"] += 1
    return list(bins.values())
