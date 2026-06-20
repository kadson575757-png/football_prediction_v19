from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_human_match_pipeline_preview as pipeline_audit  # noqa: E402
import build_human_match_pipeline_preview as pipeline_preview  # noqa: E402
import build_human_match_pipeline_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.human_match_pipeline_preview import (  # noqa: E402
    HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT,
    HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH,
    HUMAN_MATCH_PIPELINE_PREVIEW_READY,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_csv(path: Path, match_id: str = "m1") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "source_id": "file_csv",
        "provider_match_id": match_id,
        "league": "Preview League",
        "season": "2024",
        "date": "2024-08-23",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "home_goals": 2,
        "away_goals": 1,
        "match_status": "finished",
    }]).to_csv(path, index=False)
    return path


def _build(tmp_path: Path):
    root = tmp_path / "repo"
    summary = pipeline_preview.build_human_match_pipeline_preview(output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)
    return root, summary, manifest


def test_builds_full_human_match_pipeline_preview(tmp_path):
    _root, summary, _manifest = _build(tmp_path)

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["steps_failed"] == 0


def test_builds_missing_upstream_preview_outputs(tmp_path):
    root, summary, _manifest = _build(tmp_path)

    assert (root / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv").exists()
    assert (root / "outputs" / "analysis_preview" / "human_match_report" / "human_match_analysis_report_preview.md").exists()
    assert summary["steps_checked"] == 5


def test_supports_optional_local_input_csv(tmp_path):
    root = tmp_path / "repo"
    source = _input_csv(root / "local.csv", match_id="custom-1")

    summary = pipeline_preview.build_human_match_pipeline_preview(input_path=source, match_id="custom-1", output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_PREVIEW_READY
    assert summary["provider_match_id"] == "custom-1"


def test_supports_optional_match_id_selection(tmp_path):
    root = tmp_path / "repo"
    source = _input_csv(root / "local.csv", match_id="m42")

    summary = pipeline_preview.build_human_match_pipeline_preview(input_path=source, match_id="m42", output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_PREVIEW_READY
    assert summary["provider_match_id"] == "m42"


def test_blocks_unknown_match_id(tmp_path):
    root = tmp_path / "repo"
    source = _input_csv(root / "local.csv", match_id="m42")

    summary = pipeline_preview.build_human_match_pipeline_preview(input_path=source, match_id="missing", output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT


def test_blocks_unsafe_output_path(tmp_path):
    root = tmp_path / "repo"

    summary = pipeline_preview.build_human_match_pipeline_preview(output_dir=root / "not_outputs", write_preview=True, base_dir=root)

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH


def test_no_missing_values_are_inferred_or_invented(tmp_path):
    root = tmp_path / "repo"
    source = _input_csv(root / "local.csv")
    frame = pd.read_csv(source)
    frame["home_team"] = ""
    frame.to_csv(source, index=False)

    summary = pipeline_preview.build_human_match_pipeline_preview(input_path=source, output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert summary["human_match_pipeline_status"] != HUMAN_MATCH_PIPELINE_PREVIEW_READY


def test_output_paths_are_under_preview_dirs_only(tmp_path):
    root, summary, _manifest = _build(tmp_path)

    for key in ["manifest_path", "step_summary_path", "pipeline_report_path", "final_report_path"]:
        path = Path(summary[key]).resolve()
        assert (root / "outputs" / "analysis_preview").resolve() in path.parents


def test_final_human_report_exists_and_contains_required_preview_safety_no_bet_statements(tmp_path):
    _root, summary, _manifest = _build(tmp_path)
    report = Path(summary["final_report_path"])
    text = report.read_text(encoding="utf-8")

    assert report.exists()
    for fragment in [
        "preview-only human-facing analysis report",
        "No model prediction was run",
        "No betting/staking recommendation was generated",
        "No live external data was fetched",
        "Missing optional context is not inferred or invented",
    ]:
        assert fragment in text


def test_network_prediction_and_betting_logic_are_disabled_by_design(tmp_path):
    _root, summary, manifest = _build(tmp_path)

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False
    assert not manifest["network_calls_enabled"].astype(bool).any()
    assert not manifest["prediction_logic_enabled"].astype(bool).any()
    assert not manifest["betting_logic_enabled"].astype(bool).any()


def test_no_live_scraping_provider_calls_occur():
    text = Path(pipeline_preview.__file__).read_text(encoding="utf-8")
    forbidden = ["req" + "uests.", "url" + "open(", "httpx.", "Beautiful" + "Soup(", "selenium", "playwright"]
    assert not any(token in text for token in forbidden)


def test_audit_returns_human_match_pipeline_preview_ready(tmp_path):
    root, summary, _manifest = _build(tmp_path)

    table, _markdown, rec = pipeline_audit.run(manifest=summary["manifest_path"], output_dir=root / "outputs" / "diagnostics", base_dir=root)

    assert rec == HUMAN_MATCH_PIPELINE_PREVIEW_READY
    assert table.iloc[0]["preview_valid"]


def test_helper_works_on_tiny_fixture_input(monkeypatch, tmp_path):
    root = tmp_path / "repo"
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(root / "outputs" / "analysis_preview" / "human_match_pipeline")

    assert summary["human_match_pipeline_status"] == HUMAN_MATCH_PIPELINE_PREVIEW_READY
    assert summary["rows_reported"] == 1
    assert summary["steps_failed"] == 0


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
    root = tmp_path / "repo"
    files = [
        root / "data" / "processed" / "target_clean.csv",
        root / "data" / "trusted_xg_sources" / "accepted" / "accepted_xg.csv",
        root / "data" / "trusted_xg_sources" / "raw" / "raw_source.csv",
        root / "data" / "templates" / "manual_xg_manifest_template.csv",
    ]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sentinel\n", encoding="utf-8")
    before = {path: _sha(path) for path in files}

    pipeline_preview.build_human_match_pipeline_preview(output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in files} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root = tmp_path / "repo"

    pipeline_preview.build_human_match_pipeline_preview(output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text

