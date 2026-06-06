# -*- coding: utf-8 -*-
"""Phase 13.2 trusted xG manifest promotion audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_manifest_promotion import (  # noqa: E402
    TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED,
    TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
    TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE,
    TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG,
    TRUSTED_XG_PROMOTION_READY,
    TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS,
    run_trusted_xg_manifest_promotion,
)
from football_prediction_v19.importers.trusted_xg_source import UNKNOWN_SCHEMA, detect_trusted_xg_source_schema  # noqa: E402

OUTPUT_CSV = "trusted_xg_manifest_promotion_summary.csv"
OUTPUT_MD = "trusted_xg_manifest_promotion_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if path.exists() and resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def discover_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "raw" / "*xg*.csv",
        root / "data" / "manual_xg" / "*xg*.csv",
        root / "data" / "*xg*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def discover_targets(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "processed" / "*_clean.csv",
        root / "data" / "upcoming*_fixtures*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def build_table(root: Path, output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    sources = discover_sources(root)
    targets = discover_targets(root)
    for source in sources:
        try:
            schema = detect_trusted_xg_source_schema(pd.read_csv(source, low_memory=False))
        except Exception:
            schema = UNKNOWN_SCHEMA
        if schema == UNKNOWN_SCHEMA:
            rows.append({
                "source_xg_path": str(source),
                "source_file": source.name,
                "template_source_path": "",
                "target_path": "",
                "target_file": "",
                "promotion_label": TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE,
                "acceptance_label": "",
                "rows_template": 0,
                "rows_filled": 0,
                "rows_missing_xg": 0,
                "join_coverage_pct": 0.0,
                "blocking_reasons": "INVALID_TRUSTED_XG_SOURCE_SCHEMA",
            })
            continue
        for target in targets[:20]:
            result = run_trusted_xg_manifest_promotion(
                source,
                target,
                target,
                output_dir=output_dir,
                write_manifest_preview=False,
            )
            row = result.to_dict()
            row["source_file"] = source.name
            row["target_file"] = target.name
            row["blocking_reasons"] = " | ".join(result.blocking_reasons)
            row["warning_notes"] = " | ".join(result.warning_notes)
            rows.append(row)
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "ADD_TRUSTED_XG_SOURCE_FILE"
    labels = table["promotion_label"].astype(str)
    if labels.isin([TRUSTED_XG_PROMOTION_READY, TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS]).any():
        return "READY_TO_ADD_PRODUCTION_XG_MANIFEST_ENTRY"
    if labels.eq(TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG).any():
        return "FILL_MISSING_XG_FROM_TRUSTED_SOURCE"
    if labels.eq(TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE).any():
        return "FIX_TRUSTED_XG_JOIN_KEYS"
    if labels.eq(TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE).all():
        return "FIX_TRUSTED_XG_SOURCE_SCHEMA"
    return "INCONCLUSIVE_NO_PROMOTION_CANDIDATES"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 40) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ";") for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str, sources_count: int, targets_count: int) -> str:
    labels = table["promotion_label"].astype(str) if not table.empty else pd.Series(dtype=str)
    ready = table[labels == TRUSTED_XG_PROMOTION_READY] if not table.empty else pd.DataFrame()
    warn = table[labels == TRUSTED_XG_PROMOTION_READY_WITH_WARNINGS] if not table.empty else pd.DataFrame()
    blocked = table[labels.str.startswith("TRUSTED_XG_PROMOTION_BLOCKED", na=False)] if not table.empty else pd.DataFrame()
    missing = table[labels == TRUSTED_XG_PROMOTION_BLOCKED_MISSING_XG] if not table.empty else pd.DataFrame()
    low = table[labels == TRUSTED_XG_PROMOTION_BLOCKED_LOW_JOIN_COVERAGE] if not table.empty else pd.DataFrame()
    invalid = table[labels == TRUSTED_XG_PROMOTION_BLOCKED_INVALID_SOURCE] if not table.empty else pd.DataFrame()
    failed = table[labels == TRUSTED_XG_PROMOTION_BLOCKED_ACCEPTANCE_FAILED] if not table.empty else pd.DataFrame()
    cols = ["source_file", "target_file", "rows_template", "rows_filled", "rows_missing_xg", "join_coverage_pct", "promotion_label"]
    lines = [
        "# Phase 13.2 Trusted xG Manifest Promotion Audit",
        "",
        "Phase 13.2 is diagnostic/foundation only. No xG values were inferred or invented, and no production manifest was modified.",
        "",
        "## A. Executive Summary",
        f"- trusted xG candidates scanned: {sources_count}",
        f"- target files scanned: {targets_count}",
        f"- promotion previews attempted: {len(table)}",
        f"- promotion-ready previews: {len(ready) + len(warn)}",
        f"- blocked missing xG: {len(missing)}",
        f"- blocked invalid source: {len(invalid)}",
        f"- blocked low join coverage: {len(low)}",
        f"- blocked acceptance failed: {len(failed)}",
        "",
        "## B. Promotion-Ready Previews",
    ]
    lines += _section_table(ready, cols)
    lines += ["## C. Ready With Warnings"]
    lines += _section_table(warn, cols)
    lines += ["## D. Blocked Promotion Previews"]
    lines += _section_table(blocked, cols + ["blocking_reasons"])
    lines += ["## E. Missing xG Diagnostics"]
    lines += _section_table(missing, cols)
    lines += [
        "## F. Manifest Entry Preview Guidance",
        "Promotion-ready rows create manifest-entry previews only. Review them before manually editing the production manifest.",
        "Use scripts/audit_trusted_xg_intake.py before promotion to identify best source-target pairs.",
        "",
        "## G. Safety Checks",
        "- No source, target, template, or production manifest file modified.",
        "- No xG values inferred or invented.",
        "- No model, probability, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## H. Phase 13.2 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    promotion_dir = root / "outputs" / "xg_promotion_preview"
    sources = discover_sources(root)
    targets = discover_targets(root)
    table = build_table(root, promotion_dir)
    rec = recommendation(table)
    markdown = build_markdown(table, rec, len(sources), len(targets))
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(root=Path(args.root), output_dir=Path(args.output_dir))
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## H. Phase 13.2 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
