# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_csv import (
    import_manual_xg_csv,
    normalize_manual_xg_dataframe,
    validate_manual_xg_dataframe,
)
from football_prediction_v19.importers.registry import get_importer


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_manual_xg_importer as manual_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pair_df(**extra) -> pd.DataFrame:
    data = {
        "date": ["2026-01-01", "2026-01-02"],
        "home_team": ["A", "C"],
        "away_team": ["B", "D"],
        "home_xg": [1.2, 0.7],
        "away_xg": [0.8, 1.4],
    }
    data.update(extra)
    return pd.DataFrame(data)


def test_match_pair_manual_xg_validates_and_normalizes():
    normalized, errors, _warnings, summary = validate_manual_xg_dataframe(_pair_df(), path="season_manual_xg.csv")

    assert not errors
    assert list(normalized.columns)[:5] == ["date", "home_team", "away_team", "home_xg", "away_xg"]
    assert summary["xg_contract_label"] == "XG_CONTRACT_READY"


def test_xg_home_away_aliases_normalize():
    df = pd.DataFrame({"Date": ["2026-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "xG_home": [1.1], "xG_away": [0.9]})

    normalized = normalize_manual_xg_dataframe(df)

    assert normalized.loc[0, "home_xg"] == 1.1
    assert normalized.loc[0, "away_xg"] == 0.9


def test_hxg_axg_aliases_normalize():
    df = pd.DataFrame({"date": ["2026-01-01"], "home_team": ["A"], "away_team": ["B"], "hxg": [1.1], "axg": [0.9]})

    normalized = normalize_manual_xg_dataframe(df)

    assert normalized.loc[0, "home_xg"] == 1.1
    assert normalized.loc[0, "away_xg"] == 0.9


def test_missing_identity_columns_fails_validation():
    df = pd.DataFrame({"home_xg": [1.0], "away_xg": [0.8]})

    _normalized, errors, _warnings, _summary = validate_manual_xg_dataframe(df)

    assert "MISSING_IDENTITY_COLUMNS" in errors or "LONG_XG_PAIRING_REQUIRED" in errors


def test_missing_xg_columns_fails_validation():
    df = pd.DataFrame({"date": ["2026-01-01"], "home_team": ["A"], "away_team": ["B"]})

    _normalized, errors, _warnings, _summary = validate_manual_xg_dataframe(df)

    assert "MISSING_XG_COLUMNS" in errors or "LONG_XG_PAIRING_REQUIRED" in errors


def test_negative_xg_fails_validation():
    _normalized, errors, _warnings, _summary = validate_manual_xg_dataframe(_pair_df(home_xg=[-1.0, 0.7]))

    assert "NEGATIVE_XG_VALUES" in errors


def test_null_xg_fails_validation_in_strict_mode():
    _normalized, errors, _warnings, _summary = validate_manual_xg_dataframe(_pair_df(home_xg=[None, 0.7]), strict=True)

    assert "NULL_XG_VALUES" in errors


def test_template_file_detected_as_demo_not_production(tmp_path):
    source = tmp_path / "manual_xg_template.csv"
    _pair_df().to_csv(source, index=False)

    result = import_manual_xg_csv(source, output_dir=tmp_path / "preview", write_preview=False)

    assert "TEMPLATE_OR_DEMO_FILE" in result.warning_notes
    assert result.xg_production_ready is False


def test_importer_preview_writes_only_under_preview_dir(tmp_path):
    source = tmp_path / "season_manual_xg.csv"
    _pair_df().to_csv(source, index=False)
    output_dir = tmp_path / "outputs" / "xg_import_preview"

    result = import_manual_xg_csv(source, output_dir=output_dir)

    output = Path(result.output_path)
    assert output.exists()
    assert output_dir.resolve() in output.resolve().parents


def test_importer_never_overwrites_source_file(tmp_path):
    source = tmp_path / "season_manual_xg.csv"
    _pair_df().to_csv(source, index=False)
    before = _hash(source)

    import_manual_xg_csv(source, output_dir=tmp_path / "outputs" / "xg_import_preview")

    assert _hash(source) == before


def test_manual_xg_registry_entry_is_active():
    entry = get_importer("manual_xg_csv")

    assert entry["status"] == "ACTIVE"
    assert "manual_xg_csv_path" in entry["required_inputs"]


def test_audit_manual_xg_importer_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    templates = root / "data" / "templates"
    templates.mkdir(parents=True)
    _pair_df().to_csv(templates / "manual_xg_template.csv", index=False)

    table, markdown = manual_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert len(table) == 1
    assert (root / "outputs" / "diagnostics" / manual_audit.OUTPUT_CSV).exists()
    assert "Phase 12.9 is diagnostic/foundation only" in markdown


def test_cli_no_write_preview_does_not_write_preview_file(tmp_path):
    source = tmp_path / "season_manual_xg.csv"
    _pair_df().to_csv(source, index=False)
    output_dir = tmp_path / "preview"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_manual_xg_csv.py"),
            "--input",
            str(source),
            "--output-dir",
            str(output_dir),
            "--no-write-preview",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert not output_dir.exists()


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    source = tmp_path / "season_manual_xg.csv"
    _pair_df().to_csv(source, index=False)

    import_manual_xg_csv(source, output_dir=tmp_path / "outputs" / "xg_import_preview")

    after = {path: _hash(path) for path in protected}
    assert after == before
