from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_team_xg_reporting_aggregates as aggregate_audit  # noqa: E402
import build_team_xg_reporting_aggregates as aggregates  # noqa: E402
import build_understat_bundesliga_2024_team_xg_reporting_aggregates as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reporting_df(*, missing_xg: bool = False) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "date": "2024-01-01",
            "home_team": "Alpha",
            "away_team": "Beta",
            "score": "2-1",
            "home_goals": 2,
            "away_goals": 1,
            "home_xg": 1.4,
            "away_xg": 0.8,
            "xg_reporting_status": "XG_REPORTING_READY",
        },
        {
            "date": "2024-01-02",
            "home_team": "Beta",
            "away_team": "Alpha",
            "score": "0-3",
            "home_goals": 0,
            "away_goals": 3,
            "home_xg": "" if missing_xg else 0.5,
            "away_xg": 2.1,
            "xg_reporting_status": "MISSING_XG" if missing_xg else "XG_REPORTING_READY",
        },
    ])


def _fixture_root(tmp_path: Path, *, missing_xg: bool = False, manifest_id: str = "tiny_manifest_xg") -> tuple[Path, Path, Path, Path, Path]:
    root = tmp_path / "repo"
    out = root / "outputs" / "xg_reporting_preview"
    out.mkdir(parents=True)
    preview = out / "tiny_xg_reporting_preview.csv"
    _reporting_df(missing_xg=missing_xg).to_csv(preview, index=False)
    xg = root / "data" / "trusted_xg_sources" / "accepted" / "tiny_manual_xg.csv"
    target = root / "data" / "processed" / "target_clean.csv"
    manifest = root / "data" / "templates" / "manual_xg_manifest_template.csv"
    xg.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "home_xg": 1.4, "away_xg": 0.8},
        {"date": "2024-01-02", "home_team": "Beta", "away_team": "Alpha", "home_xg": 0.5, "away_xg": 2.1},
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "score": "2-1", "home_goals": 2, "away_goals": 1},
        {"date": "2024-01-02", "home_team": "Beta", "away_team": "Alpha", "score": "0-3", "home_goals": 0, "away_goals": 3},
    ]).to_csv(target, index=False)
    pd.DataFrame([{
        "manifest_id": manifest_id,
        "xg_file_path": "data/trusted_xg_sources/accepted/tiny_manual_xg.csv",
        "target_file_path": "data/processed/target_clean.csv",
        "league": "Tiny League",
        "season": "2024",
        "source_type": "MANUAL_XG_CSV",
        "data_role": "PRODUCTION",
        "is_demo": "false",
        "expected_rows": 2,
        "min_join_coverage_pct": 100.0,
        "notes": "tiny accepted xG",
    }]).to_csv(manifest, index=False)
    return root, preview, xg, target, manifest


def test_builds_team_aggregates_from_reporting_preview(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)
    summary = aggregates.build_team_xg_reporting_aggregates(
        reporting_preview=preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["aggregate_status"] == aggregates.TEAM_XG_REPORTING_AGGREGATES_READY
    assert summary["teams_reported"] == 2
    assert Path(summary["aggregate_output_path"]).exists()


def test_one_row_per_team_and_match_totals(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)
    summary = aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)
    table = pd.read_csv(summary["aggregate_output_path"], low_memory=False)

    assert sorted(table["team"]) == ["Alpha", "Beta"]
    assert int(table["matches"].sum()) == 4


def test_home_away_splits_are_correct(tmp_path):
    table = aggregates.build_team_aggregates(_reporting_df())
    alpha = table[table["team"] == "Alpha"].iloc[0]
    beta = table[table["team"] == "Beta"].iloc[0]

    assert alpha["home_matches"] == 1
    assert alpha["away_matches"] == 1
    assert beta["home_goals_for"] == 0
    assert beta["away_goals_for"] == 1


def test_goals_and_xg_for_against_from_match_level_values(tmp_path):
    table = aggregates.build_team_aggregates(_reporting_df())
    alpha = table[table["team"] == "Alpha"].iloc[0]
    beta = table[table["team"] == "Beta"].iloc[0]

    assert alpha["goals_for"] == 5
    assert alpha["goals_against"] == 1
    assert round(alpha["xg_for"], 2) == 3.5
    assert round(alpha["xg_against"], 2) == 1.3
    assert round(beta["xg_for"], 2) == 1.3


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    df = _reporting_df()
    before = df[["home_xg", "away_xg"]].copy()

    aggregates.build_team_aggregates(df)

    assert df[["home_xg", "away_xg"]].equals(before)


def test_blocks_missing_xg(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path, missing_xg=True)

    summary = aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", base_dir=root)

    assert summary["aggregate_status"] == aggregates.TEAM_XG_REPORTING_AGGREGATES_BLOCKED_MISSING_XG
    assert summary["rows_missing_xg"] == 1


def test_blocks_unsafe_output_path(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)

    summary = aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "not_outputs", base_dir=root)

    assert summary["aggregate_status"] == aggregates.TEAM_XG_REPORTING_AGGREGATES_BLOCKED_UNSAFE_PATH


def test_does_not_modify_target_artifact_or_manifest(tmp_path):
    root, preview, xg, target, manifest = _fixture_root(tmp_path)
    before = {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest), preview: _sha(preview)}

    aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {xg: _sha(xg), target: _sha(target), manifest: _sha(manifest), preview: _sha(preview)} == before


def test_audit_team_aggregates_ready(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)
    summary = aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    table, _markdown, rec = aggregate_audit.run(preview=summary["aggregate_output_path"], output_dir=tmp_path / "diag", expected_team_match_rows=4)

    assert rec == aggregate_audit.TEAM_XG_REPORTING_AGGREGATES_READY
    assert table.iloc[0]["teams_reported"] == 2


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _preview, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview")

    assert summary["recommendation"] == aggregate_audit.TEAM_XG_REPORTING_AGGREGATES_READY
    assert summary["teams_reported"] == 2


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, preview, *_ = _fixture_root(tmp_path)

    aggregates.build_team_xg_reporting_aggregates(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
