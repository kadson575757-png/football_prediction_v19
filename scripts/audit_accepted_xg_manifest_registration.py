# -*- coding: utf-8 -*-
"""Audit whether the accepted Bundesliga 2024 trusted xG artifact is registered."""
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

from register_accepted_xg_manifest_entry import (  # noqa: E402
    DEFAULT_ENTRY,
    OUTPUT_CSV,
    OUTPUT_MD,
    _is_outputs_path,
    _repo_relative,
    _validate_acceptance,
)

ACCEPTED_XG_MANIFEST_REGISTERED = "ACCEPTED_XG_MANIFEST_REGISTERED"
REGISTER_ACCEPTED_XG_MANIFEST_ENTRY = "REGISTER_ACCEPTED_XG_MANIFEST_ENTRY"
FIX_ACCEPTED_XG_MANIFEST_ENTRY = "FIX_ACCEPTED_XG_MANIFEST_ENTRY"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _load_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def audit_accepted_xg_manifest_registration(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    table = _load_manifest(manifest_path)
    rows: list[dict[str, Any]] = []
    if table.empty or "manifest_id" not in table.columns:
        rows.append({
            **DEFAULT_ENTRY,
            "entry_present": False,
            "entry_valid": False,
            "acceptance_label": "",
            "rows_source": 0,
            "join_coverage_pct": 0.0,
            "blocking_reasons": "MANIFEST_MISSING_OR_INVALID",
        })
    else:
        matches = table[table["manifest_id"].astype(str) == DEFAULT_ENTRY["manifest_id"]]
        if matches.empty:
            rows.append({
                **DEFAULT_ENTRY,
                "entry_present": False,
                "entry_valid": False,
                "acceptance_label": "",
                "rows_source": 0,
                "join_coverage_pct": 0.0,
                "blocking_reasons": "ACCEPTED_ENTRY_NOT_REGISTERED",
            })
        else:
            row = matches.iloc[0].to_dict()
            errors: list[str] = []
            try:
                xg_rel = _repo_relative(row.get("xg_file_path", ""), base)
                target_rel = _repo_relative(row.get("target_file_path", ""), base)
            except ValueError as exc:
                xg_rel = str(row.get("xg_file_path", ""))
                target_rel = str(row.get("target_file_path", ""))
                errors.append(str(exc))
            if _is_outputs_path(xg_rel) or _is_outputs_path(target_rel):
                errors.append("OUTPUTS_PATH_NOT_ALLOWED")
            if xg_rel != DEFAULT_ENTRY["xg_file_path"]:
                errors.append("UNEXPECTED_XG_FILE_PATH")
            if target_rel != DEFAULT_ENTRY["target_file_path"]:
                errors.append("UNEXPECTED_TARGET_FILE_PATH")
            if str(row.get("league", "")).strip() != DEFAULT_ENTRY["league"]:
                errors.append("UNEXPECTED_LEAGUE")
            if str(row.get("season", "")).strip() != DEFAULT_ENTRY["season"]:
                errors.append("UNEXPECTED_SEASON")
            if not (base / xg_rel).exists():
                errors.append("ACCEPTED_ARTIFACT_NOT_FOUND")
            if not (base / target_rel).exists():
                errors.append("TARGET_FILE_NOT_FOUND")
            acceptance = {
                "acceptance_label": "",
                "rows_source": 0,
                "rows_valid": 0,
                "rows_join_matched": 0,
                "join_coverage_pct": 0.0,
            }
            if not errors:
                acceptance, validation_errors = _validate_acceptance(row, base, Path(output_dir))
                errors.extend(validation_errors)
            rows.append({
                **row,
                "xg_file_path": xg_rel,
                "target_file_path": target_rel,
                "entry_present": True,
                "entry_valid": not errors,
                **acceptance,
                "blocking_reasons": " | ".join(errors),
            })
    result = pd.DataFrame(rows)
    if result["entry_valid"].any():
        rec = ACCEPTED_XG_MANIFEST_REGISTERED
    elif result["entry_present"].any():
        rec = FIX_ACCEPTED_XG_MANIFEST_ENTRY
    else:
        rec = REGISTER_ACCEPTED_XG_MANIFEST_ENTRY
    markdown = build_markdown(result, rec, manifest_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_root / OUTPUT_CSV, index=False)
    (output_root / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return result, markdown, rec


def build_markdown(table: pd.DataFrame, rec: str, manifest_path: Path) -> str:
    row = table.iloc[0] if not table.empty else {}
    lines = [
        "# Phase 13.13 Accepted xG Manifest Registration Audit",
        "",
        "Phase 13.13 is diagnostic/foundation only. xG is registered as accepted data only and remains inactive in model logic.",
        "",
        "## A. Executive Summary",
        f"- manifest path: {manifest_path}",
        f"- accepted entry present: {row.get('entry_present', False)}",
        f"- accepted entry valid: {row.get('entry_valid', False)}",
        f"- manifest_id: {row.get('manifest_id', '')}",
        f"- xg_file_path: {row.get('xg_file_path', '')}",
        f"- target_file_path: {row.get('target_file_path', '')}",
        f"- expected_rows: {row.get('expected_rows', '')}",
        f"- rows_source: {row.get('rows_source', 0)}",
        f"- join_coverage_pct: {row.get('join_coverage_pct', 0.0)}",
        f"- blocking_reasons: {row.get('blocking_reasons', '')}",
        "",
        "## B. Safety Checks",
        "- No xG values inferred or invented.",
        "- No raw Understat source CSV modified.",
        "- No target match CSV modified.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "- xG remains inactive until a future explicit integration phase.",
        "",
        "## C. Phase 13.13 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = audit_accepted_xg_manifest_registration(
        manifest=args.manifest,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
