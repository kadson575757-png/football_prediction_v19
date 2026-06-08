# -*- coding: utf-8 -*-
"""Import an explicit trusted xG source export into data/trusted_xg_sources."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_source_import import import_trusted_xg_source  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "trusted_xg_sources"))
    parser.add_argument("--raw-output-dir", default=str(ROOT / "data" / "trusted_xg_sources" / "raw"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = import_trusted_xg_source(
        args.source,
        output_name=args.output_name,
        output_dir=args.output_dir,
        raw_output_dir=args.raw_output_dir,
        overwrite=args.overwrite,
        no_fetch=args.no_fetch,
    )
    print(f"source_type={result.source_type}")
    print(f"rows_read={result.rows_read}")
    print(f"rows_normalized={result.rows_normalized}")
    print(f"output_path={result.output_path}")
    print(f"raw_output_path={result.raw_output_path}")
    print(f"detected_schema={result.detected_schema}")
    print(f"import_label={result.import_label}")
    print(f"validation_errors={' | '.join(result.validation_errors)}")
    print(f"warning_notes={' | '.join(result.warning_notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
