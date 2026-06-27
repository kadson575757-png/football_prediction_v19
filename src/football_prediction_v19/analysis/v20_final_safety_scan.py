# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


FORBIDDEN = ["automatic_betting_enabled=true", "staking_logic_enabled=true", "roi_logic_enabled=true", "profit_enabled=true"]


def run_v20_final_safety_scan(repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    offenders = []
    for path in list((root / "src").glob("**/v20*.py")) + list((root / "scripts").glob("run_v20*.py")):
        if path.name == "v20_final_safety_scan.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in FORBIDDEN:
            if token in text:
                offenders.append(str(path))
    return {"safety_scan_status": "PASSED" if not offenders else "FAILED", "offenders": offenders, "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
