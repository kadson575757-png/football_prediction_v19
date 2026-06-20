# -*- coding: utf-8 -*-
"""Build a reporting-only xG preview pack index.

The pack bundles match-level, team aggregate, rolling form, and matchup xG
reporting previews. It is diagnostic/reporting only and never modifies source,
target, accepted artifact, manifest, model, probability, market, betting,
staking, ROI, or SUPER_A_TIER logic.
"""
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

from build_rolling_xg_form_reporting import ROLLING_XG_FORM_REPORTING_READY, build_rolling_xg_form_reporting  # noqa: E402
from build_team_xg_reporting_aggregates import TEAM_XG_REPORTING_AGGREGATES_READY, build_team_xg_reporting_aggregates  # noqa: E402
from build_xg_matchup_reporting_preview import XG_MATCHUP_REPORTING_PREVIEW_READY, build_xg_matchup_reporting_preview  # noqa: E402
from build_xg_reporting_preview import XG_REPORTING_PREVIEW_READY, build_xg_reporting_preview  # noqa: E402
from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402

XG_REPORTING_PACK_PREVIEW_READY = "XG_REPORTING_PACK_PREVIEW_READY"
XG_REPORTING_PACK_PREVIEW_BLOCKED_REPORT_FAILED = "XG_REPORTING_PACK_PREVIEW_BLOCKED_REPORT_FAILED"
XG_REPORTING_PACK_PREVIEW_BLOCKED_UNSAFE_PATH = "XG_REPORTING_PACK_PREVIEW_BLOCKED_UNSAFE_PATH"
XG_REPORTING_PACK_PREVIEW_BLOCKED_INVALID_MANIFEST = "XG_REPORTING_PACK_PREVIEW_BLOCKED_INVALID_MANIFEST"

OUTPUT_DIR = ROOT / "outputs" / "xg_reporting_preview"
INDEX_NAME = "xg_reporting_pack_index.csv"
SUMMARY_NAME = "xg_reporting_pack_summary.md"

