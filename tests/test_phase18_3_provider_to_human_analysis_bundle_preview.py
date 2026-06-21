from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_provider_to_human_analysis_bundle_preview as audit_bundle  # noqa: E402
import build_provider_to_human_analysis_bundle_preview as build_bundle  # noqa: E402
import build_provider_to_human_analysis_bundle_preview_helper as helper  # noqa: E402
from football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview import (  # noqa: E402
    MANIFEST_COLUMNS,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_HUMAN_PIPELINE,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MANUAL_BRIDGE,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_UNSAFE_PATH,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_VALIDATION,
    PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY,
    ProviderToHumanAnalysisBundleConfig,
    ProviderToHumanAnalysisBundleRunner,
)

ALIASES = ROOT / "tests" / "fixtures" / "team_aliases" / "team_alias_registry_preview.csv"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build(root: Path, **kwargs):
    return build_bundle.build_provider_to_human_analysis_bundle_preview(
        output_dir=root / "outputs" / "analysis_preview" / "provider_to_human_bundle",
        base_dir=root,
        **kwargs,
    )


def test_builds_provider_to_human_analysis_bundle_preview_from_understat_fixture(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id="u-bundesliga-2024-001")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert summary["provider_pull_status"] == "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY"
    assert summary["match_finder_status"] == "PROVIDER_MATCH_FINDER_PREVIEW_READY"
    assert summary["manual_input_bridge_status"] == "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY"
    assert summary["validation_status"] == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"
    assert summary["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"


def test_supports_provider_match_id_selection(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id="u-bundesliga-2024-002")

    assert summary["provider_match_id"] == "u-bundesliga-2024-002"
    assert summary["home_team"] == "North FC"


def test_supports_home_away_team_selection(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id=None, home_team="Home FC", away_team="Away FC")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert summary["provider_match_id"] == "u-bundesliga-2024-001"


def test_supports_alias_registry_selection(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id=None, home_team="Home-F.C.", away_team="Away Football Club", alias_registry=ALIASES)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert summary["provider_match_id"] == "u-bundesliga-2024-001"


def test_supports_optional_match_date_filtering(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id=None, home_team="Home FC", away_team="Away FC", match_date="2024-08-23")

    assert summary["match_date"] == "2024-08-23"
    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY


def test_blocks_unknown_match(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id=None, home_team="Missing FC", away_team="Away FC")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER
    assert summary["match_finder_status"] == "PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH"


def test_blocks_ambiguous_match(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id=None, league="Bundesliga")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER
    assert summary["match_finder_status"] == "PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH"


def test_blocks_unsafe_output_paths(tmp_path):
    root = tmp_path / "repo"

    result, _steps = ProviderToHumanAnalysisBundleRunner(
        ProviderToHumanAnalysisBundleConfig(output_dir=root / "outputs" / "not_bundle", base_dir=root)
    ).run()

    assert result.bundle_status == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_UNSAFE_PATH


def test_blocks_missing_provider_pull_output_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id="u-bundesliga-2024-001", build_missing=False)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL


def test_propagates_provider_pull_failure(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider="unknown_provider")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL


def test_propagates_match_finder_failure(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id="missing")

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER


def test_propagates_manual_bridge_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"

    def fake_bridge(**_kwargs):
        return {"manual_input_bridge_status": "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_BLOCKED_MISSING_SELECTED_MATCH", "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False}

    monkeypatch.setattr("football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview.build_manual_input_from_provider_match_finder_preview", fake_bridge)
    summary = _build(root)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MANUAL_BRIDGE


def test_propagates_validation_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"

    class FakeValidator:
        def __init__(self, *_args, **_kwargs):
            pass

        def validate(self):
            class Result:
                __dict__ = {"validation_status": "MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES", "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "recommendation": "bad", "notes": ""}

            return Result(), pd.DataFrame()

        def write_outputs(self, _result):
            return {}

    monkeypatch.setattr("football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview.ManualHumanMatchInputValidator", FakeValidator)
    summary = _build(root)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_VALIDATION


def test_propagates_human_pipeline_failure(monkeypatch, tmp_path):
    root = tmp_path / "repo"

    def fake_pipeline(**_kwargs):
        return {"human_match_pipeline_status": "HUMAN_MATCH_PIPELINE_BLOCKED_IMPORTER", "rows_reported": 0, "steps_failed": 1, "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False}

    monkeypatch.setattr("football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview.build_pipeline_from_manual_input", fake_pipeline)
    summary = _build(root)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_HUMAN_PIPELINE


def test_does_not_infer_missing_optional_values(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root, provider_match_id="u-bundesliga-2024-001")
    step_summary = pd.read_csv(summary["step_summary_path"], low_memory=False)

    assert summary["bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert "provider_pull" in set(step_summary["step_name"])


def test_writes_manifest_step_summary_and_markdown_under_bundle_preview_dir(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root)
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)

    for key in ["manifest_path", "step_summary_path", "summary_path"]:
        path = Path(summary[key]).resolve()
        assert (root / "outputs" / "analysis_preview" / "provider_to_human_bundle").resolve() in path.parents
        assert path.exists()
    assert set(MANIFEST_COLUMNS).issubset(manifest.columns)


def test_final_human_report_exists(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root)

    assert Path(summary["final_report_path"]).exists()


def test_audit_and_helper_return_ready(tmp_path):
    root = tmp_path / "repo"

    table, _markdown, rec = audit_bundle.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)
    helper_summary = helper.run_workflow(root)

    assert rec == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert bool(table.iloc[0]["preview_valid"])
    assert helper_summary["provider_to_human_bundle_status"] == PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY
    assert helper_summary["rows_reported"] == 1
    assert helper_summary["steps_failed"] == 0


def test_safety_flags_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = _build(root)

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False


def test_no_live_scraping_provider_or_network_calls_occur():
    files = [
        ROOT / "src" / "football_prediction_v19" / "analysis" / "provider_to_human_analysis_bundle_preview.py",
        ROOT / "scripts" / "build_provider_to_human_analysis_bundle_preview.py",
        ROOT / "scripts" / "audit_provider_to_human_analysis_bundle_preview.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text


def test_no_production_target_source_accepted_artifact_or_manifest_is_modified(tmp_path):
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

    helper.run_workflow(root)

    assert {path: _sha(path) for path in protected} == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}

    helper.run_workflow(tmp_path / "repo")

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
