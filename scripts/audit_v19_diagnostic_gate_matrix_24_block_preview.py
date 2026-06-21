# -*- coding: utf-8 -*-
"""Audit v1.9 diagnostic gate matrix integration into the 24-block report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from build_human_24_block_report_preview import build_human_24_block_report_preview  # noqa: E402
from build_v19_diagnostic_gate_matrix_preview import build_v19_diagnostic_gate_matrix_preview  # noqa: E402
from build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview  # noqa: E402
from football_prediction_v19.analysis.human_24_block_report_preview import HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY, REQUIRED_SECTIONS  # noqa: E402
from football_prediction_v19.analysis.v19_diagnostic_gate_matrix_preview import V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY  # noqa: E402

V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY = "V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY"
BUILD_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW = "BUILD_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW"
FIX_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW = "FIX_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW"
OUTPUT_CSV = "v19_diagnostic_gate_matrix_24_block_preview_summary.csv"
OUTPUT_MD = "v19_diagnostic_gate_matrix_24_block_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
FORBIDDEN_REPORT_TERMS = ["stake size", "roi", "super_a_tier", "super_a", "bet this", " units"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-matrix-manifest", default=None)
    parser.add_argument("--report-manifest", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    return value if isinstance(value, bool) else str(value).strip().lower() in {"true", "1", "yes"}


def _under(path_text: str, base: Path, rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _protected(path_text: str) -> bool:
    return any(token in str(path_text).replace("\\", "/").lower() for token in PROTECTED)


def audit_pair(gate_matrix_manifest: Path, report_manifest: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    gate_row = pd.read_csv(gate_matrix_manifest, low_memory=False).iloc[0]
    report_row = pd.read_csv(report_manifest, low_memory=False).iloc[0]
    report_path = str(report_row.get("report_output_path", ""))
    report_text = Path(report_path).read_text(encoding="utf-8") if report_path and Path(report_path).exists() else ""
    lower_text = report_text.lower()
    sections_rendered = sum(1 for section in REQUIRED_SECTIONS if f"## {section}" in report_text)
    gates_evaluated = int(gate_row.get("gates_evaluated", 0))
    matrix_ready = str(gate_row.get("v19_diagnostic_gate_matrix_status", "")) == V19_DIAGNOSTIC_GATE_MATRIX_PREVIEW_READY
    report_ready = str(report_row.get("human_24_block_report_status", "")) == HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY
    integrated = all(term in report_text for term in [
        "Gate matrix diagnostics:",
        "hard_1x2_control_model_gate",
        "chaos_score_gate",
        "underdog_win_score_gate",
        "score_family_readiness_gate",
        "Betting output is disabled in this diagnostic gate preview layer.",
    ])
    safe_paths = _under(report_path, base, "outputs/analysis_preview") and not _protected(report_path)
    no_forbidden_terms = not any(term in lower_text for term in FORBIDDEN_REPORT_TERMS)
    flags_disabled = not any(_as_bool(report_row.get(column, False)) for column in [
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled",
    ])
    for ok, label in [
        (matrix_ready, "GATE_MATRIX_NOT_READY"),
        (report_ready, "REPORT_NOT_READY"),
        (gates_evaluated >= 19, "GATES_NOT_EVALUATED"),
        (sections_rendered == 24, "SECTIONS_NOT_READY"),
        (integrated, "GATE_MATRIX_NOT_INTEGRATED"),
        (safe_paths, "UNSAFE_REPORT_PATH"),
        (no_forbidden_terms, "FORBIDDEN_PRODUCTION_LANGUAGE_PRESENT"),
        (flags_disabled, "RUNTIME_FLAGS_ENABLED"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "gate_matrix_manifest": str(gate_matrix_manifest),
        "report_manifest": str(report_manifest),
        "v19_diagnostic_gate_matrix_status": str(gate_row.get("v19_diagnostic_gate_matrix_status", "")),
        "human_24_block_report_status": str(report_row.get("human_24_block_report_status", "")),
        "gates_evaluated": gates_evaluated,
        "gates_blocked": int(gate_row.get("gates_blocked", 0)),
        "gates_disabled": int(gate_row.get("gates_disabled", 0)),
        "blocked_gate_count": int(gate_row.get("blocked_gate_count", 0)),
        "rows_reported": int(report_row.get("rows_reported", 0)),
        "sections_rendered": sections_rendered,
        "required_sections_rendered": sections_rendered,
        "gate_matrix_integrated": integrated,
        "network_calls_enabled": _as_bool(report_row.get("network_calls_enabled", False)),
        "prediction_logic_enabled": _as_bool(report_row.get("prediction_logic_enabled", False)),
        "betting_logic_enabled": _as_bool(report_row.get("betting_logic_enabled", False)),
        "staking_logic_enabled": _as_bool(report_row.get("staking_logic_enabled", False)),
        "roi_logic_enabled": _as_bool(report_row.get("roi_logic_enabled", False)),
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW
    if table["preview_valid"].any():
        return V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW_READY
    return FIX_V19_DIAGNOSTIC_GATE_MATRIX_24_BLOCK_PREVIEW


def run(
    *,
    gate_matrix_manifest: str | Path | None = None,
    report_manifest: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    matrix_manifest = Path(gate_matrix_manifest) if gate_matrix_manifest else None
    rpt_manifest = Path(report_manifest) if report_manifest else None
    if matrix_manifest is None or rpt_manifest is None or not matrix_manifest.exists() or not rpt_manifest.exists():
        bridge = build_context_bundle_human_input_bridge_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input", base_dir=base)
        synthesis = build_v19_diagnostic_synthesis_preview(context_human_input_path=bridge["human_input_output_path"], cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis", base_dir=base, build_missing=False)
        matrix = build_v19_diagnostic_gate_matrix_preview(v19_diagnostic_synthesis_path=synthesis["output_path"], context_human_input_path=bridge["human_input_output_path"], cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix", base_dir=base, build_missing=False)
        report = build_human_24_block_report_preview(context_human_input_path=bridge["human_input_output_path"], v19_diagnostic_synthesis_path=synthesis["output_path"], v19_diagnostic_gate_matrix_path=matrix["gate_matrix_output_path"], output_dir=base / "outputs" / "analysis_preview" / "human_24_block_report", base_dir=base, build_missing=False)
        matrix_manifest = Path(str(matrix.get("manifest_path", "")))
        rpt_manifest = Path(str(report.get("manifest_path", "")))
    rows = [audit_pair(matrix_manifest, rpt_manifest, base_dir=base)] if matrix_manifest.exists() and rpt_manifest.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 23 v1.9 Diagnostic Gate Matrix 24-Block Audit",
        "",
        f"- flows audited: {len(table)}",
        f"- valid flows: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- gate matrix is preview-only",
        "- no production model, probability, market, betting, position sizing, financial-return, or SUPER_A_TIER logic is invoked",
        "",
        "## Recommendation",
        rec,
        "",
    ])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(gate_matrix_manifest=args.gate_matrix_manifest, report_manifest=args.report_manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
