# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def compute_v27_metrics(rows: pd.DataFrame | list[dict[str, Any]]) -> dict[str, object]:
    frame = pd.DataFrame(rows)
    requested = int(len(frame))
    if frame.empty:
        return _empty_metrics(requested)
    decisions = frame["decision_class"].astype(str) if "decision_class" in frame else pd.Series([], dtype=str)
    evals = frame["evaluation_result"].astype(str) if "evaluation_result" in frame else pd.Series([], dtype=str)
    known = frame["result_status"].astype(str).eq("RESOLVED") if "result_status" in frame else pd.Series([False] * requested)
    decision_mask = decisions.isin(["WINNER_PICK", "WINNER_LEAN"])
    confidence = pd.to_numeric(frame.get("confidence", pd.Series(dtype=float)), errors="coerce")
    metrics = {
        "matches_requested": requested,
        "matches_evaluated": requested,
        "result_known_count": int(known.sum()),
        "decision_count": int(decision_mask.sum()),
        "winner_pick_count": int(decisions.eq("WINNER_PICK").sum()),
        "winner_lean_count": int(decisions.eq("WINNER_LEAN").sum()),
        "hit_count": int(evals.eq("HIT").sum()),
        "miss_count": int(evals.eq("MISS").sum()),
        "hit_rate": _rate(int(evals.eq("HIT").sum()), int(evals.isin(["HIT", "MISS"]).sum())),
        "no_decision_count": int(evals.eq("NO_DECISION").sum()),
        "no_decision_rate": _rate(int(evals.eq("NO_DECISION").sum()), requested),
        "data_blocked_count": int(evals.eq("DATA_BLOCKED").sum()),
        "data_blocked_rate": _rate(int(evals.eq("DATA_BLOCKED").sum()), requested),
        "result_unknown_count": int(evals.eq("RESULT_UNKNOWN").sum()),
        "result_unknown_rate": _rate(int(evals.eq("RESULT_UNKNOWN").sum()), requested),
        "average_confidence": round(float(confidence.mean()), 4) if not confidence.dropna().empty else 0.0,
        "hit_rate_by_decision_class": _group_hit_rate(frame, ["decision_class"]),
        "hit_rate_by_competition": _group_hit_rate(frame, ["competition"]),
        "top_block_reasons": _top_values(frame.get("block_reason_text", pd.Series(dtype=str))),
        "top_no_decision_reasons": _top_values(frame.get("recommendation_summary", pd.Series(dtype=str))),
        "top_risk_notes": _top_values(frame.get("risk_notes", pd.Series(dtype=str))),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "productive_betting_enabled": False,
    }
    return metrics


def _empty_metrics(requested: int) -> dict[str, object]:
    return {
        "matches_requested": requested,
        "matches_evaluated": 0,
        "result_known_count": 0,
        "decision_count": 0,
        "winner_pick_count": 0,
        "winner_lean_count": 0,
        "hit_count": 0,
        "miss_count": 0,
        "hit_rate": 0.0,
        "no_decision_count": 0,
        "no_decision_rate": 0.0,
        "data_blocked_count": 0,
        "data_blocked_rate": 0.0,
        "result_unknown_count": 0,
        "result_unknown_rate": 0.0,
        "average_confidence": 0.0,
        "hit_rate_by_decision_class": {},
        "hit_rate_by_competition": {},
        "top_block_reasons": {},
        "top_no_decision_reasons": {},
        "top_risk_notes": {},
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "productive_betting_enabled": False,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(float(numerator / denominator), 4) if denominator else 0.0


def _group_hit_rate(frame: pd.DataFrame, group_cols: list[str]) -> dict[str, dict[str, object]]:
    if frame.empty or any(col not in frame.columns for col in group_cols):
        return {}
    out: dict[str, dict[str, object]] = {}
    for key, group in frame.groupby(group_cols, dropna=False):
        label = str(key if not isinstance(key, tuple) else "|".join(str(part) for part in key))
        evals = group["evaluation_result"].astype(str)
        decisions = int(evals.isin(["HIT", "MISS"]).sum())
        hits = int(evals.eq("HIT").sum())
        out[label] = {"n": int(len(group)), "decisions": decisions, "hits": hits, "hit_rate": _rate(hits, decisions)}
    return out


def _top_values(values: pd.Series) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for value in values.fillna("").astype(str):
        for item in value.replace("[", "").replace("]", "").replace("'", "").split(","):
            text = item.strip()
            if text:
                counter[text] += 1
    return dict(counter.most_common(10))
