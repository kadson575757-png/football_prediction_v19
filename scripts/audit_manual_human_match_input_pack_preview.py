# -*- coding: utf-8 -*-
"""Audit Phase 17.1 manual human match input pack preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.manual_human_match_input import (  # noqa: E402
    ALL_COLUMNS,
    MANUAL_HUMAN_MATCH_INPUT_BETTING_DISABLED_BY_DESIGN,
    MANUAL_HUMAN_MATCH_INPUT_EXAMPLE_READY,
    MANUAL_HUMAN_MATCH_INPUT_MODEL_DISABLED_BY_DESIGN,
    MANUAL_HUMAN_MATCH_INPUT_NETWORK_DISABLED_BY_DESIGN,
    MANUAL_HUMAN_MATCH_INPUT_TEMPLATE_READY,
    MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY,
    ManualHumanMatchInputConfig,
    ManualHumanMatchInputTemplateBuilder,
    ManualHumanMatchInputValidator,
)

MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW_READY = "MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW_READY"
FIX_MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW = "FIX_MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW"
OUTPUT_CSV = "manual_human_match_input_pack_preview_summary.csv"
OUTPUT_MD = "manual_human_match_input_pack_preview_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_preview" / "manual_input"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def audit_preview(*, preview_dir: str | Path, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    preview = Path(preview_dir)
    if not preview.is_absolute():
        preview = base / preview
    builder = ManualHumanMatchInputTemplateBuilder(ManualHumanMatchInputConfig(output_dir=preview, base_dir=base))
    safe_preview = builder.output_dir()
    template = preview / "manual_human_match_input_template.csv"
    example = preview / "manual_human_match_input_example.csv"
    errors: list[str] = []
    if safe_preview is None:
        errors.append("UNSAFE_PREVIEW_PATH")
    if not template.exists():
        errors.append("TEMPLATE_MISSING")
    if not example.exists():
        errors.append("EXAMPLE_MISSING")

    template_columns_ok = False
    example_columns_ok = False
    validation_summary: dict[str, Any] = {}
    if template.exists():
        template_frame = pd.read_csv(template, low_memory=False)
        template_columns_ok = list(template_frame.columns) == ALL_COLUMNS
    if example.exists():
        example_frame = pd.read_csv(example, low_memory=False)
        example_columns_ok = set(ALL_COLUMNS).issubset(example_frame.columns)
        validator = ManualHumanMatchInputValidator(ManualHumanMatchInputConfig(input_path=example, output_dir=preview, base_dir=base))
        result, _frame = validator.validate()
        validation_summary = result.__dict__
        if result.validation_status != MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY:
            errors.append("EXAMPLE_VALIDATION_NOT_READY")
    if not template_columns_ok:
        errors.append("TEMPLATE_COLUMNS_INVALID")
    if not example_columns_ok:
        errors.append("EXAMPLE_COLUMNS_INVALID")
    for key in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled"]:
        if _as_bool(validation_summary.get(key, True)):
            errors.append(key.upper())

    preview_valid = not errors
    return {
        "template_status": MANUAL_HUMAN_MATCH_INPUT_TEMPLATE_READY if template.exists() and template_columns_ok else "",
        "example_status": MANUAL_HUMAN_MATCH_INPUT_EXAMPLE_READY if example.exists() and example_columns_ok else "",
        "validation_status": validation_summary.get("validation_status", ""),
        "template_path": str(template.resolve()) if template.exists() else "",
        "example_path": str(example.resolve()) if example.exists() else "",
        "rows_valid": int(validation_summary.get("rows_valid", 0) or 0),
        "network_calls_enabled": _as_bool(validation_summary.get("network_calls_enabled", True)),
        "prediction_logic_enabled": _as_bool(validation_summary.get("prediction_logic_enabled", True)),
        "betting_logic_enabled": _as_bool(validation_summary.get("betting_logic_enabled", True)),
        "preview_valid": preview_valid,
        "blocking_reasons": " | ".join(errors),
        "recommendation": MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW_READY if preview_valid else FIX_MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW,
    }


def run(*, preview_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "manual_input", output_dir: str | Path = ROOT / "outputs" / "diagnostics", base_dir: str | Path = ROOT) -> tuple[pd.DataFrame, str, str]:
    row = audit_preview(preview_dir=preview_dir, base_dir=base_dir)
    table = pd.DataFrame([row])
    rec = str(row["recommendation"])
    markdown = "\n".join([
        "# Phase 17.1 Manual Human Match Input Pack Preview Audit",
        "",
        f"- preview_valid: {str(row['preview_valid']).lower()}",
        f"- rows_valid: {row['rows_valid']}",
        f"- recommendation: {rec}",
        "",
        "## Safety",
        f"- {MANUAL_HUMAN_MATCH_INPUT_NETWORK_DISABLED_BY_DESIGN}",
        f"- {MANUAL_HUMAN_MATCH_INPUT_MODEL_DISABLED_BY_DESIGN}",
        f"- {MANUAL_HUMAN_MATCH_INPUT_BETTING_DISABLED_BY_DESIGN}",
        "- Manual optional context is never inferred or invented.",
        "",
    ])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
