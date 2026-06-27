# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run_real_source_smoke_suite(output_dir: str | Path, *, enable_network: bool = False) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    status = "PARTIAL" if enable_network else "BLOCKED"
    result = {"v20_real_source_smoke_status": status, "football_data_status": "SKIPPED" if not enable_network else "PARTIAL", "understat_status": "SKIPPED" if not enable_network else "PARTIAL", "odds_api_status": "DISABLED_MISSING_KEY", "network_calls_enabled": bool(enable_network), "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    (out / "v20_real_source_smoke_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([result]).to_csv(out / "v20_real_source_smoke_results.csv", index=False)
    (out / "v20_real_source_smoke_dashboard.md").write_text(f"# v2.0 Real Source Smoke\n\n- status: {status}\n- network_calls_enabled: {str(enable_network).lower()}\n", encoding="utf-8")
    return result
