from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.trusted_xg_intake import (  # noqa: E402
    TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA,
    TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH,
    TRUSTED_XG_INTAKE_NO_SOURCES_FOUND,
    TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW,
    build_trusted_xg_intake_report,
    discover_trusted_xg_sources,
    evaluate_trusted_xg_source_intake,
    trusted_xg_intake_recommendation,
)
import audit_trusted_xg_intake as intake_audit  # noqa: E402


PYTHON = sys.executable


def _matches(n: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
        "HomeTeam": [f"Home {idx}" for idx in range(n)],
        "AwayTeam": [f"Away {idx}" for idx in range(n)],
        "FTHG": [1] * n,
        "FTAG": [0] * n,
        "FTR": ["H"] * n,
    })


def _trusted(n: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
        "home_team": [f"Home {idx}" for idx in range(n)],
        "away_team": [f"Away {idx}" for idx in range(n)],
        "home_xg": [1.1 + idx for idx in range(n)],
        "away_xg": [0.5 + idx for idx in range(n)],
    })


def _write_pair(tmp_path: Path, source_rows: int = 2, target_rows: int = 2) -> tuple[Path, Path]:
    source = tmp_path / "trusted_xg.csv"
    target = tmp_path / "target_clean.csv"
    _trusted(source_rows).to_csv(source, index=False)
    _matches(target_rows).to_csv(target, index=False)
    return source, target


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_no_source_files_recommends_add_trusted_xg_source_file(tmp_path):
    source_dir = tmp_path / "trusted_xg_sources"
    source_dir.mkdir()
    table = build_trusted_xg_intake_report(source_dir)
    assert table.iloc[0]["intake_label"] == TRUSTED_XG_INTAKE_NO_SOURCES_FOUND
    assert trusted_xg_intake_recommendation(table) == "ADD_TRUSTED_XG_SOURCE_FILE"


def test_valid_match_pair_trusted_source_is_detected(tmp_path):
    source, target = _write_pair(tmp_path)
    result = evaluate_trusted_xg_source_intake(source, targets=[target])
    assert result.valid_source is True
    assert result.detected_schema == "MATCH_PAIR_XG_SOURCE"


def test_invalid_schema_is_blocked(tmp_path):
    source = tmp_path / "bad_xg.csv"
    target = tmp_path / "target.csv"
    pd.DataFrame({"foo": [1]}).to_csv(source, index=False)
    _matches().to_csv(target, index=False)
    result = evaluate_trusted_xg_source_intake(source, targets=[target])
    assert result.intake_label == TRUSTED_XG_INTAKE_BLOCKED_INVALID_SCHEMA


def test_demo_example_files_are_not_counted_as_production_sources(tmp_path):
    source_dir = tmp_path / "trusted_xg_sources"
    source_dir.mkdir()
    _trusted().to_csv(source_dir / "sample_trusted_xg.csv", index=False)
    _trusted().to_csv(source_dir / "real_trusted_xg.csv", index=False)
    sources = discover_trusted_xg_sources(source_dir)
    assert [path.name for path in sources] == ["real_trusted_xg.csv"]


def test_source_with_matching_target_reports_fill_coverage(tmp_path):
    source, target = _write_pair(tmp_path)
    result = evaluate_trusted_xg_source_intake(source, targets=[target])
    assert result.best_rows_filled == 2
    assert result.best_fill_coverage_pct == 100.0
    assert result.intake_label == TRUSTED_XG_INTAKE_READY_FOR_PROMOTION_PREVIEW


def test_source_with_no_target_match_reports_blocked_no_target_match(tmp_path):
    source = tmp_path / "trusted_xg.csv"
    target = tmp_path / "target_clean.csv"
    _trusted().to_csv(source, index=False)
    _matches().assign(HomeTeam=["Other 1", "Other 2"]).to_csv(target, index=False)
    result = evaluate_trusted_xg_source_intake(source, targets=[target])
    assert result.best_rows_filled == 0
    assert result.intake_label == TRUSTED_XG_INTAKE_BLOCKED_NO_TARGET_MATCH


def test_command_generator_prints_fill_validate_promote_commands(tmp_path):
    source, target = _write_pair(tmp_path)
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "show_trusted_xg_intake_commands.py"),
            "--source-dir",
            str(source.parent),
            "--target",
            str(target),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "generate_manual_xg_template.py" in result.stdout
    assert "fill_manual_xg_from_trusted_source.py" in result.stdout
    assert "validate_filled_manual_xg.py" in result.stdout
    assert "promote_trusted_xg_to_manifest.py" in result.stdout


def test_intake_audit_writes_csv_and_markdown(tmp_path):
    source_dir = tmp_path / "trusted_xg_sources"
    output_dir = tmp_path / "outputs" / "diagnostics"
    source_dir.mkdir()
    table, markdown, rec = intake_audit.run(source_dir, output_dir)
    assert not table.empty
    assert (output_dir / "trusted_xg_intake_summary.csv").exists()
    assert (output_dir / "trusted_xg_intake_summary.md").exists()
    assert "Phase 13.3 Trusted xG Source Intake Audit" in markdown
    assert rec == "ADD_TRUSTED_XG_SOURCE_FILE"


def test_optional_command_list_writes_ps1_under_outputs_diagnostics(tmp_path):
    source_dir = tmp_path / "trusted_xg_sources"
    output_dir = tmp_path / "outputs" / "diagnostics"
    source_dir.mkdir()
    intake_audit.run(source_dir, output_dir, write_command_list=True)
    command_file = output_dir / "trusted_xg_next_commands.ps1"
    assert command_file.exists()
    assert output_dir.resolve() in command_file.resolve().parents


def test_docs_manual_xg_workflow_contains_trusted_xg_source_intake():
    text = (ROOT / "docs" / "manual_xg_workflow.md").read_text(encoding="utf-8")
    assert "Trusted xG Source Intake" in text
    assert "audit_trusted_xg_intake.py" in text


def test_protected_logic_files_are_not_modified_by_intake(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source_dir = tmp_path / "trusted_xg_sources"
    output_dir = tmp_path / "outputs" / "diagnostics"
    source_dir.mkdir()
    intake_audit.run(source_dir, output_dir, write_command_list=True)
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
