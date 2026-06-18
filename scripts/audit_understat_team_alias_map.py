# -*- coding: utf-8 -*-
"""Audit the Understat team alias-map template or user-provided alias map."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

REQUIRED_COLUMNS = ["provider", "league", "season", "source_team", "target_team", "alias_status", "notes"]
XG_COLUMNS = {"home_xg", "away_xg", "xg", "xga", "hxg", "axg", "home_xG", "away_xG"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias-map", default=str(ROOT / "data" / "templates" / "understat_team_alias_map_template.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def audit_alias_map(alias_map: str | Path) -> tuple[pd.DataFrame, str, list[str]]:
    path = Path(alias_map)
    if not path.is_absolute():
        path = ROOT / path
    rows = []
    if not path.exists():
        rows.append({"check": "alias_map_exists", "status": "FAIL", "detail": str(path)})
        return pd.DataFrame(rows), "CREATE_UNDERSTAT_TEAM_ALIAS_MAP", ["ALIAS_MAP_NOT_FOUND"]
    df = pd.read_csv(path, low_memory=False)
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    rows.append({"check": "required_columns", "status": "FAIL" if missing else "PASS", "detail": ",".join(missing)})
    xg_cols = sorted(set(df.columns).intersection(XG_COLUMNS))
    rows.append({"check": "no_xg_columns", "status": "FAIL" if xg_cols else "PASS", "detail": ",".join(xg_cols)})
    accepted = df[df.get("alias_status", pd.Series(dtype=str)).astype(str).str.strip().str.lower().eq("accepted")].copy() if "alias_status" in df.columns else pd.DataFrame()
    empty_accepted = 0
    duplicate_accepted = 0
    if not accepted.empty and {"source_team", "target_team"}.issubset(df.columns):
        empty_accepted = int((accepted[["source_team", "target_team"]].isna() | accepted[["source_team", "target_team"]].astype(str).apply(lambda col: col.str.strip().eq(""))).any(axis=1).sum())
        duplicate_accepted = int(accepted["source_team"].astype(str).str.strip().duplicated().sum())
    rows.append({"check": "accepted_aliases_have_teams", "status": "FAIL" if empty_accepted else "PASS", "detail": str(empty_accepted)})
    rows.append({"check": "no_duplicate_accepted_source_team", "status": "FAIL" if duplicate_accepted else "PASS", "detail": str(duplicate_accepted)})
    table = pd.DataFrame(rows)
    failures = table[table["status"].eq("FAIL")]["check"].tolist()
    if missing or xg_cols or empty_accepted or duplicate_accepted:
        rec = "FIX_UNDERSTAT_TEAM_ALIAS_MAP"
    elif accepted.empty:
        rec = "CREATE_UNDERSTAT_TEAM_ALIAS_MAP" if df.empty else "REVIEW_UNDERSTAT_TEAM_ALIAS_MAP"
    else:
        rec = "UNDERSTAT_TEAM_ALIAS_MAP_READY"
    return table, rec, failures


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    rows = ["| check | status | detail |", "| --- | --- | --- |"]
    for _idx, row in table.fillna("").iterrows():
        rows.append(f"| {row['check']} | {row['status']} | {str(row['detail']).replace('|', '/')} |")
    return "\n".join([
        "# Understat Team Alias Map Audit",
        "",
        "Phase 13.9 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## Summary",
        "\n".join(rows),
        "",
        "## Recommendation",
        rec,
        "",
        "## Safety Checks",
        "- Alias maps do not contain xG values.",
        "- No source or target CSV is modified by this audit.",
        "- Production manifests are not modified.",
        "",
    ])


def run(alias_map: str | Path | None = None, output_dir: str | Path | None = None) -> tuple[pd.DataFrame, str, str]:
    alias_map = alias_map or (ROOT / "data" / "templates" / "understat_team_alias_map_template.csv")
    output_dir = Path(output_dir or (ROOT / "outputs" / "diagnostics"))
    output_dir.mkdir(parents=True, exist_ok=True)
    table, rec, _failures = audit_alias_map(alias_map)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / "understat_team_alias_map_audit_summary.csv", index=False)
    (output_dir / "understat_team_alias_map_audit_summary.md").write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, _markdown, rec = run(args.alias_map, args.output_dir)
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
