from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.trusted_xg_manifest_promotion import (  # noqa: E402
    MANIFEST_ENTRY_BLOCKED_MISSING_METADATA,
    MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH,
    MANIFEST_ENTRY_PREVIEW_ONLY,
    MANIFEST_ENTRY_PREVIEW_READY,
    run_trusted_xg_manifest_promotion,
)
import build_understat_bundesliga_2024_manifest_preview as manifest_helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_dir(tmp_path: Path) -> Path:
    root = ROOT / "outputs" / "pytest_phase13_11" / tmp_path.name
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_source_target(tmp_path: Path) -> tuple[Path, Path]:
    root = _fixture_dir(tmp_path)
    source = root / "trusted_xg.csv"
    target = root / "target.csv"
    rows = [
        {"date": "2024-01-01", "home_team": "A", "away_team": "B", "home_xg": 1.2, "away_xg": 0.8},
        {"date": "2024-01-02", "home_team": "C", "away_team": "D", "home_xg": 1.1, "away_xg": 0.9},
    ]
    pd.DataFrame(rows).to_csv(source, index=False)
    pd.DataFrame([
        {"Date": "2024-01-01", "HomeTeam": "A", "AwayTeam": "B"},
        {"Date": "2024-01-02", "HomeTeam": "C", "AwayTeam": "D"},
    ]).to_csv(target, index=False)
    return source, target


def _manifest_preview(result_path: str) -> pd.DataFrame:
    return pd.read_csv(result_path, low_memory=False)


def test_manifest_preview_flags_absolute_windows_output_paths(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path=ROOT / "outputs" / "pytest_phase13_11" / tmp_path.name / "manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    preview = _manifest_preview(result.manifest_preview_path)
    assert result.manifest_registration_status == MANIFEST_ENTRY_PREVIEW_ONLY
    assert preview.loc[0, "manifest_registration_status"] == MANIFEST_ENTRY_PREVIEW_ONLY
    assert str(preview.loc[0, "xg_file_path"]).replace("\\", "/").startswith("outputs/")


def test_manifest_preview_blocks_absolute_path_outside_repo(tmp_path):
    source, target = _write_source_target(tmp_path)
    outside = Path("C:/outside/manual_xg.csv")
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path=outside,
        league="Bundesliga",
        season="2024",
    )
    assert result.manifest_registration_status == MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH
    preview = _manifest_preview(result.manifest_preview_path)
    assert preview.loc[0, "manifest_registration_status"] == MANIFEST_ENTRY_BLOCKED_UNSAFE_PATH


def test_manifest_preview_accepts_repo_relative_accepted_path(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
        source_name="Understat Bundesliga 2024",
    )
    preview = _manifest_preview(result.manifest_preview_path)
    assert result.manifest_registration_status == MANIFEST_ENTRY_PREVIEW_READY
    assert preview.loc[0, "manifest_registration_status"] == MANIFEST_ENTRY_PREVIEW_READY
    assert preview.loc[0, "xg_file_path"] == "data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv"


def test_league_and_season_are_populated_in_manifest_preview(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    preview = _manifest_preview(result.manifest_preview_path)
    assert preview.loc[0, "league"] == "Bundesliga"
    assert str(preview.loc[0, "season"]) == "2024"


def test_missing_metadata_blocks_manifest_registration(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
    )
    assert result.manifest_registration_status == MANIFEST_ENTRY_BLOCKED_MISSING_METADATA


def test_target_file_path_remains_repo_relative(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    preview = _manifest_preview(result.manifest_preview_path)
    assert not Path(str(preview.loc[0, "target_file_path"])).is_absolute()


def test_no_production_manifest_is_modified(tmp_path):
    manifest = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"
    before = _sha(manifest)
    source, target = _write_source_target(tmp_path)
    run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    assert _sha(manifest) == before


def test_no_source_or_target_csv_modified_in_place(tmp_path):
    source, target = _write_source_target(tmp_path)
    before = {source: _sha(source), target: _sha(target)}
    run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    assert {source: _sha(source), target: _sha(target)} == before


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    source, target = _write_source_target(tmp_path)
    result = run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    filled = pd.read_csv(result.filled_preview_path, low_memory=False)
    assert set(filled["home_xg"].round(3)) == {1.2, 1.1}
    assert set(filled["away_xg"].round(3)) == {0.8, 0.9}


def test_helper_can_run_on_tiny_fixture_and_produce_manifest_preview_ready(tmp_path):
    root = _fixture_dir(tmp_path)
    source = root / "understat.csv"
    alias_map = root / "alias_map.csv"
    date_map = root / "date_map.csv"
    target = root / "target.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "St Pauli", "away_team": "Kiel", "home_xg": 1.4, "away_xg": 0.9},
    ]).to_csv(source, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "St Pauli", "target_team": "FC St Pauli", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Kiel", "target_team": "Holstein Kiel", "alias_status": "accepted", "notes": ""},
    ]).to_csv(alias_map, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    pd.DataFrame([
        {"Date": "2024-11-29", "HomeTeam": "FC St Pauli", "AwayTeam": "Holstein Kiel"},
    ]).to_csv(target, index=False)
    summary = manifest_helper.run_manifest_preview(
        source,
        alias_map,
        date_map,
        target,
        root / "outputs",
        "data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
    )
    assert summary["manifest_registration_status"] == MANIFEST_ENTRY_PREVIEW_READY


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source, target = _write_source_target(tmp_path)
    run_trusted_xg_manifest_promotion(
        source,
        target,
        target,
        output_dir=_fixture_dir(tmp_path) / "outputs" / "promotion",
        manifest_xg_path="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv",
        league="Bundesliga",
        season="2024",
    )
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
