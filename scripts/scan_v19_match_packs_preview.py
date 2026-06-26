# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.v19_match_pack_scanner_preview import V19MatchPackScanner, V19MatchPackScannerConfig  # noqa: E402


def scan_v19_match_packs_preview(**kwargs: object) -> dict[str, object]:
    return V19MatchPackScanner(V19MatchPackScannerConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest")
    parser.add_argument("--root-dir")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_match_pack_scan"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = scan_v19_match_packs_preview(manifest=args.manifest, root_dir=args.root_dir, output_dir=args.output_dir, emit_all=args.emit_all, base_dir=args.base_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
