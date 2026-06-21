from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_provider_match_finder_preview as audit_finder  # noqa: E402
import build_human_match_pipeline_from_manual_input_preview as pipeline_from_manual  # noqa: E402
import build_manual_input_from_provider_match_finder_preview as bridge_script  # noqa: E402
import build_provider_match_finder_preview_helper as helper  # noqa: E402
import build_understat_provider_pull_preview as build_understat  # noqa: E402
import find_provider_match_preview as find_script  # noqa: E402
import validate_manual_human_match_input as validate_manual  # noqa: E402
from football_prediction_v19.importers.provider_match_finder_preview import (  # noqa: E402
    MANIFEST_COLUMNS,
    PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH,
    PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT,
    PROVIDER_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS,
    PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH,
    PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH,
    PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING,
    PROVIDER_MATCH_FINDER_PREVIEW_READY,
    ProviderMatchFinderConfig,
    ProviderMatchFinderPreview,
)

FIXTURE = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
ALIASES = ROOT / "tests" / "fixtures" / "team_aliases" / "team_alias_registry_preview.csv"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized(root: Path) -> str:
    summary = build_understat.build_understat_provider_pull_preview(
        league="Bundesliga",
        season="2024",
        input_path=FIXTURE,
        output_dir=root / "outputs" / "provider_pull_preview" / "understat",
        base_dir=root,
    )
    return str(summary["normalized_output_path"])


def _find(root: Path, **kwargs):
    normalized_input = kwargs.pop("normalized_input", None)
    output_dir = kwargs.pop("output_dir", root / "outputs" / "provider_pull_preview" / "match_finder")
    return find_script.find_provider_match_preview(
        normalized_input=normalized_input if normalized_input is not None else _normalized(root),
        output_dir=output_dir,
        base_dir=root,
        build_missing=False,
        **kwargs,
    )


def test_builds_provider_match_finder_preview_from_understat_normalized_fixture_output(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, provider_match_id="u-bundesliga-2024-001")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert summary["provider_match_id"] == "u-bundesliga-2024-001"
    assert summary["candidates_matched"] == 1


def test_finds_match_by_provider_match_id(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, provider_match_id="u-bundesliga-2024-002")

    assert summary["home_team"] == "North FC"
    assert summary["away_team"] == "South FC"


def test_finds_match_by_exact_home_away_team_names(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, home_team="Home FC", away_team="Away FC")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert summary["provider_match_id"] == "u-bundesliga-2024-001"


def test_finds_match_by_case_insensitive_and_punctuation_normalized_names(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, home_team="home-f.c.", away_team="away fc")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert summary["provider_match_id"] == "u-bundesliga-2024-001"


def test_finds_match_by_alias_registry(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, home_team="Home-F.C.", away_team="Away Football Club", alias_registry=ALIASES)

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert summary["alias_match_used"] is True


def test_supports_optional_match_date_filtering(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, home_team="Home FC", away_team="Away FC", match_date="2024-08-23")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert summary["match_date"] == "2024-08-23"


def test_blocks_unknown_match(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, home_team="Missing FC", away_team="Away FC")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_BLOCKED_UNKNOWN_MATCH


def test_blocks_ambiguous_match(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, league="Bundesliga")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_BLOCKED_AMBIGUOUS_MATCH
    assert summary["candidates_matched"] == 2


def test_blocks_missing_normalized_input_when_build_missing_disabled(tmp_path):
    root = tmp_path / "repo"

    summary = find_script.find_provider_match_preview(
        provider_match_id="u-bundesliga-2024-001",
        output_dir=root / "outputs" / "provider_pull_preview" / "match_finder",
        base_dir=root,
        build_missing=False,
    )

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_BLOCKED_MISSING_NORMALIZED_INPUT


def test_blocks_missing_required_normalized_columns(tmp_path):
    root = tmp_path / "repo"
    source = Path(_normalized(root))
    frame = pd.read_csv(source).drop(columns=["home_team"])
    broken = root / "outputs" / "provider_pull_preview" / "understat" / "normalized" / "broken.csv"
    frame.to_csv(broken, index=False)

    summary = _find(root, normalized_input=broken, provider_match_id="u-bundesliga-2024-001")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_BLOCKED_MISSING_REQUIRED_COLUMNS


