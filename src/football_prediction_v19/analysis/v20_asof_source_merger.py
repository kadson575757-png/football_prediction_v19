# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


def merge_asof_sources(football: dict[str, object], xg: dict[str, object], odds: dict[str, object], leakage: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    coverage = {"table_available": bool(football.get("table_available")), "form_available": bool(football.get("form_available")), "xg_available": bool(xg.get("xg_available")), "player_xg_available": bool(xg.get("player_xg_available")), "odds_1x2_available": bool(odds.get("odds_1x2_available")), "odds_totals_available": bool(odds.get("odds_totals_available")), "h2h_available": False, "injuries_available": False, "lineups_available": False, "leakage_clean": leakage.get("leakage_status") == "CLEAN"}
    status = "ASOF_BLOCKED" if not coverage["leakage_clean"] else ("ASOF_READY" if coverage["table_available"] and coverage["xg_available"] and coverage["odds_1x2_available"] else "ASOF_PARTIAL")
    payload = {"asof_status": status, "coverage": coverage, "inputs": {"football": football, "xg": xg, "odds": odds, "leakage": leakage}}
    (out / "asof_merged_dataset.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame([coverage | {"asof_status": status}]).to_csv(out / "asof_source_coverage_matrix.csv", index=False)
    (out / "asof_merged_dataset_report.md").write_text("# v2.0 As-Of Merged Dataset Report\n\n" + str(coverage) + "\n", encoding="utf-8")
    return {"asof_status": status, **coverage, "asof_merged_dataset_path": str((out / "asof_merged_dataset.json").resolve()), "asof_source_coverage_matrix_path": str((out / "asof_source_coverage_matrix.csv").resolve()), "asof_merged_dataset_report_path": str((out / "asof_merged_dataset_report.md").resolve())}
