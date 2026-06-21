# -*- coding: utf-8 -*-
"""Audit controlled FBref provider pull preview."""
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

from build_fbref_provider_pull_preview import build_fbref_provider_pull_preview  # noqa: E402
from football_prediction_v19.importers.fbref_provider_pull_preview import (  # noqa: E402
    FBREF_PROVIDER_PULL_PREVIEW_READY,
    MANIFEST_COLUMNS,
    NORMALIZED_COLUMNS,
)

BUILD_FBREF_PROVIDER_PULL_PREVIEW = "BUILD_FBREF_PROVIDER_PULL_PREVIEW"
FIX_FBREF_PROVIDER_PULL_PREVIEW = "FIX_FBREF_PROVIDER_PULL_PREVIEW"
OUTPUT_CSV = "fbref_provider_pull_preview_summary.csv"
OUTPUT_MD = "fbref_provider_pull_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "fbref"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"} if not isinstance(value, bool) else value


def _under(path_text: str, base: Path, rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _protected(path_text: str) -> bool:
    text = str(path_text).replace("\\", "/").lower()
    return any(token in text for token in PROTECTED)


def _manifest_path(manifest: str | Path | None, preview_dir: str | Path) -> Path | None:
    if manifest:
        return Path(manifest)
    path = Path(preview_dir) / "fbref_provider_pull_manifest.csv"
    return path if path.exists() else None


def audit_manifest(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return _row(path, [str(exc)])
    missing = sorted(set(MANIFEST_COLUMNS) - set(table.columns))
    if missing:
        errors.append("MISSING_REQUIRED_COLUMNS")
    provider_ok = bool((table.get("provider", pd.Series(dtype=str)).astype(str) == "fbref").all()) if "provider" in table.columns else False
    status_ok = set(table.get("fbref_provider_pull_status", pd.Series(dtype=str)).astype(str)).issubset({FBREF_PROVIDER_PULL_PREVIEW_READY}) if "fbref_provider_pull_status" in table.columns else False
    rows_ok = bool((pd.to_numeric(table.get("rows_normalized", pd.Series(dtype=int)), errors="coerce").fillna(0) > 0).all()) if "rows_normalized" in table.columns else False
    network_enabled = any(_as_bool(v) for v in table.get("network_calls_enabled", pd.Series(dtype=bool)))
    normalized_paths = table.get("normalized_output_path", pd.Series(dtype=str)).fillna("").astype(str)
    raw_paths = table.get("raw_output_path", pd.Series(dtype=str)).fillna("").astype(str)
    normalized_safe = all(_under(p, base, "outputs/provider_pull_preview/fbref/normalized") and not _protected(p) for p in normalized_paths)
    raw_safe = all(_under(p, base, "outputs/provider_pull_preview/fbref/raw") and not _protected(p) for p in raw_paths if str(p).strip())
    normalized_columns_ok = False
    if normalized_paths.any():
        normalized_file = Path(normalized_paths.iloc[0])
        if normalized_file.exists():
            normalized_columns_ok = set(NORMALIZED_COLUMNS).issubset(set(pd.read_csv(normalized_file, nrows=0).columns))
    for ok, label in [
        (provider_ok, "PROVIDER_NOT_FBREF"),
        (status_ok, "STATUS_NOT_READY"),
        (rows_ok, "NO_NORMALIZED_ROWS"),
        (not network_enabled, "NETWORK_ENABLED_IN_OFFLINE_AUDIT"),
        (normalized_safe, "UNSAFE_NORMALIZED_PATH"),
        (raw_safe, "UNSAFE_RAW_PATH"),
        (normalized_columns_ok, "NORMALIZED_COLUMNS_MISSING"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "manifest_path": str(path),
        "manifests_found": 1,
        "missing_required_columns": " | ".join(missing),
        "provider_ok": provider_ok,
        "status_ok": status_ok,
        "rows_normalized_ok": rows_ok,
        "network_calls_enabled": network_enabled,
        "normalized_path_safe": normalized_safe,
        "raw_path_safe": raw_safe,
        "normalized_columns_ok": normalized_columns_ok,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def _row(path: Path, errors: list[str]) -> dict[str, Any]:
    return {"manifest_path": str(path), "manifests_found": 0, "missing_required_columns": "ALL", "provider_ok": False, "status_ok": False, "rows_normalized_ok": False, "network_calls_enabled": True, "normalized_path_safe": False, "raw_path_safe": False, "normalized_columns_ok": False, "preview_valid": False, "blocking_reasons": " | ".join(errors)}


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_FBREF_PROVIDER_PULL_PREVIEW
    if table["preview_valid"].any():
        return FBREF_PROVIDER_PULL_PREVIEW_READY
    return FIX_FBREF_PROVIDER_PULL_PREVIEW


def run(*, manifest: str | Path | None = None, preview_dir: str | Path = ROOT / "outputs" / "provider_pull_preview" / "fbref", output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    path = _manifest_path(manifest, preview_dir)
    if path is None:
        summary = build_fbref_provider_pull_preview(base_dir=base_dir, output_dir=preview_dir)
        path = Path(str(summary.get("manifest_path", "")))
    rows = [audit_manifest(path, base_dir=base_dir)] if path and path.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 19.1 FBref Provider Pull Preview Audit",
        "",
        f"- manifests audited: {len(table)}",
        f"- valid manifests: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- network_calls_enabled=false in default audit mode",
        "- no model/prediction/market/betting/staking logic is invoked",
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
    table, _markdown, rec = run(manifest=args.manifest, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