def test_blocks_unsafe_paths(tmp_path):
    root = tmp_path / "repo"

    summary = _find(root, provider_match_id="u-bundesliga-2024-001", output_dir=root / "outputs" / "not_match_finder")

    assert summary["match_finder_status"] == PROVIDER_MATCH_FINDER_BLOCKED_UNSAFE_PATH


def test_does_not_infer_missing_optional_values(tmp_path):
    root = tmp_path / "repo"
    source = Path(_normalized(root))
    frame = pd.read_csv(source).astype(object)
    frame.loc[0, "home_xg"] = ""
    frame.to_csv(source, index=False)

    summary = _find(root, normalized_input=source, provider_match_id="u-bundesliga-2024-001")
    selected = pd.read_csv(summary["selected_match_output_path"], low_memory=False)

    assert PROVIDER_MATCH_FINDER_OPTIONAL_VALUES_MISSING in selected.iloc[0]["match_finder_warning"]
    assert str(selected.iloc[0]["home_xg"]) in {"", "nan"}


def test_writes_selected_match_manifest_and_markdown_under_preview_dir(tmp_path):
    root = tmp_path / "repo"
    summary = _find(root, provider_match_id="u-bundesliga-2024-001")
    manifest = pd.read_csv(summary["manifest_path"], low_memory=False)

    for key in ["selected_match_output_path", "manifest_path", "summary_path"]:
        assert (root / "outputs" / "provider_pull_preview" / "match_finder").resolve() in Path(summary[key]).resolve().parents
        assert Path(summary[key]).exists()
    assert set(MANIFEST_COLUMNS).issubset(manifest.columns)


def test_bridge_converts_selected_match_into_manual_human_match_input(tmp_path):
    root = tmp_path / "repo"
    summary = _find(root, provider_match_id="u-bundesliga-2024-001")

    bridge = bridge_script.build_manual_input_from_provider_match_finder_preview(
        selected_match=summary["selected_match_output_path"],
        output_dir=root / "outputs" / "analysis_preview" / "manual_input",
        base_dir=root,
    )
    frame = pd.read_csv(bridge["output_path"], low_memory=False)

    assert bridge["manual_input_bridge_status"] == "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY"
    assert bridge["rows_written"] == 1
    assert frame.iloc[0]["provider_match_id"] == "u-bundesliga-2024-001"


def test_generated_manual_input_validates_and_runs_human_pipeline_preview(tmp_path):
    root = tmp_path / "repo"
    finder = _find(root, provider_match_id="u-bundesliga-2024-001")
    bridge = bridge_script.build_manual_input_from_provider_match_finder_preview(selected_match=finder["selected_match_output_path"], output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)

    validation = validate_manual.validate_manual_human_match_input(input_path=bridge["output_path"], output_dir=root / "outputs" / "analysis_preview" / "manual_input", base_dir=root)
    pipeline = pipeline_from_manual.build_pipeline_from_manual_input(input_path=bridge["output_path"], output_dir=root / "outputs" / "analysis_preview" / "human_match_pipeline", base_dir=root)

    assert validation["validation_status"] == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"
    assert pipeline["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"


def test_audit_and_helper_return_provider_match_finder_preview_ready(tmp_path):
    root = tmp_path / "repo"

    table, _markdown, rec = audit_finder.run(output_dir=root / "outputs" / "diagnostics", base_dir=root)
    helper_summary = helper.run_workflow(root)

    assert rec == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert bool(table.iloc[0]["preview_valid"])
    assert helper_summary["provider_match_finder_status"] == PROVIDER_MATCH_FINDER_PREVIEW_READY
    assert helper_summary["manual_input_bridge_status"] == "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY"
    assert helper_summary["validation_status"] == "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"
    assert helper_summary["human_match_pipeline_status"] == "HUMAN_MATCH_PIPELINE_PREVIEW_READY"


def test_safety_flags_disabled(tmp_path):
    root = tmp_path / "repo"
    summary = _find(root, provider_match_id="u-bundesliga-2024-001")

    assert summary["network_calls_enabled"] is False
    assert summary["prediction_logic_enabled"] is False
    assert summary["betting_logic_enabled"] is False


def test_no_live_scraping_provider_or_network_calls_occur():
    files = [
        ROOT / "src" / "football_prediction_v19" / "importers" / "provider_match_finder_preview.py",
        ROOT / "scripts" / "find_provider_match_preview.py",
        ROOT / "scripts" / "audit_provider_match_finder_preview.py",
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
