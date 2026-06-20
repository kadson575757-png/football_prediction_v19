from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_xg_matchup_reporting_preview as matchup_audit  # noqa: E402
import build_rolling_xg_form_reporting as rolling  # noqa: E402
import build_understat_bundesliga_2024_xg_matchup_reporting_preview as helper  # noqa: E402
import build_xg_matchup_reporting_preview as matchup  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reporting_df(*, missing_xg: bool = False) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "date": "2024-01-01",
            "home_team": "Alpha",
            "away_team": "Beta",
            "score": "1-0",
            "home_goals": 1,
            "away_goals": 0,
            "home_xg": 1.0,
            "away_xg": 0.2,
            "actual_result_label": "H",
            "xg_result_label": "H",
        },
        {
            "date": "2024-01-08",
            "home_team": "Gamma",
            "away_team": "Alpha",
            "score": "2-2",
            "home_goals": 2,
            "away_goals": 2,
            "home_xg": 1.5,
            "away_xg": "" if missing_xg else 0.7,
            "actual_result_label": "D",
            "xg_result_label": "H",
        },
        {
            "date": "2024-01-15",
            "home_team": "Alpha",
            "away_team": "Gamma",
            "score": "0-1",
            "home_goals": 0,
            "away_goals": 1,
            "home_xg": 2.4,
            "away_xg": 0.4,
            "actual_result_label": "A",
            "xg_result_label": "H",
        },
    ])


def _fixture_root(tmp_path: Path, *, missing_xg: bool = False, manifest_id: str = "tiny_manifest_xg") -> tuple[Path, Path, Path, Path, Path, Path]:
    root = tmp_path / "repo"
    out = root / "outputs" / "xg_reporting_preview"
    out.mkdir(parents=True)
    reporting_preview = out / "tiny_xg_reporting_preview.csv"
    _reporting_df(missing_xg=missing_xg).to_csv(reporting_preview, index=False)
    if missing_xg:
        rolling_preview = out / "tiny_rolling_xg_form_reporting.csv"
        form = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
        form.to_csv(rolling_preview, index=False)
    else:
        form = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=5)
        rolling_preview = out / "tiny_rolling_xg_form_reporting.csv"
        form.to_csv(rolling_preview, index=False)
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
    return root, reporting_preview, rolling_preview, xg, target, manifest


