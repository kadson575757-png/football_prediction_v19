# -*- coding: utf-8 -*-
"""Match pack scanner preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_evidence_coverage_matrix_preview import build_evidence_coverage_matrix
from football_prediction_v19.analysis.v19_match_pack_contract_preview import ALL_EVIDENCE_GROUPS, MatchPackValidationResult, validate_match_pack

V19_MATCH_PACK_SCAN_PREVIEW_READY = "V19_MATCH_PACK_SCAN_PREVIEW_READY"


@dataclass(frozen=True)
class V19MatchPackScannerConfig:
    manifest: str | Path | None = None
    root_dir: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_match_pack_scan"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19MatchPackScannerResult:
    match_pack_scan_status: str
    match_pack_scan_enabled: bool
    output_dir: str
    packs_total: int
    packs_ready: int
    packs_partial: int
    packs_blocked: int
    packs_invalid: int
    auto_batch_config_path: str
    match_pack_scan_dashboard_path: str
    match_pack_registry_path: str
    match_pack_registry_md_path: str
    match_pack_validation_results_json_path: str
    match_pack_validation_results_csv_path: str
    match_pack_health_summary_path: str
    evidence_coverage_matrix_path: str
    evidence_coverage_matrix_md_path: str
    match_pack_scan_bundle_index_path: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19MatchPackScanner:
    def __init__(self, config: V19MatchPackScannerConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19MatchPackScannerResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        rows = self._load_rows()
        validations = [validate_match_pack(row, base_dir=self.base).to_dict() for row in rows]
        registry = [_registry_row(row, validation) for row, validation in zip(rows, validations)]
        paths = {
            "dashboard": out / "match_pack_scan_dashboard.md",
            "registry": out / "match_pack_registry.csv",
            "registry_md": out / "match_pack_registry.md",
            "validation_json": out / "match_pack_validation_results.json",
            "validation_csv": out / "match_pack_validation_results.csv",
            "health_summary": out / "match_pack_health_summary.md",
            "auto_batch_config": out / "auto_batch_config.csv",
            "bundle": out / "match_pack_scan_bundle_index.csv",
        }
        pd.DataFrame(registry).to_csv(paths["registry"], index=False)
        pd.DataFrame(validations).to_csv(paths["validation_csv"], index=False)
        paths["validation_json"].write_text(json.dumps({"match_pack_scan_status": V19_MATCH_PACK_SCAN_PREVIEW_READY, "packs_total": len(validations), "validation_results": validations, "safety": _safety()}, indent=2), encoding="utf-8")
        paths["registry_md"].write_text("# v1.9 Match Pack Registry\n\n" + _table(pd.DataFrame(registry)) + "\n", encoding="utf-8")
        coverage = build_evidence_coverage_matrix(validations, out)
        paths["health_summary"].write_text(_health_summary(validations), encoding="utf-8")
        paths["dashboard"].write_text(_dashboard(validations, registry, paths["auto_batch_config"]), encoding="utf-8")
        _write_recommended_batch_config(paths["auto_batch_config"], rows, validations)
        bundle_paths = dict(paths)
        bundle_paths["evidence_coverage_matrix"] = Path(coverage["evidence_coverage_matrix_path"])
        bundle_paths["evidence_coverage_matrix_md"] = Path(coverage["evidence_coverage_matrix_md_path"])
        _write_bundle(paths["bundle"], bundle_paths)
        counts = _counts(validations)
        return V19MatchPackScannerResult(
            V19_MATCH_PACK_SCAN_PREVIEW_READY, True, str(out.resolve()), len(validations), counts["READY"], counts["PARTIAL"], counts["BLOCKED"], counts["INVALID"], str(paths["auto_batch_config"].resolve()), str(paths["dashboard"].resolve()), str(paths["registry"].resolve()), str(paths["registry_md"].resolve()), str(paths["validation_json"].resolve()), str(paths["validation_csv"].resolve()), str(paths["health_summary"].resolve()), str(Path(coverage["evidence_coverage_matrix_path"]).resolve()), str(Path(coverage["evidence_coverage_matrix_md_path"]).resolve()), str(paths["bundle"].resolve()), False, False, False, False, False, V19_MATCH_PACK_SCAN_PREVIEW_READY
        )

    def _load_rows(self) -> list[dict[str, object]]:
        if self.config.manifest:
            path = _resolve(self.config.manifest, self.base)
            return pd.read_csv(path, keep_default_na=False).to_dict(orient="records")
        root = _resolve(self.config.root_dir or "tests/fixtures/excel_evidence", self.base)
        rows = []
        for child in sorted(root.iterdir()) if root.exists() else []:
            if child.is_dir():
                rows.append({"match_id": child.name, "input_dir": str(child), "home_team": "", "away_team": "", "competition": "", "season": "", "match_date": "", "manual_evidence_completion": "", "notes": "folder discovery"})
        return rows


def _registry_row(row: dict[str, object], validation: dict[str, object]) -> dict[str, object]:
    return {
        "match_id": row.get("match_id", ""),
        "match": f"{row.get('home_team', '')} vs {row.get('away_team', '')}",
        "competition": row.get("competition", ""),
        "date": row.get("match_date", ""),
        "input_dir": row.get("input_dir", ""),
        "files_detected_count": validation.get("files_detected_count", 0),
        "health_status": validation.get("health_status", ""),
        "can_run_batch_os": validation.get("can_run_batch_os", False),
        "synthetic_demo_pack": validation.get("synthetic_demo_pack", False),
        "not_real_match_data": validation.get("not_real_match_data", False),
        "not_for_prediction": validation.get("not_for_prediction", False),
    }


def _write_recommended_batch_config(path: Path, rows: list[dict[str, object]], validations: list[dict[str, object]]) -> None:
    included = []
    for row, validation in zip(rows, validations):
        if validation.get("can_run_workbench") is True:
            included.append({
                "match_id": row.get("match_id", ""),
                "input_dir": row.get("input_dir", ""),
                "home_team": row.get("home_team", ""),
                "away_team": row.get("away_team", ""),
                "competition": row.get("competition", ""),
                "season": row.get("season", ""),
                "match_date": row.get("match_date", ""),
                "manual_evidence_completion": row.get("manual_evidence_completion", ""),
                "run_transition_lab": "false",
                "notes": row.get("notes", ""),
            })
    pd.DataFrame(included).to_csv(path, index=False)


def _dashboard(validations: list[dict[str, object]], registry: list[dict[str, object]], auto_batch_config: Path) -> str:
    counts = _counts(validations)
    coverage = []
    for group in ALL_EVIDENCE_GROUPS:
        detected = len([row for row in validations if group in _split(row.get("evidence_groups_detected", ""))])
        coverage.append({"evidence_group": group, "packs_detected": detected, "packs_missing": len(validations) - detected, "coverage_pct": round(detected / len(validations) * 100, 1) if validations else 0})
    missing = []
    for row in validations:
        for group in _split(row.get("critical_groups_missing", "")):
            missing.append({"match_id": row.get("match_id", ""), "missing_group": group, "severity": "CRITICAL_FOR_PROMOTION", "impact": "Blocks promotion confidence", "next_action": f"Add {group} evidence"})
    return "\n".join([
        "# v1.9 Match Pack Scan Dashboard",
        "",
        "## 1. Scan Status",
        f"- scan_status: {V19_MATCH_PACK_SCAN_PREVIEW_READY}",
        f"- packs_total: {len(validations)}",
        f"- packs_ready: {counts['READY']}",
        f"- packs_partial: {counts['PARTIAL']}",
        f"- packs_blocked: {counts['BLOCKED']}",
        f"- packs_invalid: {counts['INVALID']}",
        "- safety status: preview-only; network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false",
        "",
        "## 2. Match Pack Registry",
        _table(pd.DataFrame(registry)),
        "",
        "## 3. Evidence Group Coverage",
        _table(pd.DataFrame(coverage)),
        "",
        "## 4. Critical Missing Groups",
        _table(pd.DataFrame(missing)),
        "",
        "## 5. Recommended Batch Config",
        str(auto_batch_config.resolve()),
        "",
        "## 6. Safety Footer",
        "Preview only. No production betting. No stake. No ROI. No automatic betting.",
        "",
    ])


def _health_summary(validations: list[dict[str, object]]) -> str:
    return "# v1.9 Match Pack Health Summary\n\n" + _table(pd.DataFrame(validations)) + "\n"


def _counts(validations: list[dict[str, object]]) -> dict[str, int]:
    return {status: len([row for row in validations if row.get("health_status") == status]) for status in ["READY", "PARTIAL", "BLOCKED", "INVALID"]}


def _split(value: object) -> list[str]:
    return [part.strip() for part in str(value).split("|") if part.strip()]


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


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
