# -*- coding: utf-8 -*-
"""Bridge provider match finder selected match into manual input CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.manual_human_match_input import ALL_COLUMNS  # noqa: E402

MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY = "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY"
MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_MISSING_SELECTED_MATCH = "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_MISSING_SELECTED_MATCH"
MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH = "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH"
MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING = "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-match", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_manual_input_from_provider_match_finder_preview(*, selected_match: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "manual_input", base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    out = _safe_output_dir(output_dir, base)
    if out is None:
        return _summary(MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH)
    source = _default_selected_match(base) if selected_match is None else Path(selected_match)
    if not source.is_absolute():
        source = base / source
    if not source.exists() or not _under(source, base, "outputs/provider_pull_preview/match_finder"):
        return _summary(MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_MISSING_SELECTED_MATCH)
    frame = pd.read_csv(source, low_memory=False)
    if frame.empty:
        return _summary(MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_MISSING_SELECTED_MATCH)
    row = frame.iloc[0]
    manual = _manual_row(row)
    out.mkdir(parents=True, exist_ok=True)
    output = out / "manual_input_from_provider_match_finder_preview.csv"
    pd.DataFrame([manual], columns=ALL_COLUMNS).to_csv(output, index=False)
    optional_missing = any(str(manual.get(column, "")).strip() == "" for column in ["home_xg", "away_xg", "home_xga", "away_xga"])
    status = MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING if optional_missing else MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY
    return _summary(status, provider_match_id=str(row.get("provider_match_id", "")), rows_written=1, output_path=str(output.resolve()), recommendation=MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY if status == MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY else status)


def _manual_row(row: pd.Series) -> dict[str, object]:
    values = {column: "" for column in ALL_COLUMNS}
    values.update({
        "source_id": "provider_match_finder_preview",
        "provider_match_id": row.get("provider_match_id", ""),
        "league": row.get("league", ""),
        "season": row.get("season", ""),
        "match_date": row.get("match_date", ""),
        "date": row.get("match_date", ""),
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "home_goals": row.get("home_goals", ""),
        "away_goals": row.get("away_goals", ""),
        "match_status": "finished",
        "venue": row.get("venue", ""),
        "neutral_venue": row.get("neutral_venue", ""),
        "home_xg": row.get("home_xg", ""),
        "away_xg": row.get("away_xg", ""),
        "home_xga": row.get("home_xga", ""),
        "away_xga": row.get("away_xga", ""),
        "data_quality_notes": row.get("match_finder_warning", ""),
    })
    return values


def _default_selected_match(base: Path) -> Path:
    return base / "outputs" / "provider_pull_preview" / "match_finder" / "provider_match_finder_selected_match.csv"


def _safe_output_dir(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "manual_input").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _under(path: str | Path, base: Path, rel: str) -> bool:
    resolved = Path(path).resolve()
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _summary(status: str, *, provider_match_id: str = "", rows_written: int = 0, output_path: str = "", recommendation: str | None = None) -> dict[str, object]:
    return {
        "manual_input_bridge_status": status,
        "provider_match_id": provider_match_id,
        "rows_written": rows_written,
        "output_path": output_path,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "recommendation": recommendation or status,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_manual_input_from_provider_match_finder_preview(selected_match=args.selected_match, output_dir=args.output_dir, base_dir=args.base_dir)
    for key in ["manual_input_bridge_status", "provider_match_id", "rows_written", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
