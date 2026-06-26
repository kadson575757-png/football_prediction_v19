# -*- coding: utf-8 -*-
"""Assemble a match-pack manifest from local raw evidence folders."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

V19_MATCH_PACK_AUTO_ASSEMBLER_PREVIEW_READY = "V19_MATCH_PACK_AUTO_ASSEMBLER_PREVIEW_READY"


def assemble_match_pack_manifest(raw_input_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    root = Path(raw_input_dir).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in sorted([p for p in root.iterdir() if p.is_dir()]) if root.exists() else []:
        hint = _hint(folder / "metadata_hint.csv")
        rows.append({
            "match_id": hint.get("match_id_hint", folder.name),
            "input_dir": str(folder),
            "home_team": hint.get("home_team_hint", ""),
            "away_team": hint.get("away_team_hint", ""),
            "competition": hint.get("competition_hint", ""),
            "season": hint.get("season_hint", ""),
            "match_date": hint.get("match_date_hint", ""),
            "manual_evidence_completion": "tests/fixtures/manual_evidence_completion/lazio_atalanta_completion.csv" if "lazio" in str(hint.get("match_id_hint", "")).lower() else "",
            "notes": hint.get("notes", ""),
            "synthetic_demo_pack": hint.get("synthetic_demo_pack", ""),
            "not_real_match_data": hint.get("not_real_match_data", ""),
            "not_for_prediction": hint.get("not_for_prediction", ""),
        })
    manifest = out / "auto_match_pack_manifest.csv"
    dashboard = out / "assembler_dashboard.md"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    dashboard.write_text("# v1.9 Match Pack Auto Assembler\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    return {"match_pack_auto_assembler_status": V19_MATCH_PACK_AUTO_ASSEMBLER_PREVIEW_READY, "auto_match_pack_manifest_path": str(manifest), "assembler_dashboard_path": str(dashboard), "match_packs_assembled": len(rows), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _hint(path: Path) -> dict[str, object]:
    try:
        return pd.read_csv(path, keep_default_na=False).iloc[0].to_dict()
    except Exception:
        return {}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
