# -*- coding: utf-8 -*-
"""Final pipeline machine-readable JSON writer."""
from __future__ import annotations

import json
from pathlib import Path


def write_final_pipeline_json(output_path: str | Path, payload: dict[str, object]) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("safety", {})
    payload["safety"].update({
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "v19_release_candidate_enabled": True,
        "productive_betting_enabled": False,
        "automatic_betting_enabled": False,
    })
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path.resolve())
