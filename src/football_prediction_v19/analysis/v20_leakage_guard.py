# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext, parse_dt


@dataclass(frozen=True)
class SourceSnapshot:
    source_name: str
    source_kind: str
    data_timestamp: str
    records_count: int = 0
    is_critical: bool = False
    fetched_at: str = ""
    source_path: str = ""


def run_leakage_guard(context: HistoricalMatchContext, snapshots: list[SourceSnapshot], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    cutoff = parse_dt(context.analysis_cutoff)
    rows = []
    critical_bad = False; unknown_noncritical = False
    for snap in snapshots:
        status = "UNKNOWN_TIMESTAMP"
        if snap.data_timestamp:
            status = "CLEAN" if parse_dt(snap.data_timestamp) <= cutoff else "AFTER_CUTOFF"
        if status == "AFTER_CUTOFF" and snap.is_critical:
            critical_bad = True
        if status == "UNKNOWN_TIMESTAMP" and not snap.is_critical:
            unknown_noncritical = True
        rows.append({**asdict(snap), "leakage_status": status})
    leakage_status = "BLOCKED" if critical_bad else ("PARTIAL" if unknown_noncritical else "CLEAN")
    excluded = pd.DataFrame([r for r in rows if r["leakage_status"] != "CLEAN"])
    excluded_path = out / "leakage_guard_excluded_sources.csv"; excluded.to_csv(excluded_path, index=False)
    result = {"leakage_guard_status": "READY", "leakage_status": leakage_status, "snapshots_total": len(rows), "excluded_sources": len(excluded), "safety": _safety()}
    (out / "leakage_guard_result.json").write_text(json.dumps({**result, "sources": rows}, indent=2), encoding="utf-8")
    (out / "leakage_guard_report.md").write_text("# v2.0 Leakage Guard Report\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    result.update({"leakage_guard_result_json_path": str((out / "leakage_guard_result.json").resolve()), "leakage_guard_report_path": str((out / "leakage_guard_report.md").resolve()), "leakage_guard_excluded_sources_path": str(excluded_path.resolve())})
    return result


def _table(frame: pd.DataFrame) -> str:
    if frame.empty: return "No rows."
    cols = list(frame.columns); lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows(): lines.append("| " + " | ".join(str(row.get(c, "")).replace("|", ",") for c in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
