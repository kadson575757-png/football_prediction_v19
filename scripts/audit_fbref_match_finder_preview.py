# -*- coding: utf-8 -*-
"""Audit deterministic FBref match finder preview."""
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

from find_fbref_match_preview import find_fbref_match_preview  # noqa: E402
from football_prediction_v19.importers.fbref_match_finder_preview import (  # noqa: E402
    FBREF_MATCH_FINDER_PREVIEW_READY,
    MANIFEST_COLUMNS,
)

BUILD_FBREF_MATCH_FINDER_PREVIEW = "BUILD_FBREF_MATCH_FINDER_PREVIEW"
FIX_FBREF_MATCH_FINDER_PREVIEW = "FIX_FBREF_MATCH_FINDER_PREVIEW"
OUTPUT_CSV = "fbref_match_finder_preview_summary.csv"
OUTPUT_MD = "fbref_match_finder_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
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
    status_ok = set(table.get("fbref_match_finder_status", pd.Series(dtype=str)).astype(str)).issubset({FBREF_MATCH_FINDER_PREVIEW_READY}) if "fbref_match_finder_status" in table.columns else False
    matched_ok = bool((pd.to_numeric(table.get("candidates_matched", pd.Series(dtype=int)), errors="coerce").fillna(0) == 1).all()) if "candidates_matched" in table.columns else False
    network_enabled = any(_as_bool(v) for v in table.get("network_calls_enabled", pd.Series(dtype=bool)))
    prediction_enabled = any(_as_bool(v) for v in table.get("prediction_logic_enabled", pd.Series(dtype=bool)))
    betting_enabled = any(_as_bool(v) for v in table.get("betting_logic_enabled", pd.Series(dtype=bool)))
    path_safe = _under(str(path), base, "outputs/provider_pull_preview/fbref/match_finder") and not _protected(str(path))
    for ok, label in [
        (status_ok, "STATUS_NOT_READY"),
        (matched_ok, "MATCH_COUNT_NOT_ONE"),
        (not network_enabled, "NETWORK_ENABLED"),
        (not prediction_enabled, "PREDICTION_ENABLED"),
        (not betting_enabled, "BETTING_ENABLED"),
        (path_safe, "UNSAFE_MANIFEST_PATH"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "manifest_path": str(path),
        "manifests_found": 1,
        "missing_required_columns": " | ".join(missing),
        "status_ok": status_ok,
        "candidates_matched_ok": matched_ok,
        "network_calls_enabled": network_enabled,
        "prediction_logic_enabled": prediction_enabled,
        "betting_logic_enabled": betting_enabled,
        "manifest_path_safe": path_safe,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def _row(path: Path, errors: list[str]) -> dict[str, Any]:
    return {"manifest_path": str(path), "manifests_found": 0, "missing_required_columns": "ALL", "status_ok": False, "candidates_matched_ok": False, "network_calls_enabled": True, "prediction_logic_enabled": True, "betting_logic_enabled": True, "manifest_path_safe": False, "preview_valid": False, "blocking_reasons": " | ".join(errors)}


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_FBREF_MATCH_FINDER_PREVIEW
    if table["preview_valid"].any():
        return FBREF_MATCH_FINDER_PREVIEW_READY
    return FIX_FBREF_MATCH_FINDER_PREVIEW


def run(*, manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    manifest_path = Path(manifest) if manifest else None
    if manifest_path is None or not manifest_path.exists():
        summary = find_fbref_match_preview(provider_match_id="fbref-bundesliga-2024-001", base_dir=base_dir)
        manifest_path = Path(str(summary.get("manifest_path", "")))
    rows = [audit_manifest(manifest_path, base_dir=base_dir)] if manifest_path and manifest_path.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 19.2 FBref Match Finder Preview Audit",
        "",
        f"- manifests audited: {len(table)}",
        f"- valid manifests: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- network_calls_enabled=false",
        "- prediction_logic_enabled=false",
        "- betting_logic_enabled=false",
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
    table, _markdown, rec = run(manifest=args.manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
