# -*- coding: utf-8 -*-
"""Preview-import a local manual xG CSV.

No source files are modified. No xG values are inferred or invented.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_csv import import_manual_xg_csv  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_import_preview"))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-preview", action="store_true", default=True)
    parser.add_argument("--no-write-preview", action="store_false", dest="write_preview")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = import_manual_xg_csv(
        args.input,
        output_dir=args.output_dir,
        strict=args.strict,
        write_preview=args.write_preview,
    )
    print(f"rows_read={result.rows_read}")
    print(f"rows_valid={result.rows_valid}")
    print(f"rows_invalid={result.rows_invalid}")
    print(f"xg_schema={result.xg_schema}")
    print(f"xg_production_ready={result.xg_production_ready}")
    print(f"output_path={result.output_path}")
    if result.validation_errors:
        print("validation_errors=" + " | ".join(result.validation_errors))
    if result.warning_notes:
        print("warning_notes=" + " | ".join(result.warning_notes))
    return 1 if result.validation_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