EXPECTED_REPORTS = [
    "match_level_reporting_preview",
    "team_xg_reporting_aggregates",
    "rolling_xg_form_reporting",
    "xg_matchup_reporting_preview",
]


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
    allowed = (base_dir / "outputs" / "xg_reporting_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("PACK_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_REPORTING_PREVIEW")
    return resolved


def _manifest_entry(manifest: Path, manifest_id: str | None) -> Any | None:
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


def _row(manifest_id: str, report_type: str, status: str, rows: int, output_path: str, recommendation: str) -> dict[str, Any]:
    return {
        "manifest_id": manifest_id,
        "report_type": report_type,
        "status": status,
        "rows": int(rows),
        "output_path": output_path,
        "recommendation": recommendation,
    }


def _pack_markdown(index: pd.DataFrame, *, entry: Any | None, pack_status: str, window: int) -> str:
    manifest_id = str(index["manifest_id"].iloc[0]) if not index.empty else getattr(entry, "manifest_id", "")
    lookup = {row["report_type"]: row for _, row in index.iterrows()}
    lines = [
        "# Phase 13.20 xG Reporting Pack Preview",
        "",
        "Phase 13.20 is reporting/diagnostic preview only. xG is not active in model logic.",
        "",
        "## A. Executive Summary",
        f"- manifest_id: {manifest_id}",
        f"- league: {getattr(entry, 'league', '') if entry else ''}",
        f"- season: {getattr(entry, 'season', '') if entry else ''}",
        f"- window: {window}",
        f"- reporting_pack_status: {pack_status}",
        "",
        "## B. Report Status",
        f"- match-level preview status: {lookup.get('match_level_reporting_preview', {}).get('status', '')}",
        f"- team aggregate status: {lookup.get('team_xg_reporting_aggregates', {}).get('status', '')}",
        f"- rolling form status: {lookup.get('rolling_xg_form_reporting', {}).get('status', '')}",
        f"- matchup preview status: {lookup.get('xg_matchup_reporting_preview', {}).get('status', '')}",
        "",
        "## C. Row Counts",
    ]
    if index.empty:
        lines += ["No reporting pack rows were built.", ""]
    else:
        lines += ["| report_type | rows | status |", "| --- | --- | --- |"]
        for _, row in index.iterrows():
            lines.append(f"| {row['report_type']} | {row['rows']} | {row['status']} |")
        lines.append("")
    lines += [
        "## D. Safety Statement",
        "- No xG values inferred or invented.",
        "- No target CSV modified in place.",
        "- No accepted xG artifact modified.",
        "- No raw Understat source CSV modified.",
        "- No production manifest modified.",
        "- xG is not active as model features.",
        "- No model predictions, probabilities, market tiers, recommended markets, betting, staking, ROI, stake sizing, or SUPER_A_TIER logic changed.",
        "",
    ]
    return "\n".join(lines)


def _blocked(status: str, reason: str, *, manifest_id: str = "") -> dict[str, Any]:
    return {
        "reporting_pack_status": status,
        "manifest_id": manifest_id,
        "reports_built": 0,
        "reports_ready": 0,
        "reporting_pack_index_path": "",
        "reporting_pack_summary_path": "",
        "blocking_reasons": reason,
    }


def build_xg_reporting_pack_preview(
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
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(XG_REPORTING_PACK_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc), manifest_id=manifest_id or "")
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        entry = _manifest_entry(manifest_path, manifest_id)
    except Exception as exc:
        return _blocked(XG_REPORTING_PACK_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc), manifest_id=manifest_id or "")
    if entry is None:
        return _blocked(XG_REPORTING_PACK_PREVIEW_BLOCKED_INVALID_MANIFEST, "NO_ACCEPTED_PRODUCTION_MANIFEST_ENTRY", manifest_id=manifest_id or "")
    manifest_id_value = entry.manifest_id

    reporting = build_xg_reporting_preview(manifest=manifest_path, manifest_id=manifest_id_value, output_dir=out_dir, write_preview=True, base_dir=base)
    reporting_path = str(reporting.get("reporting_output_path", ""))
    rows = [
        _row(
            manifest_id_value,
            "match_level_reporting_preview",
            str(reporting["reporting_status"]),
            int(reporting.get("rows_reported", 0)),
            reporting_path,
            XG_REPORTING_PREVIEW_READY if reporting["reporting_status"] == XG_REPORTING_PREVIEW_READY else str(reporting["reporting_status"]),
        )
    ]
    if reporting["reporting_status"] == XG_REPORTING_PREVIEW_READY and reporting_path:
        aggregate = build_team_xg_reporting_aggregates(reporting_preview=reporting_path, manifest=manifest_path, manifest_id=manifest_id_value, output_dir=out_dir, write_preview=True, base_dir=base)
        rolling = build_rolling_xg_form_reporting(reporting_preview=reporting_path, manifest=manifest_path, manifest_id=manifest_id_value, window=window, output_dir=out_dir, write_preview=True, base_dir=base)
        matchup = build_xg_matchup_reporting_preview(reporting_preview=reporting_path, rolling_form_preview=rolling.get("form_output_path") or None, manifest=manifest_path, manifest_id=manifest_id_value, window=window, output_dir=out_dir, write_preview=True, base_dir=base)
    else:
        aggregate = {"aggregate_status": "SKIPPED_REPORTING_FAILED", "teams_reported": 0, "aggregate_output_path": ""}
        rolling = {"form_status": "SKIPPED_REPORTING_FAILED", "team_match_rows": 0, "form_output_path": ""}
        matchup = {"matchup_status": "SKIPPED_REPORTING_FAILED", "matches_reported": 0, "matchup_output_path": ""}
    rows += [
        _row(manifest_id_value, "team_xg_reporting_aggregates", str(aggregate["aggregate_status"]), int(aggregate.get("teams_reported", 0)), str(aggregate.get("aggregate_output_path", "")), TEAM_XG_REPORTING_AGGREGATES_READY if aggregate["aggregate_status"] == TEAM_XG_REPORTING_AGGREGATES_READY else str(aggregate["aggregate_status"])),
        _row(manifest_id_value, "rolling_xg_form_reporting", str(rolling["form_status"]), int(rolling.get("team_match_rows", 0)), str(rolling.get("form_output_path", "")), ROLLING_XG_FORM_REPORTING_READY if rolling["form_status"] == ROLLING_XG_FORM_REPORTING_READY else str(rolling["form_status"])),
        _row(manifest_id_value, "xg_matchup_reporting_preview", str(matchup["matchup_status"]), int(matchup.get("matches_reported", 0)), str(matchup.get("matchup_output_path", "")), XG_MATCHUP_REPORTING_PREVIEW_READY if matchup["matchup_status"] == XG_MATCHUP_REPORTING_PREVIEW_READY else str(matchup["matchup_status"])),
    ]
    index = pd.DataFrame(rows)
    ready_statuses = {
        "match_level_reporting_preview": XG_REPORTING_PREVIEW_READY,
        "team_xg_reporting_aggregates": TEAM_XG_REPORTING_AGGREGATES_READY,
        "rolling_xg_form_reporting": ROLLING_XG_FORM_REPORTING_READY,
        "xg_matchup_reporting_preview": XG_MATCHUP_REPORTING_PREVIEW_READY,
    }
    reports_ready = int(sum(row["status"] == ready_statuses[row["report_type"]] for row in rows))
    pack_status = XG_REPORTING_PACK_PREVIEW_READY if reports_ready == len(EXPECTED_REPORTS) else XG_REPORTING_PACK_PREVIEW_BLOCKED_REPORT_FAILED
    index_path = ""
    summary_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        index_file = (out_dir / INDEX_NAME).resolve()
        summary_file = (out_dir / SUMMARY_NAME).resolve()
        if out_dir not in index_file.parents or out_dir not in summary_file.parents:
            return _blocked(XG_REPORTING_PACK_PREVIEW_BLOCKED_UNSAFE_PATH, "PACK_OUTPUT_OUTSIDE_OUTPUT_DIR", manifest_id=manifest_id_value)
        index.to_csv(index_file, index=False)
        summary_file.write_text(_pack_markdown(index, entry=entry, pack_status=pack_status, window=window), encoding="utf-8")
        index_path = str(index_file)
        summary_path = str(summary_file)
    return {
        "reporting_pack_status": pack_status,
        "manifest_id": manifest_id_value,
        "reports_built": int(len(index)),
        "reports_ready": reports_ready,
        "reporting_pack_index_path": index_path,
        "reporting_pack_summary_path": summary_path,
        "blocking_reasons": "" if pack_status == XG_REPORTING_PACK_PREVIEW_READY else "ONE_OR_MORE_REPORTS_NOT_READY",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_xg_reporting_pack_preview(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in [
        "reporting_pack_status",
        "manifest_id",
        "reports_built",
        "reports_ready",
        "reporting_pack_index_path",
        "reporting_pack_summary_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