def test_builds_matchup_preview_from_reporting_and_rolling_previews(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert summary["matchup_status"] == matchup.XG_MATCHUP_REPORTING_PREVIEW_READY
    assert summary["matches_reported"] == 3
    assert Path(summary["matchup_output_path"]).exists()


def test_one_row_per_match_and_required_columns_exist(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )
    table = pd.read_csv(summary["matchup_output_path"], low_memory=False)

    assert len(table) == 3
    assert set(matchup.REQUIRED_MATCHUP_COLUMNS).issubset(table.columns)


def test_rolling_context_joined_for_home_and_away(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    reporting = pd.read_csv(reporting_preview, low_memory=False)
    form = pd.read_csv(rolling_preview, low_memory=False)

    table, missing = matchup.build_matchup_frame(reporting, form)

    assert missing == 0
    assert table.loc[2, "home_rolling_matches_available"] == 2
    assert table.loc[2, "away_rolling_matches_available"] == 1


def test_first_match_per_team_has_zero_context_not_missing(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    table, missing = matchup.build_matchup_frame(pd.read_csv(reporting_preview), pd.read_csv(rolling_preview))

    first_match = table.iloc[0]
    assert missing == 0
    assert first_match["home_rolling_matches_available"] == 0
    assert first_match["away_rolling_matches_available"] == 0
    assert first_match["matchup_reporting_status"] == "XG_MATCHUP_REPORTING_READY"


def test_rolling_matchup_values_use_only_previous_matches_not_current_match(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    table, _missing = matchup.build_matchup_frame(pd.read_csv(reporting_preview), pd.read_csv(rolling_preview))
    alpha_home_third = table.iloc[2]

    assert alpha_home_third["home_rolling_xg_for"] == 1.7
    assert alpha_home_third["home_xg"] == 2.4
    assert alpha_home_third["home_rolling_xg_for"] != 4.1


def test_window_limit_is_respected(tmp_path):
    root, reporting_preview, _rolling_preview, *_ = _fixture_root(tmp_path)
    form = rolling.add_rolling_form(rolling.build_team_match_rows(_reporting_df()), window=1)
    rolling_preview = root / "outputs" / "xg_reporting_preview" / "tiny_window_1_rolling.csv"
    form.to_csv(rolling_preview, index=False)
    table, _missing = matchup.build_matchup_frame(pd.read_csv(reporting_preview), pd.read_csv(rolling_preview))

    assert table.iloc[2]["home_rolling_matches_available"] == 1
    assert table.iloc[2]["home_rolling_xg_for"] == 0.7


def test_matchup_rolling_xg_diff_home_is_home_minus_away_context(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    table, _missing = matchup.build_matchup_frame(pd.read_csv(reporting_preview), pd.read_csv(rolling_preview))
    row = table.iloc[2]

    expected = row["home_rolling_xg_diff"] - row["away_rolling_xg_diff"]
    assert row["matchup_rolling_xg_diff_home"] == expected


def test_no_xg_values_are_inferred_or_invented(tmp_path):
    df = _reporting_df()
    before = df[["home_xg", "away_xg"]].copy()
    form = rolling.add_rolling_form(rolling.build_team_match_rows(df), window=5)

    matchup.build_matchup_frame(df, form)

    assert df[["home_xg", "away_xg"]].equals(before)


def test_blocks_missing_xg(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path, missing_xg=True)

    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        base_dir=root,
    )

    assert summary["matchup_status"] == matchup.XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_XG
    assert summary["rows_missing_xg"] == 1


def test_blocks_missing_rolling_context_for_non_first_match(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    form = pd.read_csv(rolling_preview, low_memory=False)
    form = form[~((form["match_index"] == 2) & (form["team"] == "Alpha"))]
    form.to_csv(rolling_preview, index=False)

    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        base_dir=root,
    )

    assert summary["matchup_status"] == matchup.XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_MISSING_ROLLING_CONTEXT
    assert summary["rows_missing_rolling_context"] == 1


def test_blocks_unsafe_output_path(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)

    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "not_outputs",
        base_dir=root,
    )

    assert summary["matchup_status"] == matchup.XG_MATCHUP_REPORTING_PREVIEW_BLOCKED_UNSAFE_PATH


def test_audit_matchup_preview_ready(tmp_path):
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)
    summary = matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    table, _markdown, rec = matchup_audit.run(preview=summary["matchup_output_path"], output_dir=tmp_path / "diag", expected_rows=3)

    assert rec == matchup_audit.XG_MATCHUP_REPORTING_PREVIEW_READY
    assert table.iloc[0]["matches_reported"] == 3


def test_does_not_modify_target_artifact_manifest_or_inputs(tmp_path):
    root, reporting_preview, rolling_preview, xg, target, manifest = _fixture_root(tmp_path)
    before = {path: _sha(path) for path in [reporting_preview, rolling_preview, xg, target, manifest]}

    matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert {path: _sha(path) for path in [reporting_preview, rolling_preview, xg, target, manifest]} == before


def test_helper_works_on_tiny_fixture_data(monkeypatch, tmp_path):
    root, _reporting_preview, _rolling_preview, _xg, _target, manifest = _fixture_root(tmp_path, manifest_id=helper.MANIFEST_ID)
    monkeypatch.setattr(helper, "ROOT", root)

    summary = helper.run_workflow(manifest, root / "outputs" / "xg_reporting_preview", window=2)

    assert summary["recommendation"] == matchup_audit.XG_MATCHUP_REPORTING_PREVIEW_READY
    assert summary["matches_reported"] == 3
    assert summary["manifest_id"] == helper.MANIFEST_ID


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    root, reporting_preview, rolling_preview, *_ = _fixture_root(tmp_path)

    matchup.build_xg_matchup_reporting_preview(
        reporting_preview=reporting_preview,
        rolling_form_preview=rolling_preview,
        output_dir=root / "outputs" / "xg_reporting_preview",
        write_preview=True,
        base_dir=root,
    )

    assert {path: _sha(path) for path in protected if path.exists()} == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text
