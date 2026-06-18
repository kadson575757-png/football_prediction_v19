from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import apply_understat_date_alignment_preview as date_preview  # noqa: E402
import audit_understat_date_alignment_map as date_audit  # noqa: E402
import build_understat_bundesliga_2024_xg_acceptance_preview as workflow  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _date_map(rows: list[dict[str, object]]) -> pd.DataFrame:
    columns = ["provider", "league", "season", "home_team", "away_team", "source_date", "target_date", "alignment_status", "notes"]
    return pd.DataFrame(rows, columns=columns)


def test_date_alignment_map_template_has_required_columns():
    df = pd.read_csv(ROOT / "data" / "templates" / "understat_date_alignment_template.csv")
    assert list(df.columns) == ["provider", "league", "season", "home_team", "away_team", "source_date", "target_date", "alignment_status", "notes"]


def test_audit_catches_missing_required_columns(tmp_path):
    path = tmp_path / "date_map.csv"
    pd.DataFrame([{"home_team": "FC St Pauli"}]).to_csv(path, index=False)
    table, rec, failures = date_audit.audit_date_alignment_map(path)
    assert rec == "FIX_UNDERSTAT_DATE_ALIGNMENT_MAP"
    assert "required_columns" in failures
    assert table["status"].eq("FAIL").any()


def test_audit_catches_invalid_date(tmp_path):
    path = tmp_path / "date_map.csv"
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "bad", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(path, index=False)
    _table, rec, failures = date_audit.audit_date_alignment_map(path)
    assert rec == "FIX_UNDERSTAT_DATE_ALIGNMENT_MAP"
    assert "dates_parseable" in failures


def test_audit_catches_duplicate_accepted_mapping(tmp_path):
    path = tmp_path / "date_map.csv"
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(path, index=False)
    _table, rec, failures = date_audit.audit_date_alignment_map(path)
    assert rec == "FIX_UNDERSTAT_DATE_ALIGNMENT_MAP"
    assert "no_duplicate_accepted_source_mapping" in failures


def test_audit_rejects_xg_columns_in_date_alignment_map(tmp_path):
    path = tmp_path / "date_map.csv"
    df = _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ])
    df["home_xg"] = 1.0
    df.to_csv(path, index=False)
    _table, rec, failures = date_audit.audit_date_alignment_map(path)
    assert rec == "FIX_UNDERSTAT_DATE_ALIGNMENT_MAP"
    assert "no_xg_columns" in failures


def test_date_alignment_preview_changes_only_accepted_row_date(tmp_path):
    source = tmp_path / "source.csv"
    date_map = tmp_path / "date_map.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "home_xg": 1.4, "away_xg": 0.9},
        {"date": "2024-12-01", "home_team": "Bayern Munich", "away_team": "Dortmund", "home_xg": 2.0, "away_xg": 1.1},
    ]).to_csv(source, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "Bayern Munich", "away_team": "Dortmund", "source_date": "2024-12-01", "target_date": "2024-11-30", "alignment_status": "pending", "notes": ""},
    ]).to_csv(date_map, index=False)
    out, summary = date_preview.apply_date_alignment_preview(source, date_map, tmp_path / "out")
    assert summary["rows_date_aligned"] == 1
    assert out.loc[0, "date"] == "2024-11-29"
    assert out.loc[1, "date"] == "2024-12-01"


def test_date_alignment_preview_preserves_home_xg_and_away_xg_exactly(tmp_path):
    source = tmp_path / "source.csv"
    date_map = tmp_path / "date_map.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "home_xg": 1.456, "away_xg": 0.789},
    ]).to_csv(source, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    out, _summary = date_preview.apply_date_alignment_preview(source, date_map, tmp_path / "out")
    assert float(out.loc[0, "home_xg"]) == 1.456
    assert float(out.loc[0, "away_xg"]) == 0.789


def test_pending_and_rejected_date_alignment_rows_are_not_applied(tmp_path):
    source = tmp_path / "source.csv"
    date_map = tmp_path / "date_map.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "home_xg": 1.4, "away_xg": 0.9},
    ]).to_csv(source, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "rejected", "notes": ""},
    ]).to_csv(date_map, index=False)
    out, summary = date_preview.apply_date_alignment_preview(source, date_map, tmp_path / "out")
    assert summary["rows_date_aligned"] == 0
    assert out.loc[0, "date"] == "2024-11-30"


def test_source_file_is_not_modified(tmp_path):
    source = tmp_path / "source.csv"
    date_map = tmp_path / "date_map.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "home_xg": 1.4, "away_xg": 0.9},
    ]).to_csv(source, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    before = _sha(source)
    date_preview.apply_date_alignment_preview(source, date_map, tmp_path / "out")
    assert _sha(source) == before


def test_helper_workflow_reaches_100_percent_after_alias_and_date_alignment(tmp_path):
    source = tmp_path / "understat.csv"
    alias_map = tmp_path / "alias_map.csv"
    date_map = tmp_path / "date_map.csv"
    target = tmp_path / "target.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "St Pauli", "away_team": "Kiel", "home_xg": 1.4, "away_xg": 0.9},
        {"date": "2024-12-01", "home_team": "Bayern", "away_team": "Dortmund", "home_xg": 2.0, "away_xg": 1.1},
    ]).to_csv(source, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "St Pauli", "target_team": "FC St Pauli", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Kiel", "target_team": "Holstein Kiel", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Bayern", "target_team": "Bayern Munich", "alias_status": "accepted", "notes": ""},
    ]).to_csv(alias_map, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    pd.DataFrame([
        {"Date": "2024-11-29", "HomeTeam": "FC St Pauli", "AwayTeam": "Holstein Kiel"},
        {"Date": "2024-12-01", "HomeTeam": "Bayern Munich", "AwayTeam": "Dortmund"},
    ]).to_csv(target, index=False)
    summary = workflow.run_workflow(source, alias_map, date_map, target, tmp_path / "outputs")
    assert summary["exact_matches"] == 2
    assert summary["rows_filled"] == 2
    assert summary["rows_missing_xg"] == 0
    assert summary["acceptance_label"] == "MANUAL_XG_ACCEPTED"
    assert summary["promotion_label"] == "TRUSTED_XG_PROMOTION_READY"


def test_no_network_calls_in_tests():
    text = Path(__file__).read_text(encoding="utf-8")
    assert ("url" + "open(") not in text
    assert ("req" + "uests.") not in text


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source = tmp_path / "source.csv"
    date_map = tmp_path / "date_map.csv"
    pd.DataFrame([
        {"date": "2024-11-30", "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "home_xg": 1.4, "away_xg": 0.9},
    ]).to_csv(source, index=False)
    _date_map([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "home_team": "FC St Pauli", "away_team": "Holstein Kiel", "source_date": "2024-11-30", "target_date": "2024-11-29", "alignment_status": "accepted", "notes": ""},
    ]).to_csv(date_map, index=False)
    date_preview.apply_date_alignment_preview(source, date_map, tmp_path / "out")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
