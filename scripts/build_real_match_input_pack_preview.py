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

from football_prediction_v19.analysis.real_match_input_pack_preview import RealMatchInputPackBuilder, RealMatchInputPackConfig  # noqa: E402


def build_real_match_input_pack_preview(**kwargs: object) -> dict[str, object]:
    return RealMatchInputPackBuilder(RealMatchInputPackConfig(**kwargs)).run().__dict__


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-match-intake", default=None)
    parser.add_argument("--manual-key-generation-enabled", action="store_true", default=True)
    parser.add_argument("--output-dir", default="outputs/analysis_preview/real_match_input_pack")
    args = parser.parse_args()
    summary = build_real_match_input_pack_preview(
        real_match_intake_path=args.real_match_intake,
        manual_key_generation_enabled=args.manual_key_generation_enabled,
        output_dir=args.output_dir,
        base_dir=ROOT,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
