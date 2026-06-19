from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import audit_accepted_trusted_xg_artifacts as accepted_audit  # noqa: E402
import build_understat_bundesliga_2024_accepted_artifact_preview as accepted_helper  # noqa: E402
import materialize_accepted_trusted_xg_artifact as materializer  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _filled_and_target(tmp_path: Path, *, rows: int = 2, missing_xg: bool = False, target_rows: int | None = None) -> tuple[Path, Path]:
    filled = tmp_path / "filled_manual_xg.csv"
    target = tmp_path / "target.csv"
    data = []
    target_data = []
    for idx in range(rows):
        data.append({
            "date": f"2024-01-{idx + 1:02d}",
            "home_team": f"Home {idx}",
            "away_team": f"Away {idx}",
            "home_xg": "" if missing_xg and idx == 0 else 1.1 + idx,
            "away_xg": 0.7 + idx,
        })
    for idx in range(target_rows if target_rows is not None else rows):
        target_data.append({"Date": f"2024-01-{idx + 1:02d}", "HomeTeam": f"Home {idx}", "AwayTeam": f"Away {idx}"})
    pd.DataFrame(data).to_csv(filled, index=False)
    pd.DataFrame(target_data).to_csv(target, index=False)
    return filled, target


def _accepted_path(name: str) -> str:
    return f"data/trusted_xg_sources/accepted/{name}"


def test_dry_run_does_not_write_accepted_artifact(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    accepted = ROOT / _accepted_path("pytest_dry_run_manual_xg.csv")
    if accepted.exists():
        accepted.unlink()
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_dry_run_manual_xg.csv"),
        target,
        write=False,
        output_dir=tmp_path / "diag",
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_READY
    assert not accepted.exists()


def test_write_writes_only_under_accepted_dir(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    accepted_rel = _accepted_path("pytest_written_manual_xg.csv")
    accepted = ROOT / accepted_rel
    if accepted.exists():
        accepted.unlink()
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        accepted_rel,
        target,
        write=True,
        output_dir=tmp_path / "diag",
    )
    try:
        assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_WRITTEN
        assert accepted.exists()
        assert accepted.resolve().is_relative_to((ROOT / "data" / "trusted_xg_sources" / "accepted").resolve())
    finally:
        if accepted.exists():
            accepted.unlink()


def test_rejects_outputs_path_as_accepted_output(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        "outputs/not_allowed.csv",
        target,
        output_dir=tmp_path / "diag",
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_UNSAFE_PATH


def test_rejects_unsafe_absolute_path(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        "C:/outside/accepted.csv",
        target,
        output_dir=tmp_path / "diag",
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_UNSAFE_PATH


def test_rejects_missing_xg(tmp_path):
    filled, target = _filled_and_target(tmp_path, missing_xg=True)
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_missing_manual_xg.csv"),
        target,
        output_dir=tmp_path / "diag",
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_MISSING_XG


def test_rejects_low_join_coverage(tmp_path):
    filled, target = _filled_and_target(tmp_path, rows=2, target_rows=3)
    summary = materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_low_coverage_manual_xg.csv"),
        target,
        min_join_coverage=100.0,
        output_dir=tmp_path / "diag",
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_LOW_COVERAGE


def test_preserves_xg_values_no_inference(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    accepted_rel = _accepted_path("pytest_preserve_manual_xg.csv")
    accepted = ROOT / accepted_rel
    if accepted.exists():
        accepted.unlink()
    materializer.materialize_accepted_trusted_xg_artifact(filled, accepted_rel, target, write=True, output_dir=tmp_path / "diag")
    try:
        out = pd.read_csv(accepted, low_memory=False)
        original = pd.read_csv(filled, low_memory=False)
        assert out[["home_xg", "away_xg"]].equals(original[["home_xg", "away_xg"]])
    finally:
        if accepted.exists():
            accepted.unlink()


def test_source_csv_and_target_csv_are_not_modified(tmp_path):
    filled, target = _filled_and_target(tmp_path)
    before = {filled: _sha(filled), target: _sha(target)}
    materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_no_mutation_manual_xg.csv"),
        target,
        output_dir=tmp_path / "diag",
    )
    assert {filled: _sha(filled), target: _sha(target)} == before


def test_audit_detects_accepted_artifact(tmp_path):
    accepted_dir = tmp_path / "accepted"
    accepted_dir.mkdir()
    artifact = accepted_dir / "custom_manual_xg.csv"
    filled, _target = _filled_and_target(tmp_path)
    artifact.write_text(filled.read_text(encoding="utf-8"), encoding="utf-8")
    table, _markdown, rec = accepted_audit.run(accepted_dir=accepted_dir, output_dir=tmp_path / "diag")
    assert len(table) == 1
    assert rec == "ACCEPTED_TRUSTED_XG_ARTIFACTS_READY"


def test_helper_works_on_tiny_fixture_data(tmp_path):
    source = tmp_path / "understat.csv"
    alias_map = tmp_path / "alias.csv"
    date_map = tmp_path / "date.csv"
    target = tmp_path / "target.csv"
    pd.DataFrame([{"date": "2024-11-30", "home_team": "St Pauli", "away_team": "Kiel", "home_xg": 1.4, "away_xg": 0.9}]).to_csv(source, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "St Pauli", "target_team": "FC St Pauli", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Kiel", "target_team": "Holstein Kiel", "alias_status": "accepted", "notes": ""},
    ]).to_csv(alias_map, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    pd.DataFrame([{"Date": "2024-11-29", "HomeTeam": "FC St Pauli", "AwayTeam": "Holstein Kiel"}]).to_csv(target, index=False)
    summary = accepted_helper.run_accepted_artifact_preview(
        source,
        alias_map,
        date_map,
        target,
        tmp_path / "outputs",
        _accepted_path("pytest_helper_manual_xg.csv"),
        write=False,
    )
    assert summary["materialization_status"] == materializer.ACCEPTED_TRUSTED_XG_ARTIFACT_READY


def test_no_production_manifest_modified(tmp_path):
    manifest = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"
    before = _sha(manifest)
    filled, target = _filled_and_target(tmp_path)
    materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_manifest_unchanged_manual_xg.csv"),
        target,
        output_dir=tmp_path / "diag",
    )
    assert _sha(manifest) == before


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    filled, target = _filled_and_target(tmp_path)
    materializer.materialize_accepted_trusted_xg_artifact(
        filled,
        _accepted_path("pytest_protected_manual_xg.csv"),
        target,
        output_dir=tmp_path / "diag",
    )
    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
