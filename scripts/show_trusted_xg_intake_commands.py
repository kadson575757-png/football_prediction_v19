# -*- coding: utf-8 -*-
"""Print next PowerShell commands for trusted xG source intake."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_intake import build_trusted_xg_intake_report  # noqa: E402


def _quote(path: str) -> str:
    return f'"{path}"'


def build_commands(source: str, target: str, league: str | None = None, season: str | None = None) -> list[str]:
    template_output = "outputs/xg_entry_templates"
    fill_output = "outputs/xg_fill_preview"
    acceptance_output = "outputs/xg_acceptance_preview"
    promotion_output = "outputs/xg_promotion_preview"
    template_preview = f"{template_output}/{Path(target).stem}_manual_xg_entry_template.csv"
    filled_preview = f"{fill_output}/{Path(source).stem}__to__{Path(target).stem}_filled_manual_xg_preview.csv"
    optional = ""
    if league:
        optional += f" --league {_quote(league)}"
    if season:
        optional += f" --season {_quote(season)}"
    return [
        f"python scripts/generate_manual_xg_template.py --source {_quote(target)} --output-dir {_quote(template_output)}{optional}",
        f"python scripts/fill_manual_xg_from_trusted_source.py --source {_quote(source)} --template {_quote(template_preview)} --target {_quote(target)} --output-dir {_quote(fill_output)}",
        f"python scripts/validate_filled_manual_xg.py --xg {_quote(filled_preview)} --target {_quote(target)} --output-dir {_quote(acceptance_output)}",
        f"python scripts/promote_trusted_xg_to_manifest.py --source-xg {_quote(source)} --template-source {_quote(target)} --target {_quote(target)} --output-dir {_quote(promotion_output)}",
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=str(ROOT / "data" / "trusted_xg_sources"))
    parser.add_argument("--target", default=None)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table = build_trusted_xg_intake_report(Path(args.source_dir))
    usable = table[table["source_path"].astype(str).ne("")] if not table.empty else table
    if usable.empty:
        print("No trusted xG source CSV found.")
        print(f"Place a real trusted xG source CSV in: {args.source_dir}")
        print("Expected match-pair columns: date, home_team, away_team, home_xg, away_xg")
        print("Then run: python scripts/audit_trusted_xg_intake.py --write-command-list")
        return 0
    row = usable.sort_values(["best_fill_coverage_pct", "best_rows_filled"], ascending=False).iloc[0]
    source = str(row["source_path"])
    target = args.target or str(row["best_target_path"])
    if not target:
        print(f"Trusted source found: {source}")
        print("No compatible target match was found. Check date/home/away naming and run the intake audit.")
        return 0
    for command in build_commands(source, target, league=args.league, season=args.season):
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
