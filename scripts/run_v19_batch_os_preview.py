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

from football_prediction_v19.analysis.v19_batch_operating_system_preview import V19BatchOSConfig, V19BatchOSRunner  # noqa: E402


def run_v19_batch_os_preview(**kwargs: object) -> dict[str, object]:
    return V19BatchOSRunner(V19BatchOSConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-config", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_batch_os"))
    parser.add_argument("--preflight-validation-json")
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--skip-scenario-batch-lab", action="store_true", default=False)
    parser.add_argument("--skip-empty-rerun", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v19_batch_os_preview(
        batch_config=args.batch_config,
        output_dir=args.output_dir,
        preflight_validation_json=args.preflight_validation_json,
        emit_all=args.emit_all,
        skip_scenario_batch_lab=args.skip_scenario_batch_lab,
        skip_empty_rerun=args.skip_empty_rerun,
        strict=args.strict,
        base_dir=args.base_dir,
    )
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
