# -*- coding: utf-8 -*-
"""Audit Understat real snapshot smoke preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_understat_real_snapshot_smoke_preview import build_understat_real_snapshot_smoke_preview  # noqa: E402
from football_prediction_v19.importers.understat_real_snapshot_smoke_preview import MANIFEST_COLUMNS  # noqa: E402

UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY = "UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY"
BUILD_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW = "BUILD_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW"
FIX_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW = "FIX_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW"
OUTPUT_CSV = "understat_real_snapshot_smoke_preview_summary.csv"
OUTPUT_MD = "understat_real_snapshot_smoke_preview_summary.md"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run(*, manifest: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT):
    base = Path(base_dir).resolve()
    manifest_path = Path(manifest) if manifest else base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot" / "understat_real_snapshot_manifest.csv"
    if not manifest_path.exists():
        fixture = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
        build_understat_real_snapshot_smoke_preview(local_snapshot=fixture, output_dir=base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot", base_dir=base)
    errors: list[str] = []
    if not manifest_path.exists():
        table = pd.DataFrame()
        rec = BUILD_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW
    else:
        frame = pd.read_csv(manifest_path, low_memory=False)
        row = frame.iloc[0].to_dict() if not frame.empty else {}
        missing = sorted(set(MANIFEST_COLUMNS) - set(frame.columns))
        checks = {
            "required_columns": not missing,
            "status_ready": row.get("real_snapshot_status") == UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY,
            "network_disabled": str(row.get("network_calls_enabled", "")).lower() == "false" or row.get("network_calls_enabled") is False,
            "raw_path_safe": _safe(row.get("raw_snapshot_path", ""), base, "outputs/provider_pull_preview/understat/real_snapshot/raw"),
            "normalized_path_safe": _safe(row.get("normalized_output_path", ""), base, "outputs/provider_pull_preview/understat/real_snapshot/normalized"),
            "rows_normalized": int(row.get("rows_normalized", 0) or 0) > 0,
        }
        errors = [k for k, ok in checks.items() if not ok]
        rec = UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW_READY if not errors else FIX_UNDERSTAT_REAL_SNAPSHOT_SMOKE_PREVIEW
        table = pd.DataFrame([{**checks, "manifest_path": str(manifest_path), "preview_valid": not errors, "blocking_reasons": " | ".join(errors), "recommendation": rec}])
    md = "\n".join(["# Understat Real Snapshot Smoke Preview Audit", "", f"- recommendation: {rec}", "- no model/prediction/market/betting/staking logic is invoked", ""])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(md, encoding="utf-8")
    return table, md, rec


def _safe(path_text, base: Path, rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    allowed = (base / rel).resolve()
    text = str(resolved).replace("\\", "/").lower()
    return (resolved == allowed or allowed in resolved.parents) and not any(token in text for token in PROTECTED)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, _md, rec = run(manifest=args.manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
