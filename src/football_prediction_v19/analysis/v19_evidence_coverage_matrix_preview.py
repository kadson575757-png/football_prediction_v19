# -*- coding: utf-8 -*-
"""Evidence coverage matrix preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_match_pack_contract_preview import ALL_EVIDENCE_GROUPS, CRITICAL_PROMOTION_GROUPS, REQUIRED_EVIDENCE_GROUPS

V19_EVIDENCE_COVERAGE_MATRIX_PREVIEW_READY = "V19_EVIDENCE_COVERAGE_MATRIX_PREVIEW_READY"


def build_evidence_coverage_matrix(validation_rows: list[dict[str, object]], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [_coverage_row(row) for row in validation_rows]
    frame = pd.DataFrame(rows)
    csv_path = out / "evidence_coverage_matrix.csv"
    md_path = out / "evidence_coverage_matrix.md"
    frame.to_csv(csv_path, index=False)
    md_path.write_text("# v1.9 Evidence Coverage Matrix\n\n" + _table(frame) + "\n", encoding="utf-8")
    return {
        "evidence_coverage_matrix_status": V19_EVIDENCE_COVERAGE_MATRIX_PREVIEW_READY,
        "evidence_coverage_matrix_path": str(csv_path.resolve()),
        "evidence_coverage_matrix_md_path": str(md_path.resolve()),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _coverage_row(row: dict[str, object]) -> dict[str, object]:
    detected = set(_split(row.get("evidence_groups_detected", "")))
    missing = [group for group in ALL_EVIDENCE_GROUPS if group not in detected]
    required_hits = len([group for group in REQUIRED_EVIDENCE_GROUPS if group in detected])
    critical_hits = len([group for group in CRITICAL_PROMOTION_GROUPS if group in detected])
    score = round((required_hits * 12 + critical_hits * 5) / (len(REQUIRED_EVIDENCE_GROUPS) * 12 + len(CRITICAL_PROMOTION_GROUPS) * 5) * 100, 1)
    output = {"match_id": row.get("match_id", "")}
    for group in ALL_EVIDENCE_GROUPS:
        output[group] = group in detected
    output.update({
        "total_groups_detected": len(detected),
        "total_groups_missing": len(missing),
        "critical_groups_missing": row.get("critical_groups_missing", ""),
        "coverage_score": score,
        "health_status": row.get("health_status", ""),
    })
    return output


def _split(value: object) -> list[str]:
    return [part.strip() for part in str(value).split("|") if part.strip()]


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
