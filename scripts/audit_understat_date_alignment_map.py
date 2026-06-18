# -*- coding: utf-8 -*-
"""Audit a reviewed Understat date-alignment map."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

REQUIRED_COLUMNS = ["provider", "league", "season", "home_team", "away_team", "source_date", "target_date", "alignment_status", "notes"]
ALLOWED_STATUSES = {"accepted", "pending", "rejected"}
XG_COLUMNS = {"home_xg", "away_xg", "xg", "xga", "hxg", "axg", "home_xG", "away_xG"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date-map", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def _resolve(path: str | Path) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = ROOT / out
    return out


def _blank_mask(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    return df[columns].isna().any(axis=1) | df[columns].astype(str).apply(lambda col: col.str.strip().eq("")).any(axis=1)


def audit_date_alignment_map(date_map: str | Path) -> tuple[pd.DataFrame, str, list[str]]:
    path = _resolve(date_map)
    rows = []
    if not path.exists():
        rows.append({"check": "date_map_exists", "status": "FAIL", "detail": str(path)})
        return pd.DataFrame(rows), "CREATE_UNDERSTAT_DATE_ALIGNMENT_MAP", ["DATE_MAP_NOT_FOUND"]
    df = pd.read_csv(path, low_memory=False)
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    rows.append({"check": "required_columns", "status": "FAIL" if missing else "PASS", "detail": ",".join(missing)})
    xg_cols = sorted(set(df.columns).intersection(XG_COLUMNS))
    rows.append({"check": "no_xg_columns", "status": "FAIL" if xg_cols else "PASS", "detail": ",".join(xg_cols)})
    invalid_status = 0
    accepted_empty = 0
    invalid_dates = 0
    duplicate_accepted = 0
    if "alignment_status" in df.columns:
        statuses = df["alignment_status"].astype(str).str.strip().str.lower()
        invalid_status = int((~statuses.isin(ALLOWED_STATUSES)).sum())
        accepted = df[statuses.eq("accepted")].copy()
    else:
        accepted = pd.DataFrame()
    rows.append({"check": "alignment_status_allowed", "status": "FAIL" if invalid_status else "PASS", "detail": str(invalid_status)})
    if not accepted.empty and {"home_team", "away_team", "source_date", "target_date"}.issubset(df.columns):
        accepted_empty = int(_blank_mask(accepted, ["home_team", "away_team", "source_date", "target_date"]).sum())
        source_dates = pd.to_datetime(accepted["source_date"], errors="coerce", format="mixed")
        target_dates = pd.to_datetime(accepted["target_date"], errors="coerce", format="mixed")
        invalid_dates = int(source_dates.isna().sum() + target_dates.isna().sum())
        key = (
            accepted["home_team"].astype(str).str.strip().str.lower()
            + "|"
            + accepted["away_team"].astype(str).str.strip().str.lower()
            + "|"
            + source_dates.dt.strftime("%Y-%m-%d").astype(str)
        )
        duplicate_accepted = int(key.duplicated().sum())
    rows.append({"check": "accepted_alignments_have_identity", "status": "FAIL" if accepted_empty else "PASS", "detail": str(accepted_empty)})
    rows.append({"check": "dates_parseable", "status": "FAIL" if invalid_dates else "PASS", "detail": str(invalid_dates)})
    rows.append({"check": "no_duplicate_accepted_source_mapping", "status": "FAIL" if duplicate_accepted else "PASS", "detail": str(duplicate_accepted)})
    table = pd.DataFrame(rows)
    failures = table[table["status"].eq("FAIL")]["check"].tolist()
    if failures:
        rec = "FIX_UNDERSTAT_DATE_ALIGNMENT_MAP"
    elif accepted.empty:
        rec = "CREATE_UNDERSTAT_DATE_ALIGNMENT_MAP" if df.empty else "REVIEW_UNDERSTAT_DATE_ALIGNMENT_MAP"
    else:
        rec = "UNDERSTAT_DATE_ALIGNMENT_MAP_READY"
    return table, rec, failures


def _markdown_table(table: pd.DataFrame) -> str:
    rows = ["| check | status | detail |", "| --- | --- | --- |"]
    for _idx, row in table.fillna("").iterrows():
        rows.append(f"| {row['check']} | {row['status']} | {str(row['detail']).replace('|', '/')} |")
    return "\n".join(rows)


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    return "\n".join([
        "# Understat Date Alignment Map Audit",
        "",
        "Phase 13.10b is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## Summary",
        _markdown_table(table),
        "",
        "## Recommendation",
        rec,
        "",
        "## Safety Checks",
        "- Date maps do not contain xG values.",
        "- No source or target CSV is modified by this audit.",
        "- Production manifests are not modified.",
        "",
    ])


def run(date_map: str | Path, output_dir: str | Path | None = None) -> tuple[pd.DataFrame, str, str]:
    output_dir = Path(output_dir or (ROOT / "outputs" / "diagnostics"))
    output_dir.mkdir(parents=True, exist_ok=True)
    table, rec, _failures = audit_date_alignment_map(date_map)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / "understat_date_alignment_map_audit_summary.csv", index=False)
    (output_dir / "understat_date_alignment_map_audit_summary.md").write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, _markdown, rec = run(args.date_map, args.output_dir)
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
