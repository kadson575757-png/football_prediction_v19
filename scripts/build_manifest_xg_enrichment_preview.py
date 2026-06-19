# -*- coding: utf-8 -*-
"""Build a manifest-backed xG enrichment preview.

Diagnostic/foundation only. The preview is written only under outputs/ and is
not used by model features, predictions, probabilities, or market logic.
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

from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402
from football_prediction_v19.xg_join_preview import build_match_key, normalize_join_key_columns  # noqa: E402

MANIFEST_XG_ENRICHMENT_PREVIEW_READY = "MANIFEST_XG_ENRICHMENT_PREVIEW_READY"
MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT = "MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT"
MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE = "MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE"
MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST = "MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST"
MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH = "MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "xg_enrichment_preview"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
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


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "xg_enrichment_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("PREVIEW_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_XG_ENRICHMENT_PREVIEW")
    return resolved


def _accepted_entries(manifest: str | Path, base_dir: Path) -> list[Any]:
    entries = load_manual_xg_manifest(manifest)
    return [
        entry for entry in entries
        if entry.data_role == "PRODUCTION"
        and entry.source_type == "MANUAL_XG_CSV"
        and not entry.is_demo
        and str(entry.xg_file_path).strip()
        and str(entry.target_file_path).strip()
    ]


def _select_entry(entries: list[Any], manifest_id: str | None, target: str | Path | None, base_dir: Path) -> Any | None:
    selected = entries
    if manifest_id:
        selected = [entry for entry in selected if entry.manifest_id == manifest_id]
    if target:
        target_rel = _repo_relative(target, base_dir)
        selected = [entry for entry in selected if _repo_relative(entry.target_file_path, base_dir) == target_rel]
    return selected[0] if selected else None


def _validate_entry(entry: Any, base_dir: Path) -> tuple[str | None, dict[str, Any]]:
    if Path(str(entry.xg_file_path)).is_absolute() or Path(str(entry.target_file_path)).is_absolute():
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, {"blocking_reasons": "MANIFEST_PATH_MUST_BE_REPO_RELATIVE"}
    try:
        xg_rel = _repo_relative(entry.xg_file_path, base_dir)
        target_rel = _repo_relative(entry.target_file_path, base_dir)
    except ValueError as exc:
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, {"blocking_reasons": str(exc)}
    if _is_outputs_path(xg_rel) or _is_outputs_path(target_rel):
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, {"blocking_reasons": "OUTPUTS_PATH_NOT_ALLOWED"}
    if not xg_rel.startswith("data/trusted_xg_sources/accepted/"):
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, {"blocking_reasons": "XG_PATH_NOT_ACCEPTED_ARTIFACT"}
    xg_path = base_dir / xg_rel
    target_path = base_dir / target_rel
    if not xg_path.exists():
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT, {"blocking_reasons": "ACCEPTED_ARTIFACT_NOT_FOUND"}
    if not target_path.exists():
        return MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST, {"blocking_reasons": "TARGET_FILE_NOT_FOUND"}
    return None, {"xg_file_path": xg_rel, "target_file_path": target_rel, "xg_abs_path": xg_path, "target_abs_path": target_path}


def _enrich_target(xg_df: pd.DataFrame, target_df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    xg_norm = normalize_join_key_columns(xg_df).copy()
    target_norm = normalize_join_key_columns(target_df).copy()
    required_xg = {"date", "home_team", "away_team", "home_xg", "away_xg"}
    required_target = {"date", "home_team", "away_team"}
    if not required_xg.issubset(xg_norm.columns) or not required_target.issubset(target_norm.columns):
        raise ValueError("MISSING_REQUIRED_JOIN_OR_XG_COLUMNS")
    xg_norm["match_key"] = build_match_key(xg_norm)
    target_keys = build_match_key(target_norm)
    xg_lookup = xg_norm[["match_key", "home_xg", "away_xg"]].copy()
    if xg_lookup["match_key"].duplicated().any():
        raise ValueError("DUPLICATE_XG_MATCH_KEYS")
    enriched = target_df.copy()
    # The target may already contain empty xG placeholder columns. The preview
    # replaces them in-memory with accepted artifact values and never writes
    # back to the target CSV.
    enriched = enriched.drop(columns=[col for col in ("home_xg", "away_xg") if col in enriched.columns])
    enriched["_manifest_xg_match_key"] = target_keys
    merged = enriched.merge(xg_lookup, left_on="_manifest_xg_match_key", right_on="match_key", how="left")
    merged = merged.drop(columns=["_manifest_xg_match_key", "match_key"])
    missing = int(merged[["home_xg", "away_xg"]].isna().any(axis=1).sum())
    rows_enriched = int(len(merged) - missing)
    return merged, rows_enriched, missing


def _preview_path(entry: Any, target_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{entry.manifest_id}__to__{target_path.stem}_manifest_xg_enrichment_preview.csv"


def build_manifest_xg_enrichment_preview(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    target: str | Path | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        entry = _select_entry(_accepted_entries(manifest_path, base), manifest_id, target, base)
    except Exception as exc:
        return _blocked(MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc))
    if entry is None:
        return _blocked(MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST, "NO_ACCEPTED_PRODUCTION_MANIFEST_ENTRY")
    status, details = _validate_entry(entry, base)
    if status:
        return _blocked(status, details.get("blocking_reasons", ""), entry)
    try:
        xg_df = pd.read_csv(details["xg_abs_path"], low_memory=False)
        target_df = pd.read_csv(details["target_abs_path"], low_memory=False)
        enriched, rows_enriched, rows_missing = _enrich_target(xg_df, target_df)
    except Exception as exc:
        return _blocked(MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc), entry)
    rows_target = int(len(target_df))
    coverage = round((rows_enriched / rows_target * 100.0), 2) if rows_target else 0.0
    min_coverage = float(entry.min_join_coverage_pct)
    status = MANIFEST_XG_ENRICHMENT_PREVIEW_READY
    if coverage < min_coverage:
        status = MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE
    preview_output_path = ""
    if write_preview and status == MANIFEST_XG_ENRICHMENT_PREVIEW_READY:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = _preview_path(entry, details["target_abs_path"], out_dir).resolve()
        if out_dir not in path.parents:
            return _blocked(MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH, "PREVIEW_OUTPUT_OUTSIDE_OUTPUT_DIR", entry)
        enriched.to_csv(path, index=False)
        preview_output_path = str(path)
    return {
        "enrichment_status": status,
        "manifest_id": entry.manifest_id,
        "xg_file_path": details["xg_file_path"],
        "target_file_path": details["target_file_path"],
        "rows_target": rows_target,
        "rows_enriched": rows_enriched,
        "rows_missing_xg": rows_missing,
        "join_coverage_pct": coverage,
        "preview_output_path": preview_output_path,
        "blocking_reasons": "" if status == MANIFEST_XG_ENRICHMENT_PREVIEW_READY else "LOW_JOIN_COVERAGE",
    }


def _blocked(status: str, reason: str, entry: Any | None = None) -> dict[str, Any]:
    return {
        "enrichment_status": status,
        "manifest_id": getattr(entry, "manifest_id", ""),
        "xg_file_path": getattr(entry, "xg_file_path", ""),
        "target_file_path": getattr(entry, "target_file_path", ""),
        "rows_target": 0,
        "rows_enriched": 0,
        "rows_missing_xg": 0,
        "join_coverage_pct": 0.0,
        "preview_output_path": "",
        "blocking_reasons": reason,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_manifest_xg_enrichment_preview(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        target=args.target,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in [
        "enrichment_status",
        "manifest_id",
        "rows_target",
        "rows_enriched",
        "rows_missing_xg",
        "join_coverage_pct",
        "preview_output_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
