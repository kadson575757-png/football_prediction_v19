# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_v19_batch_config_from_match_packs_preview import build_v19_batch_config_from_match_packs_preview  # noqa: E402
from scripts.run_v19_batch_health_gate_preview import run_v19_batch_health_gate_preview  # noqa: E402
from scripts.run_v19_batch_os_preview import run_v19_batch_os_preview  # noqa: E402
from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview  # noqa: E402

V19_MULTI_MATCH_BATCH_OS_DEMO_READY = "V19_MULTI_MATCH_BATCH_OS_DEMO_READY"


def run_v19_multi_match_batch_os_demo_preview(**kwargs: object) -> dict[str, object]:
    base = Path(kwargs.get("base_dir", ROOT)).resolve()
    out = _resolve(kwargs.get("output_dir", base / "outputs" / "analysis_preview" / "v19_multi_match_batch_os_demo"), base)
    out.mkdir(parents=True, exist_ok=True)
    manifest = kwargs["manifest"]
    scan = scan_v19_match_packs_preview(manifest=manifest, output_dir=out / "scan", emit_all=True, base_dir=base)
    config = build_v19_batch_config_from_match_packs_preview(manifest=manifest, output=out / "auto_batch_config.csv", include_partial=True, emit_all=True, base_dir=base)
    health = run_v19_batch_health_gate_preview(validation_json=scan["match_pack_validation_results_json_path"], output_dir=out / "health_gate", emit_all=True, base_dir=base)
    batch_os = run_v19_batch_os_preview(batch_config=config["output_path"], output_dir=out / "batch_os", emit_all=True, preflight_validation_json=health["batch_health_gate_result_json_path"], base_dir=base)
    paths = {
        "multi_match_demo_dashboard": out / "multi_match_demo_dashboard.md",
        "match_pack_scan_dashboard": out / "match_pack_scan_dashboard.md",
        "evidence_coverage_matrix_md": out / "evidence_coverage_matrix.md",
        "batch_health_gate_report": out / "batch_health_gate_report.md",
        "auto_batch_config": out / "auto_batch_config.csv",
        "auto_batch_config_report": out / "auto_batch_config_report.md",
        "executive_dashboard": out / "executive_dashboard.md",
        "batch_os_results": out / "batch_os_results.json",
        "multi_match_demo_results": out / "multi_match_demo_results.json",
        "bundle": out / "multi_match_demo_bundle_index.csv",
    }
    _copy(scan["match_pack_scan_dashboard_path"], paths["match_pack_scan_dashboard"])
    _copy(scan["evidence_coverage_matrix_md_path"], paths["evidence_coverage_matrix_md"])
    _copy(health["batch_health_gate_report_path"], paths["batch_health_gate_report"])
    _copy(config["report_path"], paths["auto_batch_config_report"])
    _copy(batch_os["executive_dashboard_path"], paths["executive_dashboard"])
    _copy(batch_os["batch_os_results_json_path"], paths["batch_os_results"])
    dashboard = _dashboard(scan, health, config, batch_os)
    paths["multi_match_demo_dashboard"].write_text(dashboard, encoding="utf-8")
    result = {
        "multi_match_demo_status": V19_MULTI_MATCH_BATCH_OS_DEMO_READY,
        "multi_match_demo_enabled": True,
        "match_pack_scan_status": scan["match_pack_scan_status"],
        "batch_health_gate_status": health["batch_health_gate_status"],
        "batch_os_status": batch_os["batch_os_status"],
        "packs_total": scan["packs_total"],
        "auto_batch_matches_included": config["matches_included"],
        "matches_total": batch_os["matches_total"],
        "matches_succeeded": batch_os["matches_succeeded"],
        "matches_failed": batch_os["matches_failed"],
        "multi_match_demo_dashboard_path": str(paths["multi_match_demo_dashboard"].resolve()),
        "batch_os_results_json_path": str(paths["batch_os_results"].resolve()),
        "multi_match_demo_bundle_index_path": str(paths["bundle"].resolve()),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    paths["multi_match_demo_results"].write_text(json.dumps(result, indent=2), encoding="utf-8")
    _write_bundle(paths["bundle"], paths)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_multi_match_batch_os_demo"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v19_multi_match_batch_os_demo_preview(manifest=args.manifest, output_dir=args.output_dir, emit_all=args.emit_all, base_dir=args.base_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


def _dashboard(scan: dict[str, object], health: dict[str, object], config: dict[str, object], batch_os: dict[str, object]) -> str:
    registry = _read_csv(scan["match_pack_registry_path"])
    coverage = _read_csv(scan["evidence_coverage_matrix_path"])
    best = coverage.sort_values("coverage_score", ascending=False).head(1)["match_id"].tolist() if not coverage.empty else ["none"]
    weakest = coverage.sort_values("coverage_score", ascending=True).head(1)["match_id"].tolist() if not coverage.empty else ["none"]
    return "\n".join([
        "# v1.9 Multi-Match Batch OS Demo Dashboard",
        "",
        "## 1. Demo Status",
        f"- demo status: {V19_MULTI_MATCH_BATCH_OS_DEMO_READY}",
        f"- packs scanned: {scan['packs_total']}",
        f"- packs included: {config['matches_included']}",
        f"- batch OS status: {batch_os['batch_os_status']}",
        "- safety status: preview-only; network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false",
        "",
        "## 2. Match Pack Health",
        _table(registry[["match_id", "match", "health_status", "can_run_batch_os"]] if not registry.empty else registry),
        "",
        "## 3. Evidence Coverage Matrix Summary",
        f"- best coverage pack: {best[0]}",
        f"- weakest coverage pack: {weakest[0]}",
        "- common missing groups: recent_form, big_chances, availability, opening_closing_odds, dnb_ou_market",
        "",
        "## 4. Auto Batch Config",
        f"- included: {config['matches_included']}",
        f"- excluded: {config['matches_excluded']}",
        "",
        "## 5. Batch OS Result",
        f"- matches_total: {batch_os['matches_total']}",
        f"- matches_succeeded: {batch_os['matches_succeeded']}",
        f"- portfolio status: {batch_os['portfolio_delta_status']}",
        f"- candidate count delta: {batch_os['candidate_count_delta']}",
        "",
        "## 6. What To Fix Before Real Multi-Match Use",
        "- missing recent form",
        "- missing big chances",
        "- missing availability",
        "- missing opening/closing market",
        "- missing DNB/OU market",
        "",
        "## 7. Artifact Links",
        "- match_pack_scan_dashboard.md",
        "- evidence_coverage_matrix.md",
        "- batch_health_gate_report.md",
        "- auto_batch_config.csv",
        "- executive_dashboard.md",
        "",
        "## 8. Safety Footer",
        "No production betting. No stake. No ROI. No automatic betting.",
        "",
    ])


def _copy(source: object, target: Path) -> None:
    src = Path(str(source))
    if src.exists() and src.resolve() != target.resolve():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() or p == path else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_csv(path: object) -> pd.DataFrame:
    try:
        return pd.read_csv(path, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _resolve(path: object, base: Path) -> Path:
    p = Path(str(path))
    return p.resolve() if p.is_absolute() else (base / p).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
