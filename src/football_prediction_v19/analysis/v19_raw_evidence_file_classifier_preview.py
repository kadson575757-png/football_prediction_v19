# -*- coding: utf-8 -*-
"""Local raw evidence file classifier for v1.9 preview."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

V19_RAW_EVIDENCE_FILE_CLASSIFIER_PREVIEW_READY = "V19_RAW_EVIDENCE_FILE_CLASSIFIER_PREVIEW_READY"


def classify_raw_evidence_files(raw_input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(raw_input_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(root.rglob("*")) if root.exists() else []:
        if path.is_file():
            rows.append({
                "raw_group_id": path.parent.name,
                "file_name": path.name,
                "path": str(path.resolve()),
                "file_role": _role(path.name),
                "synthetic_demo_pack": _hint_bool(path.parent / "metadata_hint.csv", "synthetic_demo_pack"),
                "not_real_match_data": _hint_bool(path.parent / "metadata_hint.csv", "not_real_match_data"),
                "not_for_prediction": _hint_bool(path.parent / "metadata_hint.csv", "not_for_prediction"),
            })
    frame = pd.DataFrame(rows)
    csv_path = out / "raw_file_classification.csv"
    json_path = out / "raw_file_classification.json"
    md_path = out / "raw_file_classification_dashboard.md"
    frame.to_csv(csv_path, index=False)
    payload = {"raw_file_classification_status": V19_RAW_EVIDENCE_FILE_CLASSIFIER_PREVIEW_READY, "files_total": len(rows), "files": rows, "safety": _safety()}
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text("# v1.9 Raw File Classification Dashboard\n\n" + _table(frame) + "\n\nPreview only. No network calls.\n", encoding="utf-8")
    return {"raw_file_classification_status": V19_RAW_EVIDENCE_FILE_CLASSIFIER_PREVIEW_READY, "files_total": len(rows), "raw_file_classification_path": str(csv_path), "raw_file_classification_json_path": str(json_path), "raw_file_classification_dashboard_path": str(md_path), **_safety()}


def _role(name: str) -> str:
    lower = name.lower()
    if lower == "metadata_hint.csv":
        return "METADATA_HINT"
    if "team-statistics" in lower or "statistics" in lower:
        return "TEAM_STATISTICS"
    if "team-players" in lower or "players" in lower:
        return "TEAM_PLAYERS"
    return "UNKNOWN_EVIDENCE"


def _hint_bool(path: Path, column: str) -> bool:
    try:
        frame = pd.read_csv(path, keep_default_na=False)
        return str(frame.iloc[0].get(column, "")).strip().lower() == "true"
    except Exception:
        return False


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
