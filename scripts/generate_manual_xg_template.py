# -*- coding: utf-8 -*-
"""Generate a fillable blank manual xG entry template from fixtures/history."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_template_generator import generate_manual_xg_entry_template  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", default="outputs/xg_entry_templates")
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--no-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = generate_manual_xg_entry_template(
        args.source,
        output_dir=args.output_dir,
        league=args.league,
        season=args.season,
        write_template=not args.no_write,
    )
    print(f"rows_source={result.rows_source}")
    print(f"rows_template={result.rows_template}")
    print(f"duplicate_keys_removed={result.duplicate_keys_removed}")
    print(f"missing_identity_rows={result.missing_identity_rows}")
    print(f"template_quality_label={result.template_quality_label}")
    print(f"output_path={result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
