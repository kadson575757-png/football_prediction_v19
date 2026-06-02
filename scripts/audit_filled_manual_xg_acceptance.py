# -*- coding: utf-8 -*-
"""Phase 12.12 filled manual xG acceptance audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import (  # noqa: E402
    MANUAL_XG_ACCEPTED,
    MANUAL_XG_ACCEPTED_WITH_WARNINGS,
    MANUAL_XG_REJECTED_INVALID_VALUES,
    MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE,
    MANUAL_XG_REJECTED_MISSING_VALUES,
    MANUAL_XG_TEMPLATE_ONLY,
    evaluate_manual_xg_acceptance,
)

OUTPUT_CSV = "filled_manual_xg_acceptance_summary.csv"
OUTPUT_MD = "filled_manual_xg_acceptance_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if path.exists() and resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def discover_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "manual_xg" / "*.csv",
        root / "data" / "raw" / "*xg*.csv",
        root / "data" / "*xg*.csv",
        root / "data" / "templates" / "manual_xg_template.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def discover_targets(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "processed" / "real_matches_clean.csv",
        root / "data" / "processed" / "matches_clean_with_totals.csv",
        root / "data" / "processed" / "*_clean.csv",
        root / "data" / "upcoming*_fixtures*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def _is_template_or_sample(path: Path) -> bool:
    name = path.name.lower()
    return "template" in name or "sample" in name


def build_table(root: Path, min_join_coverage: float = 95.0) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    targets = discover_targets(root)
    for xg in discover_candidates(root):
        try:
            xg_df = pd.read_csv(xg, low_memory=False)
        except Exception as exc:
            rows.append({
                "xg_source_path": str(xg),
                "xg_file_name": xg.name,
                "target_path": "",
                "target_file_name": "",
                "rows_source": 0,
                "acceptance_label": "MANUAL_XG_REJECTED_INVALID_SCHEMA",
                "blocking_reasons": str(exc),
                "warning_notes": "",
                "join_coverage_pct": 0.0,
            })
            continue
        target_list = [None] if _is_template_or_sample(xg) or not targets else targets
        for target in target_list:
            target_df = pd.read_csv(target, low_memory=False) if target is not None else None
            _joined, result = evaluate_manual_xg_acceptance(
                xg_df,
                target_df=target_df,
                source_path=xg,
                target_path=target,
                min_join_coverage=min_join_coverage,
            )
            row = result.to_dict()
            row["xg_source_path"] = str(xg)
            row["xg_file_name"] = xg.name
            row["target_file_name"] = target.name if target is not None else ""
            row["blocking_reasons"] = " | ".join(result.blocking_reasons)
            row["warning_notes"] = " | ".join(result.warning_notes)
            rows.append(row)
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_MANUAL_XG_CANDIDATES"
    labels = table["acceptance_label"].astype(str)
    if (labels == MANUAL_XG_ACCEPTED).any():
        return "READY_FOR_MANUAL_XG_ENRICHMENT_PIPELINE"
    if labels.isin([MANUAL_XG_REJECTED_MISSING_VALUES, MANUAL_XG_REJECTED_INVALID_VALUES]).any():
        return "FIX_MANUAL_XG_VALUES"
    if (labels == MANUAL_XG_REJECTED_LOW_JOIN_COVERAGE).any():
        return "FIX_MANUAL_XG_JOIN_KEYS"
    if (labels == MANUAL_XG_TEMPLATE_ONLY).any():
        return "FILL_MANUAL_XG_TEMPLATE_VALUES"
    if not table.empty:
        return "ADD_PRODUCTION_MANUAL_XG_FILE"
    return "INCONCLUSIVE_NO_MANUAL_XG_CANDIDATES"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 50) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    labels = table["acceptance_label"].astype(str) if not table.empty else pd.Series(dtype=str)
    accepted = table[labels == MANUAL_XG_ACCEPTED] if not table.empty else pd.DataFrame()
    warn = table[labels == MANUAL_XG_ACCEPTED_WITH_WARNINGS] if not table.empty else pd.DataFrame()
    templates = table[labels == MANUAL_XG_TEMPLATE_ONLY] if not table.empty else pd.DataFrame()
    rejected = table[labels.str.startswith("MANUAL_XG_REJECTED", na=False)] if not table.empty else pd.DataFrame()
    no_target = table[labels == "MANUAL_XG_NO_TARGET_PROVIDED"] if not table.empty else pd.DataFrame()
    best_coverage = float(table["join_coverage_pct"].max()) if not table.empty else 0.0
    cols = ["xg_file_name", "target_file_name", "rows_source", "rows_valid", "rows_join_matched", "join_coverage_pct", "acceptance_label", "blocking_reasons"]
    lines = [
        "# Phase 12.12 Filled Manual xG Acceptance Audit",
        "",
        "Phase 12.12 is diagnostic/foundation only. No xG values were inferred, invented, filled, deleted, or written back to source data.",
        "",
        "## A. Executive Summary",
        f"- candidates scanned: {table['xg_file_name'].nunique() if not table.empty else 0}",
        f"- accepted production manual xG files: {accepted['xg_file_name'].nunique() if not accepted.empty else 0}",
        f"- accepted with warnings: {warn['xg_file_name'].nunique() if not warn.empty else 0}",
        f"- rejected files: {rejected['xg_file_name'].nunique() if not rejected.empty else 0}",
        f"- template-only files: {templates['xg_file_name'].nunique() if not templates.empty else 0}",
        f"- no-target files: {no_target['xg_file_name'].nunique() if not no_target.empty else 0}",
        f"- best join coverage observed: {round(best_coverage, 2)}",
        "",
        "## B. Accepted Manual xG Files",
    ]
    lines += _section_table(accepted, cols)
    lines += ["## C. Accepted With Warnings"]
    lines += _section_table(warn, cols)
    lines += ["## D. Rejected Manual xG Files"]
    lines += _section_table(rejected, cols)
    lines += ["## E. Template-Only Files"]
    lines += _section_table(templates, ["xg_file_name", "rows_source", "missing_xg_count", "acceptance_label"])
    lines += ["## F. Join Coverage Diagnostics"]
    lines += _section_table(table.sort_values("join_coverage_pct", ascending=False) if not table.empty else table, ["xg_file_name", "target_file_name", "rows_join_matched", "join_coverage_pct", "acceptance_label"], limit=25)
    lines += [
        "## G. Safety Checks",
        "- No source or target CSV modified.",
        "- No xG values inferred, invented, filled, deleted, or written back.",
        "- No web/API/credential, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## H. Phase 12.12 Recommendation",
        rec,
        "",
        "Use scripts/audit_manual_xg_manifest.py to declare future production manual xG files.",
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None, min_join_coverage: float = 95.0) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root, min_join_coverage=min_join_coverage)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--min-join-coverage", type=float, default=95.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(root=Path(args.root), output_dir=Path(args.output_dir), min_join_coverage=args.min_join_coverage)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## H. Phase 12.12 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
