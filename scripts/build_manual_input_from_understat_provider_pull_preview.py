# -*- coding: utf-8 -*-
"""Bridge normalized Understat provider preview rows into manual match input CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.manual_human_match_input import ALL_COLUMNS  # noqa: E402

MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY = "MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY"
MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_NORMALIZED_INPUT = "MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_NORMALIZED_INPUT"
MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNKNOWN_MATCH_ID = "MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNKNOWN_MATCH_ID"
MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH = "MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH"
MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING = "MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-input", default=None)
    parser.add_argument("--match-id", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_manual_input_from_understat_provider_pull_preview(*, normalized_input: str | Path | None = None, match_id: str | None = None, output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "manual_input", base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    out = _safe_output_dir(output_dir, base)
    if out is None:
        return _summary(MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNSAFE_PATH)
    source = _default_normalized_path(base) if normalized_input is None else Path(normalized_input)
    if not source.is_absolute():
        source = base / source
    if not source.exists() or not _under(source, base, "outputs/provider_pull_preview/understat/normalized"):
        return _summary(MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_NORMALIZED_INPUT)
    frame = pd.read_csv(source, low_memory=False)
    if frame.empty:
        return _summary(MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_MISSING_NORMALIZED_INPUT)
    selected = frame
    if match_id:
        selected = frame[frame["provider_match_id"].astype(str) == str(match_id)]
        if selected.empty:
            return _summary(MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_BLOCKED_UNKNOWN_MATCH_ID, source_rows=len(frame), provider_match_id=match_id)
    row = selected.iloc[0]
    manual = _manual_row(row)
    out.mkdir(parents=True, exist_ok=True)
    output = out / "manual_input_from_understat_provider_pull_preview.csv"
    pd.DataFrame([manual], columns=ALL_COLUMNS).to_csv(output, index=False)
    optional_missing = any(str(manual.get(column, "")).strip() == "" for column in ["home_xg", "away_xg", "home_xga", "away_xga"])
    status = MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_OPTIONAL_VALUES_MISSING if optional_missing else MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY
    return _summary(status, source_rows=len(frame), rows_written=1, provider_match_id=str(row.get("provider_match_id", "")), output_path=str(output.resolve()), recommendation=MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY if status == MANUAL_INPUT_FROM_UNDERSTAT_PROVIDER_PULL_READY else status)


def _manual_row(row: pd.Series) -> dict[str, object]:
    values = {column: "" for column in ALL_COLUMNS}
    values.update({
        "source_id": "understat_provider_pull_preview",
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
        "data_quality_notes": row.get("normalization_warning", ""),
    })
    return values


def _default_normalized_path(base: Path) -> Path:
    normalized_dir = base / "outputs" / "provider_pull_preview" / "understat" / "normalized"
    matches = sorted(normalized_dir.glob("*_normalized_preview.csv"))
    return matches[0] if matches else normalized_dir / "understat_normalized_preview.csv"


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


def _summary(status: str, *, source_rows: int = 0, rows_written: int = 0, provider_match_id: str = "", output_path: str = "", recommendation: str | None = None) -> dict[str, object]:
    return {
        "manual_input_bridge_status": status,
        "source_rows": source_rows,
        "rows_written": rows_written,
        "provider_match_id": provider_match_id,
        "output_path": output_path,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "recommendation": recommendation or status,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_manual_input_from_understat_provider_pull_preview(normalized_input=args.normalized_input, match_id=args.match_id, output_dir=args.output_dir, base_dir=args.base_dir)
    for key in ["manual_input_bridge_status", "source_rows", "rows_written", "provider_match_id", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
