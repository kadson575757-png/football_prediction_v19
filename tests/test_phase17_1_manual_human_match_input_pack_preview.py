from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_manual_human_match_input_pack_preview as audit_pack  # noqa: E402
import build_human_match_pipeline_from_manual_input_preview as pipeline_from_manual  # noqa: E402
import build_manual_human_match_input_pack_preview as build_pack  # noqa: E402
import build_manual_human_match_input_pack_preview_helper as helper  # noqa: E402
import validate_manual_human_match_input as validate_script  # noqa: E402
from football_prediction_v19.analysis.manual_human_match_input import (  # noqa: E402
    ALL_COLUMNS,
    MANUAL_HUMAN_MATCH_INPUT_BLOCKED_DUPLICATE_MATCH_IDS,
    MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES,
    MANUAL_HUMAN_MATCH_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS,
    MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH,
    MANUAL_HUMAN_MATCH_INPUT_EXTRA_COLUMNS_WARNING,
    MANUAL_HUMAN_MATCH_INPUT_OPTIONAL_CONTEXT_MISSING,
    MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY,
    REQUIRED_COLUMNS,
    ManualHumanMatchInputConfig,
    ManualHumanMatchInputTemplateBuilder,
    ManualHumanMatchInputValidator,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _example(root: Path) -> Path:
    summary = build_pack.build_manual_human_match_input_pack_preview(
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )
    return Path(summary["example_path"])


def test_builds_template_and_example_pack(tmp_path):
    root = tmp_path / "repo"

    summary = build_pack.build_manual_human_match_input_pack_preview(
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert Path(summary["template_path"]).exists()
    assert Path(summary["example_path"]).exists()
    assert summary["validation_status"] == MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY
    assert summary["rows_valid"] == 1


def test_template_contains_required_and_optional_columns(tmp_path):
    root = tmp_path / "repo"
    builder = ManualHumanMatchInputTemplateBuilder(
        ManualHumanMatchInputConfig(output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    )

    template = builder.template_frame()

    assert list(template.columns) == ALL_COLUMNS
    for column in REQUIRED_COLUMNS:
        assert column in template.columns


def test_validates_required_non_empty_values(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)
    frame = pd.read_csv(source)
    frame.loc[0, "home_team"] = ""
    frame.to_csv(source, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES
    assert "home_team" in result.empty_required_values


def test_blocks_missing_required_columns(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)
    frame = pd.read_csv(source).drop(columns=["league"])
    frame.to_csv(source, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS
    assert "league" in result.missing_required_columns


def test_reports_duplicate_provider_match_ids(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)
    frame = pd.read_csv(source)
    pd.concat([frame, frame], ignore_index=True).to_csv(source, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_BLOCKED_DUPLICATE_MATCH_IDS
    assert "manual-preview-1" in result.duplicate_match_ids


def test_warns_for_missing_optional_context_without_blocking(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)
    frame = pd.read_csv(source)[REQUIRED_COLUMNS]
    frame.to_csv(source, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY
    assert MANUAL_HUMAN_MATCH_INPUT_OPTIONAL_CONTEXT_MISSING in result.notes


def test_warns_for_extra_columns_without_blocking(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)
    frame = pd.read_csv(source)
    frame["analyst_private_note"] = "review"
    frame.to_csv(source, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY
    assert result.extra_columns_count == 1
    assert MANUAL_HUMAN_MATCH_INPUT_EXTRA_COLUMNS_WARNING in result.notes


def test_blocks_unsafe_output_and_protected_input_paths(tmp_path):
    root = tmp_path / "repo"
    unsafe_output = ManualHumanMatchInputTemplateBuilder(
        ManualHumanMatchInputConfig(output_dir=root / "outputs" / "not_manual_input", base_dir=root)
    ).write()
    protected = root / "data" / "processed" / "manual.csv"
    protected.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{column: "x" for column in REQUIRED_COLUMNS}]).to_csv(protected, index=False)

    result, _frame = ManualHumanMatchInputValidator(
        ManualHumanMatchInputConfig(input_path=protected, output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    ).validate()

    assert unsafe_output["template_status"] == MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH
    assert result.validation_status == MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH


def test_validation_script_writes_summary_manifest_and_markdown(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)

    summary = validate_script.validate_manual_human_match_input(
        input_path=source,
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert summary["validation_status"] == MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY
    assert Path(summary["summary_path"]).exists()
    assert Path(summary["manifest_path"]).exists()
    assert Path(summary["markdown_path"]).exists()


def test_pipeline_from_manual_input_preview_runs(tmp_path):
    root = tmp_path / "repo"
    source = _example(root)

    summary = pipeline_from_manual.build_pipeline_from_manual_input(
        input_path=source,
        output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline",
        write_preview=True,
        base_dir=root,
    )

    assert summary["validation_status"] == MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY
    assert summary["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"
    assert summary["rows_reported"] == 1
    assert summary["steps_failed"] == 0


def test_audit_and_helper_report_ready(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "manual_input")
    table, _markdown, rec = audit_pack.run(
        preview_dir=root / "outputs" / "analysis_preview" / "manual_input",
        output_dir=root / "outputs" / "diagnostics",
        base_dir=root,
    )

    assert summary["manual_human_match_input_pack_status"] == "MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW_READY"
    assert rec == "MANUAL_HUMAN_MATCH_INPUT_PACK_PREVIEW_READY"
    assert bool(table.iloc[0]["preview_valid"])


def test_safety_flags_disabled_by_design(tmp_path):
    root = tmp_path / "repo"
    summary = build_pack.build_manual_human_match_input_pack_preview(
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False


def test_no_live_network_or_scraping_code_added():
    files = [
        ROOT / "src" / "football_prediction_v19" / "analysis" / "manual_human_match_input.py",
        ROOT / "scripts" / "build_manual_human_match_input_pack_preview.py",
        ROOT / "scripts" / "validate_manual_human_match_input.py",
        ROOT / "scripts" / "build_human_match_pipeline_from_manual_input_preview.py",
        ROOT / "scripts" / "audit_manual_human_match_input_pack_preview.py",
    ]
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert not any(token in text for token in forbidden)


def test_no_production_source_target_accepted_raw_or_manifest_files_modified(tmp_path):
    root = tmp_path / "repo"
    protected = [
        root / "data" / "processed" / "target_clean.csv",
        root / "data" / "trusted_xg_sources" / "accepted" / "accepted_xg.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "raw_source.csv",
        root / "data" / "templates" / "manual_xg_manifest_template.csv",
    ]
    for path in protected:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sentinel\n", encoding="utf-8")
    before = {path: _sha(path) for path in protected}

    helper.run_workflow(root / "outputs" / "analysis_preview" / "manual_input")

    assert {path: _sha(path) for path in protected} == before


def test_model_probability_market_and_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}

    helper.run_workflow(tmp_path / "repo" / "outputs" / "analysis_preview" / "manual_input")

    assert {path: _sha(path) for path in protected if path.exists()} == before
