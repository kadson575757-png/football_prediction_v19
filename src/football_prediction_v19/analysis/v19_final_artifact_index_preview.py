# -*- coding: utf-8 -*-
"""Final artifact index writer."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_final_artifact_index(output_dir: str | Path, artifact_paths: dict[str, str]) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, path in artifact_paths.items():
        p = Path(path)
        rows.append({
            "artifact_group": _group(name),
            "artifact_name": name,
            "path": str(p),
            "format": p.suffix.lstrip(".") or "directory",
            "purpose": _purpose(name),
            "open_first": name in {"final_pipeline_dashboard", "final_user_guide", "final_action_plan", "final_release_readiness_report", "batch_os_executive_dashboard", "master_completion_template"},
            "user_facing": True,
        })
    frame = pd.DataFrame(rows)
    csv_path = out / "final_artifact_index.csv"
    md_path = out / "final_artifact_index.md"
    frame.to_csv(csv_path, index=False)
    md_path.write_text("# v1.9 Final Artifact Index\n\n" + _table(frame) + "\n", encoding="utf-8")
    return {"final_artifact_index_path": str(md_path.resolve()), "final_artifact_index_csv_path": str(csv_path.resolve())}


def _group(name: str) -> str:
    for key, group in [("raw", "Raw Intake"), ("match_pack", "Match Pack Assembly"), ("health", "Health Gate"), ("batch_os", "Batch OS"), ("completion", "Completion"), ("delta", "Delta"), ("scenario", "Scenario Lab"), ("smoke", "Smoke Tests"), ("json", "Machine JSON")]:
        if key in name:
            return group
    return "Final Reports"


def _purpose(name: str) -> str:
    return name.replace("_", " ").title()


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
