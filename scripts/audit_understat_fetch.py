# -*- coding: utf-8 -*-
"""Phase 13.6 Understat league/season fetch audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_fetch import (  # noqa: E402
    detect_understat_html_state,
    normalize_understat_matches_to_trusted_xg,
    parse_understat_matches_from_html,
)

OUTPUT_CSV = "understat_fetch_audit_summary.csv"
OUTPUT_MD = "understat_fetch_audit_summary.md"


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


def discover_raw(root: Path) -> list[Path]:
    raw_dir = root / "data" / "trusted_xg_sources" / "raw"
    return _unique(sorted(raw_dir.glob("*understat*.html")) if raw_dir.exists() else [])


def discover_normalized(root: Path) -> list[Path]:
    source_dir = root / "data" / "trusted_xg_sources"
    return _unique(sorted(source_dir.glob("*understat*.csv")) if source_dir.exists() else [])


def _validate_normalized(path: Path) -> dict[str, object]:
    try:
        df = pd.read_csv(path, low_memory=False)
        required = {"date", "home_team", "away_team", "home_xg", "away_xg"}
        if not required.issubset(df.columns):
            return {"path": str(path), "file": path.name, "kind": "normalized", "rows": len(df), "status": "INVALID_SCHEMA", "error": "MISSING_REQUIRED_COLUMNS"}
        raw = df[["home_xg", "away_xg"]]
        missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
        numeric = raw.apply(pd.to_numeric, errors="coerce")
        if missing.any().any():
            return {"path": str(path), "file": path.name, "kind": "normalized", "rows": len(df), "status": "INVALID_XG_VALUES", "error": "MISSING_XG_VALUES"}
        if numeric.isna().any().any():
            return {"path": str(path), "file": path.name, "kind": "normalized", "rows": len(df), "status": "INVALID_XG_VALUES", "error": "NON_NUMERIC_XG_VALUES"}
        if (numeric < 0).any().any():
            return {"path": str(path), "file": path.name, "kind": "normalized", "rows": len(df), "status": "INVALID_XG_VALUES", "error": "NEGATIVE_XG_VALUES"}
        return {"path": str(path), "file": path.name, "kind": "normalized", "rows": len(df), "status": "READY", "error": ""}
    except Exception as exc:
        return {"path": str(path), "file": path.name, "kind": "normalized", "rows": 0, "status": "INVALID_SCHEMA", "error": str(exc)}


def _validate_raw(path: Path) -> dict[str, object]:
    html_state = ""
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
        html_state = detect_understat_html_state(html)
        matches = parse_understat_matches_from_html(html)
        normalized = normalize_understat_matches_to_trusted_xg(matches)
        status = "RAW_PARSE_READY" if not normalized.empty else "RAW_NO_MATCHES"
        error = ""
        rows = len(normalized)
    except Exception as exc:
        status = "RAW_PARSE_FAILED"
        error = str(exc)
        rows = 0
    return {"path": str(path), "file": path.name, "kind": "raw_html", "rows": rows, "status": status, "html_state": html_state, "error": error}


def build_table(root: Path = ROOT) -> pd.DataFrame:
    rows = [_validate_raw(path) for path in discover_raw(root)]
    rows.extend(_validate_normalized(path) for path in discover_normalized(root))
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "FETCH_UNDERSTAT_LEAGUE_SEASON"
    statuses = table["status"].astype(str)
    if statuses.eq("READY").any():
        return "READY_FOR_TRUSTED_XG_INTAKE"
    if statuses.eq("INVALID_XG_VALUES").any():
        return "FIX_UNDERSTAT_FETCH_XG_VALUES"
    if statuses.eq("RAW_PARSE_FAILED").any() or statuses.eq("RAW_PARSE_READY").any():
        return "FIX_UNDERSTAT_FETCH_PARSE"
    return "INCONCLUSIVE_UNDERSTAT_FETCH"


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
    raw = table[table["kind"].eq("raw_html")] if not table.empty else pd.DataFrame()
    normalized = table[table["kind"].eq("normalized")] if not table.empty else pd.DataFrame()
    blocked = table[~table["status"].isin(["READY", "RAW_PARSE_READY"])] if not table.empty else pd.DataFrame()
    cols = ["file", "kind", "rows", "status", "html_state", "error"]
    lines = [
        "# Phase 13.6 Understat Fetch Audit",
        "",
        "Phase 13.6 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- raw Understat fetches: {len(raw)}",
        f"- normalized Understat trusted sources: {len(normalized)}",
        f"- blocked / missing sources: {len(blocked)}",
        "",
        "## B. Raw Understat Fetches",
    ]
    lines += _section_table(raw, cols)
    lines += ["## C. Normalized Understat Trusted Sources"]
    lines += _section_table(normalized, cols)
    lines += ["## D. Blocked / Missing Sources"]
    lines += _section_table(blocked, cols)
    if not raw.empty and normalized.empty:
        lines += [
            "Raw Understat HTML exists but no parseable xG match payload was found.",
            "",
        ]
    lines += [
        "## E. Recommended Next Commands",
        "```powershell",
        "python scripts/fetch_understat_xg_source.py --league Bundesliga --season 2024 --output-name understat_xg_bundesliga_2024.csv",
        "python scripts/audit_understat_fetch.py",
        "python scripts/audit_understat_xg_source.py",
        "python scripts/audit_trusted_xg_intake.py --write-command-list",
        "```",
        "",
        "## F. Safety Checks",
        "- No xG values inferred, invented, estimated from scores, odds, shots, or model output.",
        "- No hidden scraping, credentials, API keys, browser automation, or model behavior changes.",
        "- Runtime fetching happens only when the user explicitly calls the fetch CLI.",
        "- No market_tier, probability, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## G. Phase 13.6 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(ROOT, Path(args.output_dir))
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
