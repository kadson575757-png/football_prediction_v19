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

from football_prediction_v19.analysis.v19_batch_completion_campaign_preview import V19BatchCompletionCampaignBuilder, V19BatchCompletionCampaignConfig  # noqa: E402


def build_v19_batch_completion_campaign_preview(**kwargs: object) -> dict[str, object]:
    return V19BatchCompletionCampaignBuilder(V19BatchCompletionCampaignConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-results-json", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_batch_completion_campaign"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = build_v19_batch_completion_campaign_preview(batch_results_json=args.batch_results_json, output_dir=args.output_dir, emit_all=args.emit_all, base_dir=args.base_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
