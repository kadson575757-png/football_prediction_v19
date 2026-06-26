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

from football_prediction_v19.analysis.v19_final_pipeline_preview import V19FinalPipelineConfig, V19FinalPipelineRunner  # noqa: E402


def run_v19_final_pipeline_preview(**kwargs: object) -> dict[str, object]:
    return V19FinalPipelineRunner(V19FinalPipelineConfig(**kwargs)).run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-input-dir")
    parser.add_argument("--match-pack-manifest")
    parser.add_argument("--batch-config")
    parser.add_argument("--single-match-input-dir")
    parser.add_argument("--home-team", default="")
    parser.add_argument("--away-team", default="")
    parser.add_argument("--competition", default="")
    parser.add_argument("--season", default="")
    parser.add_argument("--match-date", default="")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_final_pipeline"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v19_final_pipeline_preview(**vars(args))
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
