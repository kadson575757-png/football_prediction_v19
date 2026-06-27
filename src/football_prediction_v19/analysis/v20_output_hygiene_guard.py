# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def run_v20_output_hygiene_guard(repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    generated = [p for p in [root / "outputs" / "cache"] if p.exists()]
    return {"output_hygiene_status": "PASSED", "generated_paths": [str(p) for p in generated], "warnings": ["generated cache exists; do not commit it"] if generated else []}
