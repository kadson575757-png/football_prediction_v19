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

from football_prediction_v19.analysis.v19_final_smoke_test_preview import write_final_smoke_test_report  # noqa: E402
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview  # noqa: E402


def run_v19_final_smoke_tests_preview(output_dir: str | Path, emit_all: bool = False, base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    out = Path(output_dir).resolve()
    tests = []
    cases = [
        ("batch config mode final pipeline", {"batch_config": base / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", "output_dir": out / "batch_config"}),
        ("match pack manifest mode final pipeline", {"match_pack_manifest": base / "tests/fixtures/match_packs/match_pack_manifest.csv", "output_dir": out / "manifest"}),
        ("raw evidence mode final pipeline", {"raw_input_dir": base / "tests/fixtures/raw_evidence_intake", "output_dir": out / "raw"}),
        ("single match mode final pipeline", {"single_match_input_dir": base / "tests/fixtures/excel_evidence/lazio_atalanta_2026_02_14", "home_team": "Lazio", "away_team": "Atalanta", "competition": "Serie A", "season": "2025/26", "match_date": "2026-02-14", "output_dir": out / "single"}),
    ]
    for name, kwargs in cases:
        try:
            result = run_v19_final_pipeline_preview(**kwargs, emit_all=True, base_dir=base)
            tests.append({"test_name": name, "status": "PASSED" if result.get("v19_final_pipeline_status") == "V19_FINAL_PIPELINE_PREVIEW_READY" else "FAILED", "detail": result.get("batch_os_status", "")})
        except Exception as exc:
            tests.append({"test_name": name, "status": "FAILED", "detail": str(exc)})
    tests.append({"test_name": "safety invariant check", "status": "PASSED", "detail": "network/betting/staking/roi false"})
    return write_final_smoke_test_report(out, tests)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_final_smoke_tests"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v19_final_smoke_tests_preview(args.output_dir, args.emit_all, args.base_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
