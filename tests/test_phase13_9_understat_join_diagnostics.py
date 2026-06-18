from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.understat_join_diagnostics import (  # noqa: E402
    ADD_UNDERSTAT_TEAM_ALIAS_MAP,
    READY_FOR_XG_ACCEPTANCE,
    REVIEW_UNDERSTAT_DATE_ALIGNMENT,
    UNDERSTAT_JOIN_BLOCKED_LOW_COVERAGE,
    build_understat_join_diagnostics,
    find_plus_minus_one_day_candidates,
    find_same_date_team_alias_candidates,
    write_understat_join_diagnostics,
)
import apply_understat_team_alias_preview as alias_preview  # noqa: E402
import audit_understat_team_alias_map as alias_audit  # noqa: E402

PYTHON = sys.executable


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(rows: list[tuple[str, str, str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["date", "home_team", "away_team", "home_xg", "away_xg"])


def _target(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Date", "HomeTeam", "AwayTeam"])


def _write_pair(tmp_path: Path, source: pd.DataFrame, target: pd.DataFrame) -> tuple[Path, Path]:
    source_path = tmp_path / "understat.csv"
    target_path = tmp_path / "football_data.csv"
    source.to_csv(source_path, index=False)
    target.to_csv(target_path, index=False)
    return source_path, target_path


def test_exact_join_coverage_detects_full_match(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([("2024-08-01", "Bayern Munich", "Dortmund", 1.2, 0.9)]),
        _target([("2024-08-01", "Bayern Munich", "Dortmund")]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    assert result.exact_matches == 1
    assert result.exact_coverage_pct == 100.0
    assert result.recommendation == READY_FOR_XG_ACCEPTANCE


def test_low_coverage_detected_with_same_source_target_row_count(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([
            ("2024-08-01", "Bayern Munich", "Dortmund", 1.2, 0.9),
            ("2024-08-02", "Leverkusen", "Mainz", 1.1, 0.7),
        ]),
        _target([
            ("2024-08-01", "Bayern Munich", "Dortmund"),
            ("2024-08-02", "Bayer Leverkusen", "Mainz 05"),
        ]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    assert result.exact_matches == 1
    assert result.diagnostic_label == UNDERSTAT_JOIN_BLOCKED_LOW_COVERAGE
    assert "SOURCE_TARGET_ROW_COUNTS_MATCH_BUT_JOIN_COVERAGE_LOW" in result.blocking_reasons


def test_unmatched_source_and_target_rows_written(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([("2024-08-01", "A", "B", 1.0, 1.0), ("2024-08-02", "C", "D", 1.0, 1.0)]),
        _target([("2024-08-01", "A", "B"), ("2024-08-02", "X", "Y")]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    paths = write_understat_join_diagnostics(result, tmp_path / "out")
    assert paths["unmatched_source"].exists()
    assert paths["unmatched_target"].exists()
    assert len(pd.read_csv(paths["unmatched_source"])) == 1
    assert len(pd.read_csv(paths["unmatched_target"])) == 1


def test_same_date_team_alias_candidates_detected(tmp_path):
    source = _source([("2024-08-02", "Leverkusen", "Mainz", 1.1, 0.7)])
    target = _target([("2024-08-02", "Bayer Leverkusen", "Mainz 05")])
    candidates = find_same_date_team_alias_candidates(source, target)
    assert not candidates.empty
    assert candidates.iloc[0]["candidate_type"] == "SAME_DATE_TEAM_ALIAS_REVIEW"


def test_plus_minus_one_day_candidates_detected(tmp_path):
    source = _source([("2024-08-03", "Leverkusen", "Mainz", 1.1, 0.7)])
    target = _target([("2024-08-02", "Leverkusen", "Mainz")])
    candidates = find_plus_minus_one_day_candidates(source, target)
    assert not candidates.empty
    assert int(candidates.iloc[0]["date_delta_days"]) == 1


def test_recommendation_add_alias_map_when_alias_candidates_explain_missing_rows(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([
            ("2024-08-01", "Team A", "Team B", 1.0, 1.0),
            ("2024-08-02", "Team C", "Team D", 1.0, 1.0),
        ]),
        _target([
            ("2024-08-01", "A FC", "B FC"),
            ("2024-08-02", "C FC", "D FC"),
        ]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    assert result.recommendation == ADD_UNDERSTAT_TEAM_ALIAS_MAP


def test_recommendation_review_date_alignment_when_date_candidates_explain_missing_rows(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([
            ("2024-08-02", "Team A", "Team B", 1.0, 1.0),
            ("2024-08-03", "Team C", "Team D", 1.0, 1.0),
        ]),
        _target([
            ("2024-08-01", "Team A", "Team B"),
            ("2024-08-02", "Team C", "Team D"),
        ]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    assert result.recommendation == REVIEW_UNDERSTAT_DATE_ALIGNMENT


def test_alias_map_template_has_required_columns():
    df = pd.read_csv(ROOT / "data" / "templates" / "understat_team_alias_map_template.csv")
    assert list(df.columns) == ["provider", "league", "season", "source_team", "target_team", "alias_status", "notes"]


def test_alias_map_audit_catches_missing_columns(tmp_path):
    path = tmp_path / "alias.csv"
    pd.DataFrame([{"source_team": "A"}]).to_csv(path, index=False)
    table, rec, failures = alias_audit.audit_alias_map(path)
    assert rec == "FIX_UNDERSTAT_TEAM_ALIAS_MAP"
    assert "required_columns" in failures
    assert table["status"].eq("FAIL").any()


def test_alias_map_audit_catches_duplicate_accepted_mappings(tmp_path):
    path = tmp_path / "alias.csv"
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "A", "target_team": "A1", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "A", "target_team": "A2", "alias_status": "accepted", "notes": ""},
    ]).to_csv(path, index=False)
    _table, rec, failures = alias_audit.audit_alias_map(path)
    assert rec == "FIX_UNDERSTAT_TEAM_ALIAS_MAP"
    assert "no_duplicate_accepted_source_team" in failures


def test_alias_map_audit_writes_csv_and_markdown(tmp_path):
    _table, markdown, rec = alias_audit.run(
        ROOT / "data" / "templates" / "understat_team_alias_map_template.csv",
        tmp_path / "out",
    )
    assert "Understat Team Alias Map Audit" in markdown
    assert rec == "CREATE_UNDERSTAT_TEAM_ALIAS_MAP"
    assert (tmp_path / "out" / "understat_team_alias_map_audit_summary.csv").exists()
    assert (tmp_path / "out" / "understat_team_alias_map_audit_summary.md").exists()


def test_alias_preview_applies_accepted_aliases_to_copy_only(tmp_path):
    source_path = tmp_path / "understat.csv"
    alias_path = tmp_path / "alias.csv"
    source_df = _source([("2024-08-01", "Leverkusen", "Mainz", 1.3, 0.8)])
    source_df.to_csv(source_path, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Leverkusen", "target_team": "Bayer Leverkusen", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Mainz", "target_team": "Mainz 05", "alias_status": "draft", "notes": ""},
    ]).to_csv(alias_path, index=False)
    before = _sha(source_path)
    out, summary = alias_preview.apply_alias_preview(source_path, alias_path, tmp_path / "out")
    assert summary["rows_changed"] == 1
    assert out.loc[0, "home_team"] == "Bayer Leverkusen"
    assert out.loc[0, "away_team"] == "Mainz"
    assert _sha(source_path) == before
    assert Path(summary["output_path"]).is_relative_to((tmp_path / "out").resolve())


def test_alias_preview_does_not_change_xg_values(tmp_path):
    source_path = tmp_path / "understat.csv"
    alias_path = tmp_path / "alias.csv"
    _source([("2024-08-01", "A", "B", 1.3, 0.8)]).to_csv(source_path, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "A", "target_team": "A FC", "alias_status": "accepted", "notes": ""},
    ]).to_csv(alias_path, index=False)
    out, _summary = alias_preview.apply_alias_preview(source_path, alias_path, tmp_path / "out")
    assert float(out.loc[0, "home_xg"]) == 1.3
    assert float(out.loc[0, "away_xg"]) == 0.8


def test_source_and_target_csvs_are_not_modified(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([("2024-08-01", "A", "B", 1.0, 1.0)]),
        _target([("2024-08-01", "A FC", "B FC")]),
    )
    before = {_path: _sha(_path) for _path in [source_path, target_path]}
    result = build_understat_join_diagnostics(source_path, target_path)
    write_understat_join_diagnostics(result, tmp_path / "out")
    after = {_path: _sha(_path) for _path in [source_path, target_path]}
    assert after == before


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text


def test_cli_writes_csv_and_markdown(tmp_path):
    source_path, target_path = _write_pair(
        tmp_path,
        _source([("2024-08-01", "A", "B", 1.0, 1.0)]),
        _target([("2024-08-01", "A", "B")]),
    )
    out_dir = tmp_path / "diag"
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "audit_understat_join_diagnostics.py"),
            "--source",
            str(source_path),
            "--target",
            str(target_path),
            "--output-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "recommendation=READY_FOR_XG_ACCEPTANCE" in result.stdout
    assert (out_dir / "understat_join_diagnostics_summary.csv").exists()
    assert (out_dir / "understat_join_diagnostics_summary.md").exists()


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source_path, target_path = _write_pair(
        tmp_path,
        _source([("2024-08-01", "A", "B", 1.0, 1.0)]),
        _target([("2024-08-01", "A FC", "B FC")]),
    )
    result = build_understat_join_diagnostics(source_path, target_path)
    write_understat_join_diagnostics(result, tmp_path / "out")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
