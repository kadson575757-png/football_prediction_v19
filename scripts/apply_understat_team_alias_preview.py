# -*- coding: utf-8 -*-
"""Apply reviewed Understat team aliases to a copy-only preview CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_join_diagnostics import _find_col, _resolve  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--alias-map", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_alias_preview"))
    parser.add_argument("--overwrite", action="store_true")
    return parser


def apply_alias_preview(source: str | Path, alias_map: str | Path, output_dir: str | Path, overwrite: bool = False) -> tuple[pd.DataFrame, dict[str, object]]:
    source_path = _resolve(source)
    alias_path = _resolve(alias_map)
    df = pd.read_csv(source_path, low_memory=False)
    aliases = pd.read_csv(alias_path, low_memory=False)
    required = {"source_team", "target_team", "alias_status"}
    missing = required.difference(aliases.columns)
    if missing:
        raise ValueError("ALIAS_MAP_MISSING_COLUMNS=" + ",".join(sorted(missing)))
    accepted = aliases[aliases["alias_status"].astype(str).str.strip().str.lower().eq("accepted")].copy()
    mapping = dict(zip(accepted["source_team"].astype(str).str.strip(), accepted["target_team"].astype(str).str.strip()))
    home_col = _find_col(df, "home_team", "HomeTeam", "home")
    away_col = _find_col(df, "away_team", "AwayTeam", "away")
    if not home_col or not away_col:
        raise ValueError("SOURCE_MISSING_TEAM_COLUMNS")
    out = df.copy()
    before_home = out[str(home_col)].copy()
    before_away = out[str(away_col)].copy()
    out[str(home_col)] = out[str(home_col)].replace(mapping)
    out[str(away_col)] = out[str(away_col)].replace(mapping)
    rows_changed = int(((before_home != out[str(home_col)]) | (before_away != out[str(away_col)])).sum())
    teams_changed = sorted(set(before_home[before_home != out[str(home_col)]].astype(str)).union(set(before_away[before_away != out[str(away_col)]].astype(str))))
    root = _resolve(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    output = (root / f"{source_path.stem}_understat_alias_preview.csv").resolve()
    if root.resolve() not in output.parents:
        raise ValueError("Alias preview output must stay under output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    if output == source_path.resolve():
        raise ValueError("Alias preview must not overwrite source")
    out.to_csv(output, index=False)
    return out, {"rows_changed": rows_changed, "teams_changed": teams_changed, "output_path": str(output)}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _df, summary = apply_alias_preview(args.source, args.alias_map, args.output_dir, overwrite=args.overwrite)
    print(f"rows_changed={summary['rows_changed']}")
    print(f"teams_changed={','.join(summary['teams_changed'])}")
    print(f"output_path={summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
