from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_rolling_xg_form_reporting as form_audit  # noqa: E402
import build_rolling_xg_form_reporting as rolling  # noqa: E402
import build_understat_bundesliga_2024_rolling_xg_form_reporting as helper  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reporting_df(*, missing_xg: bool = False) -> pd.DataFrame:
    return pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "score": "1-0", "home_goals": 1, "away_goals": 0, "home_xg": 1.0, "away_xg": 0.2},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "score": "2-2", "home_goals": 2, "away_goals": 2, "home_xg": 1.5, "away_xg": "" if missing_xg else 0.7},
        {"date": "2024-01-15", "home_team": "Alpha", "away_team": "Gamma", "score": "0-1", "home_goals": 0, "away_goals": 1, "home_xg": 2.4, "away_xg": 0.4},
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
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "home_xg": 1.0, "away_xg": 0.2},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "home_xg": 1.5, "away_xg": 0.7},
        {"date": "2024-01-15", "home_team": "Alpha", "away_team": "Gamma", "home_xg": 2.4, "away_xg": 0.4},
    ]).to_csv(xg, index=False)
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "Alpha", "away_team": "Beta", "score": "1-0", "home_goals": 1, "away_goals": 0},
        {"date": "2024-01-08", "home_team": "Gamma", "away_team": "Alpha", "score": "2-2", "home_goals": 2, "away_goals": 2},
        {"date": "2024-01-15", "home_team": "Alpha", "away_team": "Gamma", "score": "0-1", "home_goals": 0, "away_goals": 1},
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
        "expected_rows": 3,
        "min_join_coverage_pct": 100.0,
        "notes": "tiny accepted xG",
    }]).to_csv(manifest, index=False)
    return root, preview, xg, target, manifest


def test_builds_rolling_xg_form_from_reporting_preview(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)
    summary = rolling.build_rolling_xg_form_reporting(
        reporting_preview=preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["form_status"] == rolling.ROLLING_XG_FORM_REPORTING_READY
    assert summary["team_match_rows"] == 6
    assert Path(summary["form_output_path"]).exists()


def test_creates_two_team_match_rows_per_match(tmp_path):
    rows = rolling.build_team_match_rows(_reporting_df())

    assert len(rows) == 6


def test_first_match_per_team_has_zero_available(tmp_path):
    rows = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
    first = rows.sort_values(["team", "date"]).groupby("team").head(1)

    assert (first["rolling_matches_available"] == 0).all()


def test_rolling_values_use_previous_matches_not_current(tmp_path):
    rows = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
    alpha_second = rows[(rows["team"] == "Alpha") & (rows["date"] == pd.Timestamp("2024-01-08"))].iloc[0]
    alpha_third = rows[(rows["team"] == "Alpha") & (rows["date"] == pd.Timestamp("2024-01-15"))].iloc[0]

    assert alpha_second["rolling_xg_for"] == 1.0
    assert alpha_second["rolling_xg_against"] == 0.2
    assert alpha_third["rolling_xg_for"] == 1.7
    assert alpha_third["xg_for"] == 2.4


def test_rolling_window_limit_is_respected(tmp_path):
    rows = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=1)
    alpha_third = rows[(rows["team"] == "Alpha") & (rows["date"] == pd.Timestamp("2024-01-15"))].iloc[0]

    assert alpha_third["rolling_matches_available"] == 1
    assert alpha_third["rolling_xg_for"] == 0.7


def test_home_away_context_is_preserved(tmp_path):
    rows = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
    alpha_third = rows[(rows["team"] == "Alpha") & (rows["date"] == pd.Timestamp("2024-01-15"))].iloc[0]

    assert alpha_third["venue_side"] == "home"
    assert alpha_third["rolling_home_xg_for"] == 1.0
    assert alpha_third["rolling_away_xg_for"] == 0.7


def test_goals_xg_rolling_values_from_accepted_match_level_xg_only(tmp_path):
    rows = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
    alpha_third = rows[(rows["team"] == "Alpha") & (rows["date"] == pd.Timestamp("2024-01-15"))].iloc[0]

    assert alpha_third["rolling_goals_for"] == 3
    assert alpha_third["rolling_goals_against"] == 2
    assert alpha_third["rolling_goals_minus_xg_for"] == (1 - 1.0) + (2 - 0.7)


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    df = _reporting_df()
    before = df[["home_xg", "away_xg"]].copy()

    rolling.add_rolling_form(rolling.build_team_match_rows(df), window=5)

    assert df[["home_xg", "away_xg"]].equals(before)


def test_blocks_missing_xg(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path, missing_xg=True)

    summary = rolling.build_rolling_xg_form_reporting(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", base_dir=root)

    assert summary["form_status"] == rolling.ROLLING_XG_FORM_REPORTING_BLOCKED_MISSING_XG
    assert summary["rows_missing_xg"] == 1


def test_blocks_unsafe_output_path(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)

    summary = rolling.build_rolling_xg_form_reporting(reporting_preview=preview, output_dir=root / "not_outputs", base_dir=root)

    assert summary["form_status"] == rolling.ROLLING_XG_FORM_REPORTING_BLOCKED_UNSAFE_PATH


def test_does_not_modify_target_artifact_or_manifest(tmp_path):
    root, preview, xg, target, manifest = _fixture_root(tmp_path)
    before = {preview: _sha(preview), xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)}

    rolling.build_rolling_xg_form_reporting(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {preview: _sha(preview), xg: _sha(xg), target: _sha(target), manifest: _sha(manifest)} == before


def test_audit_rolling_form_ready(tmp_path):
    root, preview, *_ = _fixture_root(tmp_path)
    summary = rolling.build_rolling_xg_form_reporting(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    table, _markdown, rec = form_audit.run(preview=summary["form_output_path"], output_dir=tmp_path / "diag", expected_team_match_rows=6, expected_teams=3)

    assert rec == form_audit.ROLLING_XG_FORM_REPORTING_READY
    assert table.iloc[0]["team_match_rows"] == 6


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _preview, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview", window=2)

    assert summary["recommendation"] == form_audit.ROLLING_XG_FORM_REPORTING_READY
    assert summary["team_match_rows"] == 6


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, preview, *_ = _fixture_root(tmp_path)

    rolling.build_rolling_xg_form_reporting(reporting_preview=preview, output_dir=root / "outputs" / "xg_reporting_preview", write_preview=True, base_dir=root)

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
