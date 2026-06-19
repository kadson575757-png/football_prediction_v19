# -*- coding: utf-8 -*-
"""Register a reviewed accepted trusted xG artifact in the manual xG manifest.

Phase 13.13 foundation only. This script validates and writes manifest metadata;
it never edits xG values, target match CSVs, model features, or market logic.
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

from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402
from football_prediction_v19.importers.manual_xg_manifest import REQUIRED_COLUMNS  # noqa: E402

ACCEPTED_XG_MANIFEST_ENTRY_READY = "ACCEPTED_XG_MANIFEST_ENTRY_READY"
ACCEPTED_XG_MANIFEST_ENTRY_WRITTEN = "ACCEPTED_XG_MANIFEST_ENTRY_WRITTEN"
ACCEPTED_XG_MANIFEST_ENTRY_ALREADY_REGISTERED = "ACCEPTED_XG_MANIFEST_ENTRY_ALREADY_REGISTERED"
ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH = "ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH"
ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_MISSING_METADATA = "ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_MISSING_METADATA"
ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_VALIDATION_FAILED = "ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_VALIDATION_FAILED"

DEFAULT_ENTRY = {
    "manifest_id": "trusted_xg_understat_bundesliga_2024_manual_xg",
    "xg_file_path": "data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
    "target_file_path": "data/processed/football_data_D1_2024_clean.csv",
    "league": "Bundesliga",
    "season": "2024",
    "source_type": "MANUAL_XG_CSV",
    "data_role": "PRODUCTION",
    "is_demo": "false",
    "expected_rows": 306,
    "min_join_coverage_pct": 100.0,
    "notes": "Accepted Understat Bundesliga 2024 xG artifact produced through Phase 13.10b-13.12 preview/acceptance workflow.",
}

OUTPUT_CSV = "accepted_xg_manifest_registration_summary.csv"
OUTPUT_MD = "accepted_xg_manifest_registration_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-entry-preview", default=None)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _repo_relative(path: str | Path, base_dir: Path) -> str:
    text = str(path).strip()
    if not text:
        raise ValueError("EMPTY_PATH")
    raw = Path(text)
    if raw.is_absolute():
        try:
            return raw.resolve().relative_to(base_dir.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("ABSOLUTE_PATH_OUTSIDE_REPO") from exc
    return raw.as_posix()


def _is_outputs_path(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").strip().lower()
    return normalized == "outputs" or normalized.startswith("outputs/")


def _entry_from_preview(preview_path: str | Path | None, base_dir: Path) -> dict[str, Any]:
    entry = dict(DEFAULT_ENTRY)
    if not preview_path:
        return entry
    table = pd.read_csv(preview_path, keep_default_na=False)
    if table.empty:
        return entry
    row = table.iloc[0].to_dict()
    for key in REQUIRED_COLUMNS:
        if key in row:
            entry[key] = row[key]
    # The reviewed Phase 13.13 registration intentionally uses the accepted
    # artifact id, even if older preview files used generated preview ids.
    if str(entry.get("manifest_id", "")).startswith("trusted_xg_understat_xg_bundesliga_2024"):
        entry["manifest_id"] = DEFAULT_ENTRY["manifest_id"]
    return entry


def _validate_entry_paths(entry: dict[str, Any], base_dir: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    normalized = dict(entry)
    try:
        xg_rel = _repo_relative(normalized["xg_file_path"], base_dir)
        target_rel = _repo_relative(normalized["target_file_path"], base_dir)
    except ValueError as exc:
        return normalized, [str(exc)]
    normalized["xg_file_path"] = xg_rel
    normalized["target_file_path"] = target_rel
    if _is_outputs_path(xg_rel) or _is_outputs_path(target_rel):
        errors.append("OUTPUTS_PATH_NOT_ALLOWED")
    if not xg_rel.startswith("data/trusted_xg_sources/accepted/"):
        errors.append("XG_PATH_MUST_BE_ACCEPTED_TRUSTED_SOURCE")
    if not (base_dir / xg_rel).exists():
        errors.append("ACCEPTED_ARTIFACT_NOT_FOUND")
    if not (base_dir / target_rel).exists():
        errors.append("TARGET_FILE_NOT_FOUND")
    if not str(normalized.get("league", "")).strip() or not str(normalized.get("season", "")).strip():
        errors.append("MISSING_LEAGUE_OR_SEASON")
    return normalized, errors


def _validate_acceptance(entry: dict[str, Any], base_dir: Path, output_dir: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    xg_path = base_dir / str(entry["xg_file_path"])
    target_path = base_dir / str(entry["target_file_path"])
    try:
        expected_rows = int(float(str(entry.get("expected_rows", "")).strip()))
    except ValueError:
        expected_rows = -1
    try:
        min_coverage = float(str(entry.get("min_join_coverage_pct", "")).strip())
    except ValueError:
        min_coverage = 100.0
    result = run_manual_xg_acceptance_gate(
        xg_path,
        target_path=target_path,
        output_dir=output_dir / "accepted_manifest_registration_acceptance_preview",
        min_join_coverage=min_coverage,
        write_preview=False,
    )
    if result.acceptance_label != "MANUAL_XG_ACCEPTED":
        errors.append("ACCEPTANCE_GATE_NOT_ACCEPTED")
    if result.rows_source != expected_rows:
        errors.append("EXPECTED_ROWS_MISMATCH")
    if result.join_coverage_pct < min_coverage:
        errors.append("JOIN_COVERAGE_BELOW_MINIMUM")
    diagnostics = {
        "acceptance_label": result.acceptance_label,
        "rows_source": result.rows_source,
        "rows_valid": result.rows_valid,
        "rows_join_matched": result.rows_join_matched,
        "join_coverage_pct": float(result.join_coverage_pct),
    }
    return diagnostics, errors


def _load_manifest(path: Path) -> pd.DataFrame:
    if path.exists():
        table = pd.read_csv(path, keep_default_na=False, dtype=str)
    else:
        table = pd.DataFrame(columns=REQUIRED_COLUMNS)
    for col in REQUIRED_COLUMNS:
        if col not in table.columns:
            table[col] = ""
    table = table[REQUIRED_COLUMNS].fillna("").astype(str).copy()
    if "is_demo" in table.columns:
        table["is_demo"] = table["is_demo"].map(_normalize_bool_text)
    return table


def _normalize_bool_text(value: Any) -> str:
    text = str(value).strip()
    if text.lower() in {"true", "1", "yes", "y"}:
        return "true"
    if text.lower() in {"false", "0", "no", "n"}:
        return "false"
    return text


def _manifest_value(value: Any, column: str) -> str:
    if column == "is_demo":
        return _normalize_bool_text(value)
    if pd.isna(value):
        return ""
    return str(value).strip()


def _entry_row(entry: dict[str, Any]) -> dict[str, str]:
    return {col: _manifest_value(entry.get(col, ""), col) for col in REQUIRED_COLUMNS}


def _entry_matches(existing: pd.Series, entry: dict[str, Any]) -> bool:
    for key in REQUIRED_COLUMNS:
        left = str(existing.get(key, "")).strip()
        right = _manifest_value(entry.get(key, ""), key)
        if key == "min_join_coverage_pct":
            try:
                if float(left) != float(right):
                    return False
                continue
            except ValueError:
                pass
        if key == "expected_rows":
            try:
                if int(float(left)) != int(float(right)):
                    return False
                continue
            except ValueError:
                pass
        if left != right:
            return False
    return True


def _write_diagnostics(summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(output_dir / OUTPUT_CSV, index=False)
    lines = [
        "# Phase 13.13 Accepted xG Manifest Registration",
        "",
        "Phase 13.13 is diagnostic/foundation only. No xG values were inferred or invented, and xG remains inactive in model logic.",
        "",
        "## A. Summary",
    ]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    lines.extend([
        "",
        "## B. Safety Checks",
        "- No raw trusted source CSV modified.",
        "- No target match CSV modified.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "- Production manifest is modified only when --write is provided.",
        "",
    ])
    (output_dir / OUTPUT_MD).write_text("\n".join(lines), encoding="utf-8")


def register_accepted_xg_manifest_entry(
    *,
    manifest_entry_preview: str | Path | None = None,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    write: bool = False,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    output_root = Path(output_dir)
    entry = _entry_from_preview(manifest_entry_preview, base)
    entry, path_errors = _validate_entry_paths(entry, base)
    if any(err == "MISSING_LEAGUE_OR_SEASON" for err in path_errors):
        status = ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_MISSING_METADATA
    elif path_errors:
        status = ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_INVALID_PATH
    else:
        acceptance, validation_errors = _validate_acceptance(entry, base, output_root)
        status = ACCEPTED_XG_MANIFEST_ENTRY_READY
        if validation_errors:
            status = ACCEPTED_XG_MANIFEST_ENTRY_BLOCKED_VALIDATION_FAILED
        path_errors.extend(validation_errors)
        entry.update(acceptance)

    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    manifest_changed = False
    if status == ACCEPTED_XG_MANIFEST_ENTRY_READY and write:
        table = _load_manifest(manifest_path)
        match = table["manifest_id"].astype(str).eq(str(entry["manifest_id"]))
        if match.any():
            idx = table.index[match][0]
            if _entry_matches(table.loc[idx], entry):
                status = ACCEPTED_XG_MANIFEST_ENTRY_ALREADY_REGISTERED
            else:
                entry_values = _entry_row(entry)
                for col in REQUIRED_COLUMNS:
                    table.loc[idx, col] = entry_values[col]
                manifest_changed = True
                status = ACCEPTED_XG_MANIFEST_ENTRY_WRITTEN
        else:
            new_row = pd.DataFrame([_entry_row(entry)], columns=REQUIRED_COLUMNS)
            table = new_row.copy() if table.empty else pd.concat([table, new_row], ignore_index=True)
            manifest_changed = True
            status = ACCEPTED_XG_MANIFEST_ENTRY_WRITTEN
        if manifest_changed:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            table = table[REQUIRED_COLUMNS].fillna("").astype(str)
            table["is_demo"] = table["is_demo"].map(_normalize_bool_text)
            table.to_csv(manifest_path, index=False)

    summary = {
        "registration_status": status,
        "manifest_path": str(manifest_path),
        "manifest_changed": manifest_changed,
        "manifest_id": entry.get("manifest_id", ""),
        "xg_file_path": entry.get("xg_file_path", ""),
        "target_file_path": entry.get("target_file_path", ""),
        "league": entry.get("league", ""),
        "season": entry.get("season", ""),
        "expected_rows": entry.get("expected_rows", ""),
        "min_join_coverage_pct": entry.get("min_join_coverage_pct", ""),
        "acceptance_label": entry.get("acceptance_label", ""),
        "rows_source": entry.get("rows_source", 0),
        "join_coverage_pct": entry.get("join_coverage_pct", 0.0),
        "blocking_reasons": " | ".join(path_errors),
    }
    _write_diagnostics(summary, output_root)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = register_accepted_xg_manifest_entry(
        manifest_entry_preview=args.manifest_entry_preview,
        manifest=args.manifest,
        write=args.write,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    print(f"registration_status={summary['registration_status']}")
    print(f"manifest_id={summary['manifest_id']}")
    print(f"xg_file_path={summary['xg_file_path']}")
    print(f"target_file_path={summary['target_file_path']}")
    print(f"join_coverage_pct={summary['join_coverage_pct']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
