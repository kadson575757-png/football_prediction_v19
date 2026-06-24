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

from football_prediction_v19.analysis.manual_evidence_overlay_preview import ManualEvidenceOverlayBuilder, ManualEvidenceOverlayConfig  # noqa: E402
from scripts.validate_real_match_intake_preview import validate_real_match_intake_preview  # noqa: E402


def build_manual_evidence_overlay_preview(*, input_path: str | Path | None = None, manual_key_generation_enabled: bool = False, output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "manual_evidence_overlay", base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    validation = validate_real_match_intake_preview(
        input_path=input_path,
        manual_key_generation_enabled=manual_key_generation_enabled,
        output_dir=base / "outputs" / "analysis_preview" / "real_match_intake_validation",
        base_dir=base,
    )
    result = ManualEvidenceOverlayBuilder(ManualEvidenceOverlayConfig(input_path=validation.get("output_path"), output_dir=output_dir, base_dir=base)).run().__dict__
    result["real_match_intake_validation_status"] = validation.get("real_match_intake_validation_status", "")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", dest="input_path", required=True)
    parser.add_argument("--manual-key-generation-enabled", action="store_true")
    parser.add_argument("--output-dir", default="outputs/analysis_preview/manual_evidence_overlay")
    args = parser.parse_args()
    summary = build_manual_evidence_overlay_preview(
        input_path=args.input_path,
        manual_key_generation_enabled=args.manual_key_generation_enabled,
        output_dir=args.output_dir,
        base_dir=ROOT,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
