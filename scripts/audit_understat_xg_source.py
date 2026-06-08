# -*- coding: utf-8 -*-
"""Phase 13.5 Understat trusted xG source audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_trusted_xg import (  # noqa: E402
    UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED,
    UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_FAILED,
    UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA,
    UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES,
    UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
    UNDERSTAT_XG_IMPORT_READY,
    import_understat_trusted_xg_source,
)
from football_prediction_v19.importers.trusted_xg_source_import import detect_import_source_type  # noqa: E402

OUTPUT_CSV = "understat_xg_source_audit_summary.csv"
OUTPUT_MD = "understat_xg_source_audit_summary.md"


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


def discover_understat_candidates(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "trusted_xg_sources" / "*understat*.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "*understat*.csv",
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
    if source:
        result = import_understat_trusted_xg_source(
            source,
            output_name=Path(str(source)).stem + "_understat_audit_preview.csv",
            overwrite=False,
            no_fetch=True,
        )
        rows.append(result.to_dict())
    for candidate in discover_understat_candidates(root):
        result = import_understat_trusted_xg_source(
            candidate,
            output_name=candidate.name,
            output_dir=candidate.parent,
            overwrite=False,
            no_fetch=True,
        )
        row = result.to_dict()
        if result.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS:
            row["import_label"] = UNDERSTAT_XG_IMPORT_READY
            row["output_path"] = str(candidate)
            row["validation_errors"] = []
        rows.append(row)
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame, source: str | None = None) -> str:
    if table.empty and not source:
        return "ADD_UNDERSTAT_XG_SOURCE_FILE"
    if table.empty:
        return "ADD_UNDERSTAT_XG_SOURCE_FILE"
    labels = table["import_label"].astype(str)
    if labels.eq(UNDERSTAT_XG_IMPORT_READY).any():
        return "READY_FOR_TRUSTED_XG_INTAKE"
    if source and detect_import_source_type(source) == "URL":
        return "FETCH_EXPLICIT_UNDERSTAT_URL"
    if labels.isin([UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED, UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_FAILED]).any():
        return "FETCH_EXPLICIT_UNDERSTAT_URL"
    if labels.eq(UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES).any():
        return "FIX_UNDERSTAT_XG_VALUES"
    if labels.eq(UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA).any():
        return "FIX_UNDERSTAT_XG_SCHEMA"
    return "INCONCLUSIVE_UNDERSTAT_XG_IMPORT"


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
    ready = serial[labels == UNDERSTAT_XG_IMPORT_READY] if not serial.empty else pd.DataFrame()
    invalid_schema = serial[labels == UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA] if not serial.empty else pd.DataFrame()
    invalid_xg = serial[labels == UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES] if not serial.empty else pd.DataFrame()
    blocked = serial[labels.ne(UNDERSTAT_XG_IMPORT_READY)] if not serial.empty else pd.DataFrame()
    cols = ["source", "source_type", "rows_read", "rows_normalized", "detected_schema", "output_path", "import_label"]
    lines = [
        "# Phase 13.5 Understat Trusted xG Source Audit",
        "",
        "Phase 13.5 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- files scanned: {len(serial)}",
        f"- import-ready files: {len(ready)}",
        f"- invalid schema files: {len(invalid_schema)}",
        f"- invalid xG value files: {len(invalid_xg)}",
        f"- blocked files: {len(blocked)}",
        "",
        "## B. Import-Ready Understat xG Sources",
    ]
    lines += _section_table(ready, cols)
    lines += ["## C. Invalid Schema Sources"]
    lines += _section_table(invalid_schema, cols + ["validation_errors"])
    lines += ["## D. Invalid xG Value Sources"]
    lines += _section_table(invalid_xg, cols + ["validation_errors"])
    lines += ["## E. Blocked / Missing Sources"]
    lines += _section_table(blocked, cols + ["validation_errors"])
    lines += [
        "## F. Safety Checks",
        "- No xG values inferred, invented, estimated from scores, odds, shots, or model output.",
        "- No hidden scraping, credentials, API keys, or model behavior changes.",
        "- Explicit URL fetches are only performed by the import CLI when the user provides the URL.",
        "- No market_tier, probability, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## G. Phase 13.5 Recommendation",
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
