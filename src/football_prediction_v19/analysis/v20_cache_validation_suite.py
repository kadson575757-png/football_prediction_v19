# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run_cache_validation_suite(cache_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    cache_path = Path(cache_dir)
    cache_files = list(cache_path.glob("**/*")) if cache_path.exists() else []
    status = "READY" if cache_files else "BLOCKED"
    result = {"v20_cache_validation_status": status, "cache_used": bool(cache_files), "cache_files_count": len(cache_files), "network_calls_enabled": False, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    (out / "v20_cache_validation_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([result]).to_csv(out / "v20_cache_validation_results.csv", index=False)
    (out / "v20_cache_validation_dashboard.md").write_text(f"# v2.0 Cache Validation\n\n- status: {status}\n- cache_used: {str(result['cache_used']).lower()}\n", encoding="utf-8")
    return result
