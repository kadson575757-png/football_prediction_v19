# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_csv import import_manual_xg_csv
from football_prediction_v19.importers.manual_xg_template_generator import (
    XG_ENTRY_TEMPLATE_READY,
    XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS,
    build_manual_xg_entry_template,
    generate_manual_xg_entry_template,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_manual_xg_template_generation as template_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_lower() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "home_team": ["Team A", "Team C"],
        "away_team": ["Team B", "Team D"],
    })


def test_source_with_date_home_team_away_team_generates_blank_xg_template():
    template, result = build_manual_xg_entry_template(_source_lower(), source_path="source.csv")

    assert result.template_quality_label == XG_ENTRY_TEMPLATE_READY
    assert list(template.columns) == [
        "date",
        "home_team",
        "away_team",
        "home_xg",
        "away_xg",
        "league",
        "season",
        "source_file",
        "xg_entry_status",
    ]
    assert template[["home_xg", "away_xg"]].isna().all().all()


def test_source_with_Date_HomeTeam_AwayTeam_generates_blank_xg_template():
    source = pd.DataFrame({"Date": ["01/02/2026"], "HomeTeam": ["Home"], "AwayTeam": ["Away"]})

    template, result = build_manual_xg_entry_template(source, source_path="source.csv")

    assert result.template_quality_label == XG_ENTRY_TEMPLATE_READY
    assert template.loc[0, "date"] == "2026-01-02"
    assert pd.isna(template.loc[0, "home_xg"])


def test_source_with_date_home_away_generates_blank_xg_template():
    source = pd.DataFrame({"date": ["2026-03-01"], "home": ["Home"], "away": ["Away"]})

    template, result = build_manual_xg_entry_template(source, source_path="source.csv")

    assert result.template_quality_label == XG_ENTRY_TEMPLATE_READY
    assert template.loc[0, "home_team"] == "Home"
    assert template.loc[0, "away_team"] == "Away"


def test_home_xg_and_away_xg_are_blank_and_status_needs_manual_entry():
    template, _result = build_manual_xg_entry_template(_source_lower(), source_path="source.csv")

    assert template["home_xg"].isna().all()
    assert template["away_xg"].isna().all()
    assert set(template["xg_entry_status"]) == {"NEEDS_MANUAL_ENTRY"}


def test_duplicate_match_keys_are_removed_and_counted():
    source = pd.concat([_source_lower().head(1), _source_lower().head(1)], ignore_index=True)

    template, result = build_manual_xg_entry_template(source, source_path="source.csv")

    assert len(template) == 1
    assert result.duplicate_keys_removed == 1
    assert result.template_quality_label == XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS


def test_rows_missing_identity_are_excluded_and_counted():
    source = _source_lower()
    source.loc[1, "away_team"] = ""

    template, result = build_manual_xg_entry_template(source, source_path="source.csv")

    assert len(template) == 1
    assert result.missing_identity_rows == 1
    assert result.template_quality_label == XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS


def test_output_writes_only_under_outputs_xg_entry_templates(tmp_path):
    source = tmp_path / "fixtures.csv"
    _source_lower().to_csv(source, index=False)
    output_dir = tmp_path / "outputs" / "xg_entry_templates"

    result = generate_manual_xg_entry_template(source, output_dir=output_dir)

    output = Path(result.output_path)
    assert output.exists()
    assert output_dir.resolve() in output.resolve().parents


def test_no_write_does_not_write_output(tmp_path):
    source = tmp_path / "fixtures.csv"
    _source_lower().to_csv(source, index=False)
    output_dir = tmp_path / "outputs" / "xg_entry_templates"

    completed = subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "generate_manual_xg_template.py"),
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--no-write",
    ], capture_output=True, text=True, check=False)

    assert completed.returncode == 0
    assert "template_quality_label=XG_ENTRY_TEMPLATE_READY" in completed.stdout
    assert not output_dir.exists()


def test_source_file_is_never_overwritten(tmp_path):
    source = tmp_path / "fixtures.csv"
    _source_lower().to_csv(source, index=False)
    before = _hash(source)

    generate_manual_xg_entry_template(source, output_dir=tmp_path / "outputs" / "xg_entry_templates")

    assert _hash(source) == before


def test_audit_manual_xg_template_generation_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    _source_lower().to_csv(processed / "real_matches_clean.csv", index=False)

    table, markdown = template_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert not table.empty
    assert (root / "outputs" / "diagnostics" / template_audit.OUTPUT_CSV).exists()
    assert (root / "outputs" / "diagnostics" / template_audit.OUTPUT_MD).exists()
    assert "Phase 12.11 is diagnostic/foundation only" in markdown


def test_recommendation_ready_when_valid_sources_exist(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    _source_lower().to_csv(processed / "real_matches_clean.csv", index=False)

    table, _markdown = template_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert template_audit.recommendation(table) == "READY_TO_GENERATE_MANUAL_XG_ENTRY_TEMPLATE"


def test_generated_template_is_not_production_ready_until_xg_values_are_filled(tmp_path):
    source = tmp_path / "fixtures.csv"
    _source_lower().to_csv(source, index=False)
    result = generate_manual_xg_entry_template(source, output_dir=tmp_path / "outputs" / "xg_entry_templates")

    import_result = import_manual_xg_csv(result.output_path, strict=False, write_preview=False)

    assert import_result.xg_production_ready is False
    assert "NULL_XG_VALUES" in import_result.warning_notes


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    source = tmp_path / "fixtures.csv"
    _source_lower().to_csv(source, index=False)

    generate_manual_xg_entry_template(source, output_dir=tmp_path / "outputs" / "xg_entry_templates")

    assert {path: _hash(path) for path in protected} == before
