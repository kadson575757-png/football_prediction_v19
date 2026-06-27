# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import pandas as pd


def write_backtest_leakage_audit(rows: list[dict[str, object]], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    audit_rows = [{"match_id": r.get("match_id"), "leakage_status": r.get("leakage_status"), "cutoff": r.get("analysis_cutoff")} for r in rows]
    path = out / "v20_backtest_leakage_audit.csv"
    pd.DataFrame(audit_rows).to_csv(path, index=False)
    return {"v20_backtest_leakage_audit_path": str(path.resolve()), "leakage_blocked_count": sum(1 for r in rows if r.get("leakage_status") == "BLOCKED")}
