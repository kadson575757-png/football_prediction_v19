# -*- coding: utf-8 -*-
"""Apply reviewed Understat date alignments to a copy-only preview CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_join_diagnostics import _find_col, _norm_team, _parse_date, _resolve  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--date-map", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_date_alignment_preview"))
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _accepted_alignments(date_map: pd.DataFrame) -> pd.DataFrame:
    required = {"home_team", "away_team", "source_date", "target_date", "alignment_status"}
    missing = required.difference(date_map.columns)
    if missing:
        raise ValueError("DATE_ALIGNMENT_MAP_MISSING_COLUMNS=" + ",".join(sorted(missing)))
    accepted = date_map[date_map["alignment_status"].astype(str).str.strip().str.lower().eq("accepted")].copy()
    if accepted.empty:
        return accepted
    accepted["home_team_norm"] = accepted["home_team"].map(_norm_team).str.lower()
    accepted["away_team_norm"] = accepted["away_team"].map(_norm_team).str.lower()
    accepted["source_date_norm"] = _parse_date(accepted["source_date"])
    accepted["target_date_norm"] = _parse_date(accepted["target_date"])
    return accepted


def apply_date_alignment_preview(source: str | Path, date_map: str | Path, output_dir: str | Path, overwrite: bool = False) -> tuple[pd.DataFrame, dict[str, object]]:
    source_path = _resolve(source)
    date_map_path = _resolve(date_map)
    df = pd.read_csv(source_path, low_memory=False)
    alignments = _accepted_alignments(pd.read_csv(date_map_path, low_memory=False))
    date_col = _find_col(df, "date", "Date")
    home_col = _find_col(df, "home_team", "HomeTeam", "home")
    away_col = _find_col(df, "away_team", "AwayTeam", "away")
    if not all([date_col, home_col, away_col]):
        raise ValueError("SOURCE_MISSING_JOIN_COLUMNS")
    out = df.copy()
    out_dates = _parse_date(out[str(date_col)])
    home_norm = out[str(home_col)].map(_norm_team).str.lower()
    away_norm = out[str(away_col)].map(_norm_team).str.lower()
    rows_aligned = 0
    used = set()
    for idx, alignment in alignments.iterrows():
        mask = (
            home_norm.eq(alignment["home_team_norm"])
            & away_norm.eq(alignment["away_team_norm"])
            & out_dates.eq(alignment["source_date_norm"])
        )
        if mask.any():
            out.loc[mask, str(date_col)] = alignment["target_date_norm"]
            rows_aligned += int(mask.sum())
            used.add(idx)
    unused = int(len(alignments) - len(used))
    root = _resolve(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    output = (root / f"{source_path.stem}_understat_date_alignment_preview.csv").resolve()
    if root.resolve() not in output.parents:
        raise ValueError("Date alignment preview output must stay under output_dir")
    if output == source_path.resolve():
        raise ValueError("Date alignment preview must not overwrite source")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    out.to_csv(output, index=False)
    return out, {"rows_date_aligned": rows_aligned, "unused_accepted_alignments": unused, "output_path": str(output)}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _df, summary = apply_date_alignment_preview(args.source, args.date_map, args.output_dir, overwrite=args.overwrite)
    print(f"rows_date_aligned={summary['rows_date_aligned']}")
    print(f"unused_accepted_alignments={summary['unused_accepted_alignments']}")
    print(f"output_path={summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
