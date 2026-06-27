# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_THRESHOLDS = {"model_tip_confidence": 0.70, "analyst_lean_confidence": 0.55, "low_quality_no_bet": 0.45, "medium_quality": 0.65, "high_quality": 0.85}


def calibrate_v20_model_policy(output_dir: str | Path, thresholds: dict[str, float] | None = None) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    data = thresholds or DEFAULT_THRESHOLDS
    result = {"v20_model_policy_calibration_status": "READY", "thresholds": data, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    (out / "v20_model_policy_thresholds.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (out / "v20_model_policy_calibration_report.md").write_text("# v2.0 Model Policy Calibration\n\nNo exact score tip. No stake. No ROI.\n", encoding="utf-8")
    (out / "v20_decision_policy_audit.md").write_text("# v2.0 Decision Policy Audit\n\nLOW quality => NO_BET. BLOCKED quality => DATA_BLOCKED.\n", encoding="utf-8")
    return result
