# -*- coding: utf-8 -*-
"""Phase 13.7 Understat data-access fallback audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_data_access import (  # noqa: E402
    UNDERSTAT_ACCESS_READY,
    discover_existing_understat_sources,
    parse_raw_understat_payload_or_html,
    validate_understat_normalized_xg,
)

OUTPUT_CSV = "understat_data_access_summary.csv"
OUTPUT_MD = "understat_data_access_summary.md"


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
    return _unique(sorted(raw_dir.glob("*understat*")) if raw_dir.exists() else [])


def _validate_existing(path: Path) -> dict[str, object]:
    try:
        df = pd.read_csv(path, low_memory=False)
        errors = validate_understat_normalized_xg(df)
        status = "READY" if not errors else "INVALID"
        return {
            "file": path.name,
            "path": str(path),
            "kind": "existing_normalized",
            "rows": len(df) if not errors else 0,
            "status": status,
            "access_label": UNDERSTAT_ACCESS_READY if not errors else "UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND",
            "error": " | ".join(errors),
        }
    except Exception as exc:
        return {"file": path.name, "path": str(path), "kind": "existing_normalized", "rows": 0, "status": "INVALID", "access_label": "UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND", "error": str(exc)}


def _validate_raw(path: Path) -> dict[str, object]:
    try:
        df = parse_raw_understat_payload_or_html(path)
        return {"file": path.name, "path": str(path), "kind": "raw_understat", "rows": len(df), "status": "RAW_PARSE_READY", "access_label": UNDERSTAT_ACCESS_READY, "error": ""}
    except Exception as exc:
        return {"file": path.name, "path": str(path), "kind": "raw_understat", "rows": 0, "status": "RAW_PARSE_FAILED", "access_label": "UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED", "error": str(exc)}


def build_table(root: Path = ROOT) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.extend(_validate_existing(path) for path in discover_existing_understat_sources(root / "data" / "trusted_xg_sources"))
    rows.extend(_validate_raw(path) for path in discover_raw(root))
    return pd.DataFrame(rows)


def optional_provider_available() -> bool:
    try:
        import soccerdata  # noqa: F401
    except Exception:
        return False
    return True


def explicit_fetch_available(root: Path = ROOT) -> bool:
    return (root / "scripts" / "fetch_understat_xg_source.py").exists()


def recommendation(table: pd.DataFrame, provider_available: bool = False, fetch_available: bool = True) -> str:
    if not table.empty:
        existing = table[table["kind"].eq("existing_normalized")]
        raw = table[table["kind"].eq("raw_understat")]
        if existing["status"].eq("READY").any() if not existing.empty else False:
            return "READY_FOR_TRUSTED_XG_INTAKE"
        if not raw.empty:
            return "FIX_UNDERSTAT_RAW_PARSE"
    if provider_available:
        return "TRY_UNDERSTAT_OPTIONAL_PROVIDER"
    if table.empty:
        return "TRY_UNDERSTAT_LOCAL_EXPORT"
    if fetch_available:
        return "TRY_UNDERSTAT_EXPLICIT_FETCH"
    return "ADD_UNDERSTAT_XG_SOURCE_FILE"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 40) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ";") for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str, provider_available: bool, fetch_available: bool) -> str:
    existing = table[table["kind"].eq("existing_normalized")] if not table.empty else pd.DataFrame()
    raw = table[table["kind"].eq("raw_understat")] if not table.empty else pd.DataFrame()
    blocked = table[~table["status"].isin(["READY", "RAW_PARSE_READY"])] if not table.empty else pd.DataFrame()
    cols = ["file", "kind", "rows", "status", "access_label", "error"]
    lines = [
        "# Phase 13.7 Understat Data Access Audit",
        "",
        "Phase 13.7 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- existing normalized Understat sources: {len(existing)}",
        f"- raw Understat files: {len(raw)}",
        f"- blocked modes/files: {len(blocked)}",
        f"- optional provider available: {provider_available}",
        f"- explicit fetch CLI available: {fetch_available}",
        "",
        "## B. Existing Normalized Understat Sources",
    ]
    lines += _section_table(existing, cols)
    lines += ["## C. Raw Understat Files"]
    lines += _section_table(raw, cols)
    lines += [
        "## D. Available Data Access Modes",
        "- existing: scans data/trusted_xg_sources/*understat*.csv",
        "- local: requires --source path/to/local_export.csv",
        "- raw: scans data/trusted_xg_sources/raw/*understat*",
        f"- optional_provider: {'available' if provider_available else 'unavailable unless soccerdata is installed'}",
        f"- explicit_fetch: {'available through scripts/fetch_understat_xg_source.py' if fetch_available else 'unavailable'}",
        "",
        "## E. Blocked Modes",
    ]
    lines += _section_table(blocked, cols)
    lines += [
        "## F. Recommended Next Commands",
        "```powershell",
        "python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --source path/to/understat_export.csv --output-name understat_xg_bundesliga_2024.csv",
        "python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --allow-optional-provider --output-name understat_xg_bundesliga_2024.csv",
        "python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --allow-network --mode explicit_fetch --output-name understat_xg_bundesliga_2024.csv",
        "python scripts/audit_understat_data_access.py",
        "python scripts/audit_understat_xg_source.py",
        "python scripts/audit_trusted_xg_intake.py --write-command-list",
        "python scripts/show_trusted_xg_intake_commands.py",
        "```",
        "",
        "## G. Safety Checks",
        "- No xG values inferred, invented, estimated from scores, odds, shots, standings, or model output.",
        "- No hidden crawling, credentials, API keys, browser automation, model behavior changes, or betting logic changes.",
        "- Runtime network access only happens when a user explicitly calls a CLI with --allow-network.",
        "- Raw runtime HTML and payload files should not be committed.",
        "",
        "## H. Phase 13.7 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root)
    provider = optional_provider_available()
    fetch = explicit_fetch_available(root)
    rec = recommendation(table, provider_available=provider, fetch_available=fetch)
    markdown = build_markdown(table, rec, provider, fetch)
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
