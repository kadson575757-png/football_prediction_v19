# -*- coding: utf-8 -*-
"""Build a human-analysis export bundle from ready xG reporting previews."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_xg_reporting_pack_preview import XG_REPORTING_PACK_PREVIEW_READY, build_xg_reporting_pack_preview  # noqa: E402
from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402

ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY = "ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_REPORT_FAILED = "ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_REPORT_FAILED"
ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_UNSAFE_PATH = "ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_UNSAFE_PATH"
ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_INVALID_MANIFEST = "ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_INVALID_MANIFEST"

OUTPUT_DIR = ROOT / "outputs" / "analysis_export_preview"
INDEX_NAME = "analysis_export_bundle_index.csv"
SUMMARY_NAME = "analysis_export_bundle_summary.md"

EXPORTS = {
    "match_level_reporting_preview": "match_level_xg_reporting_preview.csv",
    "team_xg_reporting_aggregates": "team_xg_reporting_aggregates.csv",
    "rolling_xg_form_reporting": "rolling_xg_form_reporting.csv",
    "xg_matchup_reporting_preview": "xg_matchup_reporting_preview.csv",
    "reporting_pack_index": "xg_reporting_pack_index.csv",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_export_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("ANALYSIS_EXPORT_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_EXPORT_PREVIEW")
    return resolved


def _entry(manifest: Path, manifest_id: str | None) -> Any | None:
    entries = [
        entry for entry in load_manual_xg_manifest(manifest)
        if entry.data_role == "PRODUCTION"
        and entry.source_type == "MANUAL_XG_CSV"
        and not entry.is_demo
        and str(entry.xg_file_path).strip()
        and str(entry.target_file_path).strip()
    ]
    if manifest_id:
        entries = [entry for entry in entries if entry.manifest_id == manifest_id]
    return entries[0] if entries else None


def _blocked(status: str, reason: str, *, manifest_id: str = "") -> dict[str, Any]:
    return {
        "export_bundle_status": status,
        "manifest_id": manifest_id,
        "reports_exported": 0,
        "reports_ready": 0,
        "export_bundle_dir": "",
        "export_bundle_index_path": "",
        "export_bundle_summary_path": "",
        "recommendation": status,
        "blocking_reasons": reason,
    }


def _copy_csv(source: Path, dest: Path) -> int:
    df = pd.read_csv(source, low_memory=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)
    return int(len(df))


def _summary_markdown(index: pd.DataFrame, *, entry: Any, bundle_status: str) -> str:
    lines = [
        "# Phase 14.1 Analysis Export Bundle Preview",
        "",
        "Phase 14.1 is a human-analysis export preview only. xG remains inactive in model logic.",
        "",
        "## A. Executive Summary",
        f"- manifest_id: {entry.manifest_id}",
        f"- league: {entry.league}",
        f"- season: {entry.season}",
        f"- export_bundle_status: {bundle_status}",
        "",
        "## B. Exported Reports",
        "| export_name | source_report_type | rows | source_status | export_status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in index.iterrows():
        lines.append(f"| {row['export_name']} | {row['source_report_type']} | {row['rows']} | {row['source_status']} | {row['export_status']} |")
    lines += [
        "",
        "## C. Human-analysis Usage Note",
        "This bundle collects normalized reporting previews for manual review, spreadsheet work, and future dashboard/Excel workflows.",
        "",
        "## D. Safety Note",
        "- No xG values inferred or invented.",
        "- No source, target, accepted artifact, raw trusted source, or production manifest modified.",
        "- xG remains inactive in model features, predictions, probabilities, market ranking, staking, ROI, stake sizing, and SUPER_A_TIER logic.",
        "",
    ]
    return "\n".join(lines)


def build_analysis_export_bundle_preview(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    window: int = 5,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_root = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc), manifest_id=manifest_id or "")
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        entry = _entry(manifest_path, manifest_id)
    except Exception as exc:
        return _blocked(ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc), manifest_id=manifest_id or "")
    if entry is None:
        return _blocked(ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_INVALID_MANIFEST, "NO_ACCEPTED_PRODUCTION_MANIFEST_ENTRY", manifest_id=manifest_id or "")

    pack = build_xg_reporting_pack_preview(
        manifest=manifest_path,
        manifest_id=entry.manifest_id,
        window=window,
        output_dir=base / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=base,
    )
    if pack["reporting_pack_status"] != XG_REPORTING_PACK_PREVIEW_READY or not pack["reporting_pack_index_path"]:
        return _blocked(ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_REPORT_FAILED, str(pack.get("blocking_reasons", "")), manifest_id=entry.manifest_id)

    pack_index = pd.read_csv(pack["reporting_pack_index_path"], low_memory=False)
    rows: list[dict[str, Any]] = []
    ready = 0
    bundle_dir = (out_root / entry.manifest_id).resolve()
    if out_root not in bundle_dir.parents:
        return _blocked(ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_UNSAFE_PATH, "BUNDLE_DIR_OUTSIDE_OUTPUT_DIR", manifest_id=entry.manifest_id)

    for report_type, export_name in EXPORTS.items():
        if report_type == "reporting_pack_index":
            source = Path(pack["reporting_pack_index_path"])
            source_status = pack["reporting_pack_status"]
            rows_count = int(len(pack_index))
        else:
            match = pack_index[pack_index["report_type"].astype(str).eq(report_type)]
            if match.empty:
                source = Path("")
                source_status = "MISSING_REPORT"
                rows_count = 0
            else:
                source = Path(str(match.iloc[0]["output_path"]))
                source_status = str(match.iloc[0]["status"])
                rows_count = int(match.iloc[0]["rows"])
        dest = bundle_dir / export_name
        export_status = "EXPORT_READY" if source_status.endswith("_READY") and source.exists() else "EXPORT_BLOCKED"
        output_path = ""
        if write_preview and export_status == "EXPORT_READY":
            rows_count = _copy_csv(source, dest)
            output_path = str(dest)
        elif not write_preview:
            output_path = str(dest)
        if export_status == "EXPORT_READY":
            ready += 1
        rows.append({
            "manifest_id": entry.manifest_id,
            "export_name": export_name,
            "source_report_type": report_type,
            "source_status": source_status,
            "rows": rows_count,
            "output_path": output_path,
            "export_status": export_status,
            "recommendation": "ANALYSIS_EXPORT_READY" if export_status == "EXPORT_READY" else "FIX_ANALYSIS_EXPORT",
        })

    closure = base / "outputs" / "diagnostics" / "xg_reporting_layer_closure_summary.csv"
    if closure.exists():
        dest = bundle_dir / "xg_reporting_layer_closure_summary.csv"
        rows_count = int(len(pd.read_csv(closure, low_memory=False)))
        if write_preview:
            shutil.copyfile(closure, dest)
        rows.append({
            "manifest_id": entry.manifest_id,
            "export_name": "xg_reporting_layer_closure_summary.csv",
            "source_report_type": "xg_reporting_layer_closure_summary",
            "source_status": "XG_REPORTING_LAYER_COMPLETE",
            "rows": rows_count,
            "output_path": str(dest),
            "export_status": "EXPORT_READY",
            "recommendation": "ANALYSIS_EXPORT_READY",
        })

    index = pd.DataFrame(rows)
    required_ready = sum(1 for row in rows if row["source_report_type"] in EXPORTS)
    bundle_status = ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY if ready == len(EXPORTS) else ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_REPORT_FAILED
    index_path = ""
    summary_path = ""
    if write_preview:
        bundle_dir.mkdir(parents=True, exist_ok=True)
        index_file = bundle_dir / INDEX_NAME
        summary_file = bundle_dir / SUMMARY_NAME
        index.to_csv(index_file, index=False)
        summary_file.write_text(_summary_markdown(index, entry=entry, bundle_status=bundle_status), encoding="utf-8")
        index_path = str(index_file)
        summary_path = str(summary_file)
    return {
        "export_bundle_status": bundle_status,
        "manifest_id": entry.manifest_id,
        "reports_exported": int(len(EXPORTS)),
        "reports_ready": int(ready),
        "export_bundle_dir": str(bundle_dir) if write_preview else "",
        "export_bundle_index_path": index_path,
        "export_bundle_summary_path": summary_path,
        "recommendation": ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY if bundle_status == ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY else ANALYSIS_EXPORT_BUNDLE_PREVIEW_BLOCKED_REPORT_FAILED,
        "blocking_reasons": "" if bundle_status == ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY else "ONE_OR_MORE_EXPORTS_NOT_READY",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_analysis_export_bundle_preview(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in [
        "export_bundle_status",
        "manifest_id",
        "reports_exported",
        "reports_ready",
        "export_bundle_dir",
        "export_bundle_index_path",
        "export_bundle_summary_path",
        "recommendation",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
