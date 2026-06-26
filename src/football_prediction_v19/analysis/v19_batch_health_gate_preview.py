# -*- coding: utf-8 -*-
"""Batch health gate preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_BATCH_HEALTH_GATE_PREVIEW_READY = "V19_BATCH_HEALTH_GATE_PREVIEW_READY"


@dataclass(frozen=True)
class V19BatchHealthGateConfig:
    validation_json: str | Path
    batch_results_json: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_batch_health_gate"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchHealthGateResult:
    batch_health_gate_status: str
    batch_health_status: str
    batch_health_gate_enabled: bool
    output_dir: str
    packs_total: int
    packs_ready: int
    packs_partial: int
    packs_blocked: int
    packs_invalid: int
    can_run_batch_os: bool
    can_run_completion_campaign: bool
    can_run_portfolio_delta: bool
    critical_issues: str
    warnings: str
    recommended_action: str
    batch_health_gate_report_path: str
    batch_health_gate_result_json_path: str
    batch_health_gate_matrix_path: str
    batch_health_gate_bundle_index_path: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class V19BatchHealthGateRunner:
    def __init__(self, config: V19BatchHealthGateConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchHealthGateResult:
        payload = _read_json(_resolve(self.config.validation_json, self.base))
        rows = [row for row in payload.get("validation_results", []) if isinstance(row, dict)]
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        counts = _counts(rows)
        runnable = len([row for row in rows if row.get("can_run_batch_os") is True])
        health = _health_status(counts, runnable)
        critical = [f"{row.get('match_id')}: {row.get('errors')}" for row in rows if row.get("errors")]
        warnings = [f"{row.get('match_id')}: {row.get('warnings')}" for row in rows if row.get("warnings")]
        action = _recommended_action(health, critical, warnings)
        paths = {"report": out / "batch_health_gate_report.md", "result": out / "batch_health_gate_result.json", "matrix": out / "batch_health_gate_matrix.csv", "bundle": out / "batch_health_gate_bundle_index.csv"}
        pd.DataFrame(rows).to_csv(paths["matrix"], index=False)
        result_payload = {
            "batch_health_gate_status": V19_BATCH_HEALTH_GATE_PREVIEW_READY,
            "batch_health_status": health,
            "packs_total": len(rows),
            "packs_ready": counts["READY"],
            "packs_partial": counts["PARTIAL"],
            "packs_blocked": counts["BLOCKED"],
            "packs_invalid": counts["INVALID"],
            "can_run_batch_os": runnable > 0,
            "can_run_completion_campaign": runnable > 0,
            "can_run_portfolio_delta": runnable > 0,
            "critical_issues": critical,
            "warnings": warnings,
            "recommended_action": action,
            "safety": _safety(),
        }
        paths["result"].write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
        paths["report"].write_text(_report(result_payload, rows), encoding="utf-8")
        _write_bundle(paths["bundle"], paths)
        return V19BatchHealthGateResult(V19_BATCH_HEALTH_GATE_PREVIEW_READY, health, True, str(out.resolve()), len(rows), counts["READY"], counts["PARTIAL"], counts["BLOCKED"], counts["INVALID"], runnable > 0, runnable > 0, runnable > 0, " | ".join(critical), " | ".join(warnings), action, str(paths["report"].resolve()), str(paths["result"].resolve()), str(paths["matrix"].resolve()), str(paths["bundle"].resolve()), False, False, False, False, False)


def _health_status(counts: dict[str, int], runnable: int) -> str:
    if counts["INVALID"] and runnable == 0:
        return "INVALID"
    if runnable == 0:
        return "BLOCKED"
    if counts["BLOCKED"] or counts["INVALID"] or counts["PARTIAL"]:
        return "PARTIAL_READY"
    return "READY"


def _recommended_action(status: str, critical: list[str], warnings: list[str]) -> str:
    if status == "READY":
        return "RUN_BATCH_OS"
    if status == "PARTIAL_READY":
        return "RUN_BATCH_OS_FOR_READY_PACKS_AND_FILL_MISSING_EVIDENCE"
    if critical:
        return "FIX_INVALID_OR_BLOCKED_PACKS_FIRST"
    return "ADD_MATCH_PACK_EVIDENCE"


def _report(payload: dict[str, object], rows: list[dict[str, object]]) -> str:
    return "\n".join([
        "# v1.9 Batch Health Gate Preview",
        "",
        "## 1. Gate Status",
        f"- batch_health_gate_status: {payload['batch_health_gate_status']}",
        f"- batch_health_status: {payload['batch_health_status']}",
        "",
        "## 2. Pack Health Summary",
        _table(pd.DataFrame(rows)),
        "",
        "## 3. Critical Issues",
        "\n".join(f"- {item}" for item in payload["critical_issues"]) or "- none",
        "",
        "## 4. What Can Run",
        f"- can_run_batch_os: {str(payload['can_run_batch_os']).lower()}",
        f"- can_run_completion_campaign: {str(payload['can_run_completion_campaign']).lower()}",
        f"- can_run_portfolio_delta: {str(payload['can_run_portfolio_delta']).lower()}",
        "",
        "## 5. What Is Blocked",
        "\n".join(f"- {item}" for item in payload["warnings"]) or "- none",
        "",
        "## 6. Recommended Next Action",
        str(payload["recommended_action"]),
        "",
        "## 7. Safety Footer",
        "Preview only. No production betting. No stake. No ROI. No automatic betting.",
        "",
    ])


def _counts(rows: list[dict[str, object]]) -> dict[str, int]:
    return {status: len([row for row in rows if row.get("health_status") == status]) for status in ["READY", "PARTIAL", "BLOCKED", "INVALID"]}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() or p == path else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
