# -*- coding: utf-8 -*-
"""Phase 13.4 trusted xG source import audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_source_import import (  # noqa: E402
    TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA,
    TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES,
    TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
    TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND,
    TRUSTED_XG_IMPORT_READY,
    detect_import_source_type,
    import_trusted_xg_source,
)

OUTPUT_CSV = "trusted_xg_source_import_summary.csv"
OUTPUT_MD = "trusted_xg_source_import_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return out


def discover_import_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "trusted_xg_sources" / "*.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def _serialize(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    for col in ("validation_errors", "warning_notes"):
        if col in out.columns:
            out[col] = out[col].map(lambda value: " | ".join(value) if isinstance(value, list) else str(value or ""))
    return out


def build_table(root: Path = ROOT, source: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    candidates = discover_import_candidates(root)
    if source:
        result = import_trusted_xg_source(source, output_name=Path(str(source)).stem + "_audit_preview.csv", overwrite=False, no_fetch=True)
        rows.append(result.to_dict())
    for candidate in candidates:
        result = import_trusted_xg_source(
            candidate,
            output_name=candidate.name,
            output_dir=candidate.parent,
            overwrite=False,
            no_fetch=True,
        )
        row = result.to_dict()
        if result.import_label == TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS:
            row["import_label"] = TRUSTED_XG_IMPORT_READY
            row["output_path"] = str(candidate)
            row["validation_errors"] = []
        rows.append(row)
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame, source: str | None = None) -> str:
    if table.empty and not source:
        return "ADD_TRUSTED_XG_SOURCE_FILE"
    if source and detect_import_source_type(source) == "URL" and table.empty:
        return "FETCH_EXPLICIT_SOURCE_URL"
    if table.empty:
        return "ADD_TRUSTED_XG_SOURCE_FILE"
    labels = table["import_label"].astype(str)
    if labels.eq(TRUSTED_XG_IMPORT_READY).any():
        return "READY_FOR_TRUSTED_XG_INTAKE"
    if source and detect_import_source_type(source) == "URL":
        return "FETCH_EXPLICIT_SOURCE_URL"
    if labels.eq(TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES).any():
        return "FIX_TRUSTED_XG_VALUES"
    if labels.eq(TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA).any():
        return "FIX_TRUSTED_XG_IMPORT_SCHEMA"
    if labels.eq(TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND).any():
        return "FETCH_EXPLICIT_SOURCE_URL"
    return "INCONCLUSIVE_TRUSTED_XG_IMPORT"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 40) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ";") for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    serial = _serialize(table)
    labels = serial["import_label"].astype(str) if not serial.empty else pd.Series(dtype=str)
    ready = serial[labels == TRUSTED_XG_IMPORT_READY] if not serial.empty else pd.DataFrame()
    invalid_schema = serial[labels == TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA] if not serial.empty else pd.DataFrame()
    invalid_xg = serial[labels == TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES] if not serial.empty else pd.DataFrame()
    output_exists = serial[labels == TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS] if not serial.empty else pd.DataFrame()
    missing = serial[labels == TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND] if not serial.empty else pd.DataFrame()
    cols = ["source", "source_type", "rows_read", "rows_normalized", "detected_schema", "output_path", "import_label"]
    lines = [
        "# Phase 13.4 Trusted xG Source Import Audit",
        "",
        "Phase 13.4 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- files scanned: {len(serial)}",
        f"- import-ready files: {len(ready)}",
        f"- invalid schema files: {len(invalid_schema)}",
        f"- invalid xG value files: {len(invalid_xg)}",
        f"- output exists / blocked files: {len(output_exists)}",
        f"- source-not-found files: {len(missing)}",
        "",
        "## B. Import-Ready Trusted xG Sources",
    ]
    lines += _section_table(ready, cols)
    lines += ["## C. Invalid Schema Sources"]
    lines += _section_table(invalid_schema, cols + ["validation_errors"])
    lines += ["## D. Invalid xG Value Sources"]
    lines += _section_table(invalid_xg, cols + ["validation_errors"])
    lines += ["## E. Blocked / Missing Sources"]
    blocked = serial[labels.ne(TRUSTED_XG_IMPORT_READY)] if not serial.empty else pd.DataFrame()
    lines += _section_table(blocked, cols + ["validation_errors"])
    lines += [
        "## F. Safety Checks",
        "- No xG values inferred, invented, estimated from odds, scores, shots, or model output.",
        "- No hidden scraping, credentials, API keys, or model behavior changes.",
        "- Explicit URL fetches are only performed by the import CLI when the user provides the URL.",
        "- No market_tier, probability, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## G. Phase 13.4 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None, source: str | None = None) -> tuple[pd.DataFrame, str, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root, source=source)
    rec = recommendation(table, source=source)
    markdown = build_markdown(table, rec)
    _serialize(table).to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(ROOT, Path(args.output_dir), source=args.source)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
