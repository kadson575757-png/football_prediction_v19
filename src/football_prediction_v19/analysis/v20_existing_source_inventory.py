# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

SOURCES = {
    "football_data": ["src/football_prediction_v19/importers/football_data.py"],
    "fbref": ["src/football_prediction_v19/importers/fbref.py"],
    "xg_importer": ["src/football_prediction_v19/importers/manual_xg_csv.py", "src/football_prediction_v19/importers/trusted_xg_source.py"],
    "understat_provider_preview": ["src/football_prediction_v19/importers/understat_provider_pull_preview.py", "src/football_prediction_v19/importers/understat_join_diagnostics.py"],
    "historical_odds": ["src/football_prediction_v19/importers/historical_odds.py"],
    "totals_odds": ["src/football_prediction_v19/importers/the_odds_api.py"],
    "v19_decision_engine_preview": ["src/football_prediction_v19/analysis/v19_decision_engine_preview.py"],
    "v19_final_pipeline_preview": ["src/football_prediction_v19/analysis/v19_final_pipeline_preview.py"],
}


def build_existing_source_inventory(output_dir: str | Path, *, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for source, paths in SOURCES.items():
        found = [p for p in paths if (root / p).exists()]
        status = "REUSE_READY" if found else "MISSING"
        if found and len(found) < len(paths):
            status = "PARTIAL"
        rows.append({"source": source, "status": status, "paths_found": " | ".join(found), "purpose": "reuse existing repo source"})
    frame = pd.DataFrame(rows)
    csv_path = out / "existing_source_inventory.csv"; md_path = out / "existing_source_inventory.md"; json_path = out / "existing_source_inventory.json"
    frame.to_csv(csv_path, index=False)
    md_path.write_text("# v2.0 Existing Source Inventory\n\n" + _table(frame) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps({"existing_source_inventory_status": "READY", "sources": rows}, indent=2), encoding="utf-8")
    return {"existing_source_inventory_status": "READY", "existing_source_inventory_md_path": str(md_path), "existing_source_inventory_json_path": str(json_path), "existing_source_inventory_csv_path": str(csv_path)}


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns); lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(c, "")).replace("|", ",") for c in cols) + " |")
    return "\n".join(lines)
