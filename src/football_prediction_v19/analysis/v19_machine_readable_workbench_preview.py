# -*- coding: utf-8 -*-
"""Machine-readable JSON writer for the v1.9 match workbench preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

V19_MACHINE_READABLE_WORKBENCH_PREVIEW_READY = "V19_MACHINE_READABLE_WORKBENCH_PREVIEW_READY"


@dataclass(frozen=True)
class V19MachineReadableWorkbenchConfig:
    payload: dict[str, object]
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19MachineReadableWorkbenchResult:
    machine_readable_workbench_status: str
    machine_readable_workbench_path: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19MachineReadableWorkbenchWriter:
    def __init__(self, config: V19MachineReadableWorkbenchConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19MachineReadableWorkbenchResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "machine_readable_workbench.json"
        payload = dict(self.config.payload)
        payload.setdefault("safety", {})
        payload["safety"].update({
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
            "workbench_preview_enabled": True,
        })
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return V19MachineReadableWorkbenchResult(V19_MACHINE_READABLE_WORKBENCH_PREVIEW_READY, str(path.resolve()), False, False, False, False, V19_MACHINE_READABLE_WORKBENCH_PREVIEW_READY)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
