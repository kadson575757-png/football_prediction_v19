# -*- coding: utf-8 -*-
"""Audit preview-only Understat + FBref match context bundle."""
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

from build_match_context_bundle_preview import build_match_context_bundle_preview  # noqa: E402
from football_prediction_v19.analysis.match_context_bundle_preview import (  # noqa: E402
    BUNDLE_COLUMNS,
    MANIFEST_COLUMNS,
    MATCH_CONTEXT_BUNDLE_PREVIEW_READY,
)

BUILD_MATCH_CONTEXT_BUNDLE_PREVIEW = "BUILD_MATCH_CONTEXT_BUNDLE_PREVIEW"
FIX_MATCH_CONTEXT_BUNDLE_PREVIEW = "FIX_MATCH_CONTEXT_BUNDLE_PREVIEW"
OUTPUT_CSV = "match_context_bundle_preview_summary.csv"
OUTPUT_MD = "match_context_bundle_preview_summary.md"
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
        manifest = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return _row(path, [str(exc)])
    missing = sorted(set(MANIFEST_COLUMNS) - set(manifest.columns))
    if missing:
        errors.append("MISSING_MANIFEST_COLUMNS")
    output_path = str(manifest.get("output_path", pd.Series([""])).fillna("").iloc[0])
    status_ok = set(manifest.get("context_bundle_status", pd.Series(dtype=str)).astype(str)).issubset({MATCH_CONTEXT_BUNDLE_PREVIEW_READY}) if "context_bundle_status" in manifest.columns else False
    joined_ok = bool((pd.to_numeric(manifest.get("rows_joined", pd.Series(dtype=int)), errors="coerce").fillna(0) == 1).all()) if "rows_joined" in manifest.columns else False
    matched_ok = bool((pd.to_numeric(manifest.get("candidates_matched", pd.Series(dtype=int)), errors="coerce").fillna(0) == 1).all()) if "candidates_matched" in manifest.columns else False
    network = any(_as_bool(v) for v in manifest.get("network_calls_enabled", pd.Series(dtype=bool)))
    prediction = any(_as_bool(v) for v in manifest.get("prediction_logic_enabled", pd.Series(dtype=bool)))
    betting = any(_as_bool(v) for v in manifest.get("betting_logic_enabled", pd.Series(dtype=bool)))
    output_safe = _under(output_path, base, "outputs/analysis_preview/match_context_bundle") and not _protected(output_path)
    bundle_columns_ok = False
    if output_path and Path(output_path).exists():
        bundle_columns_ok = set(BUNDLE_COLUMNS).issubset(set(pd.read_csv(output_path, nrows=0).columns))
    for ok, label in [
        (status_ok, "STATUS_NOT_READY"),
        (joined_ok, "ROWS_JOINED_NOT_ONE"),
        (matched_ok, "CANDIDATES_MATCHED_NOT_ONE"),
        (not network, "NETWORK_ENABLED"),
        (not prediction, "PREDICTION_ENABLED"),
        (not betting, "BETTING_ENABLED"),
        (output_safe, "UNSAFE_OUTPUT_PATH"),
        (bundle_columns_ok, "BUNDLE_COLUMNS_MISSING"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "manifest_path": str(path),
        "manifests_found": 1,
        "missing_required_columns": " | ".join(missing),
        "status_ok": status_ok,
        "rows_joined_ok": joined_ok,
        "candidates_matched_ok": matched_ok,
        "network_calls_enabled": network,
        "prediction_logic_enabled": prediction,
        "betting_logic_enabled": betting,
        "output_path_safe": output_safe,
        "bundle_columns_ok": bundle_columns_ok,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def _row(path: Path, errors: list[str]) -> dict[str, Any]:
    return {"manifest_path": str(path), "manifests_found": 0, "missing_required_columns": "ALL", "status_ok": False, "rows_joined_ok": False, "candidates_matched_ok": False, "network_calls_enabled": True, "prediction_logic_enabled": True, "betting_logic_enabled": True, "output_path_safe": False, "bundle_columns_ok": False, "preview_valid": False, "blocking_reasons": " | ".join(errors)}


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_MATCH_CONTEXT_BUNDLE_PREVIEW
    if table["preview_valid"].any():
        return MATCH_CONTEXT_BUNDLE_PREVIEW_READY
    return FIX_MATCH_CONTEXT_BUNDLE_PREVIEW


def run(*, manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    manifest_path = Path(manifest) if manifest else None
    if manifest_path is None or not manifest_path.exists():
        summary = build_match_context_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001", base_dir=base_dir)
        manifest_path = Path(str(summary.get("manifest_path", "")))
    rows = [audit_manifest(manifest_path, base_dir=base_dir)] if manifest_path and manifest_path.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 19.4 Match Context Bundle Preview Audit",
        "",
        f"- manifests audited: {len(table)}",
        f"- valid manifests: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- network_calls_enabled=false",
        "- prediction_logic_enabled=false",
        "- betting_logic_enabled=false",
        "- no model/probability/market/betting/staking/ROI/SUPER_A_TIER logic is invoked",
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
