# -*- coding: utf-8 -*-
"""Tests for official_results importer.

All tests use mocked HTTP / fixture data — no real API calls are made.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from football_prediction_v19.importers.official_results import (
    LEAGUE_TO_FD_CODE,
    OUTPUT_COLUMNS,
    UNSUPPORTED_LEAGUES,
    _get_api_key,
    _safe_goals,
    fetch_football_data_results,
    merge_official_results_with_daily_reports,
    normalize_official_results,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _api_match(
    status: str = "FINISHED",
    home: str = "Arsenal FC",
    away: str = "Chelsea FC",
    home_goals: int | None = 2,
    away_goals: int | None = 1,
    utc_date: str = "2026-05-17T14:00:00Z",
    match_id: int = 1001,
) -> dict:
    """Build a minimal football-data.org match dict."""
    return {
        "id": match_id,
        "utcDate": utc_date,
        "status": status,
        "homeTeam": {"id": 57, "name": home},
        "awayTeam": {"id": 61, "name": away},
        "score": {
            "fullTime": {
                "home": home_goals,
                "away": away_goals,
            }
        },
    }


def _mock_session(matches: list[dict]):
    """Return a mock session whose .get().json() returns the given matches."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"matches": matches}
    resp.raise_for_status = MagicMock()
    session = MagicMock()
    session.get.return_value = resp
    return session


def _minimal_pre_report(league: str = "EPL",
                         home: str = "Arsenal FC",
                         away: str = "Chelsea FC",
                         date: str = "2026-05-17") -> pd.DataFrame:
    return pd.DataFrame([{
        "date": date,
        "league": league,
        "home_team": home,
        "away_team": away,
        "likely_1x2": "Home",
        "confidence": "MEDIUM",
        "model_home_prob": 0.5,
        "model_draw_prob": 0.25,
        "model_away_prob": 0.25,
        "control_10": 3.0,
        "chaos_10": 2.0,
        "recommended_market_type": "DOUBLE_CHANCE",
        "recommended_market_read": "home_or_draw_1X",
        "recommendation_strength": "MEDIUM",
        "risk_note": "test",
    }])


# ---------------------------------------------------------------------------
# 1. Normal finished match -> verified=yes
# ---------------------------------------------------------------------------

def test_finished_match_becomes_verified_yes():
    match = _api_match(status="FINISHED", home_goals=2, away_goals=1)
    with patch(
        "football_prediction_v19.importers.official_results._make_session",
        return_value=_mock_session([match]),
    ), patch(
        "football_prediction_v19.importers.official_results._get_api_key",
        return_value="fake-key",
    ):
        df = fetch_football_data_results("fake-key", "2026-05-17", "2026-05-17",
                                          leagues=["EPL"])
    assert len(df) == 1
    row = df.iloc[0]
    assert row["verified"] == "yes"
    assert row["home_goals"] == 2
    assert row["away_goals"] == 1
    assert row["source_status"] == "FINISHED"


# ---------------------------------------------------------------------------
# 2. Scheduled match -> verified=no, goals blank
# ---------------------------------------------------------------------------

def test_scheduled_match_remains_verified_no():
    match = _api_match(status="SCHEDULED", home_goals=None, away_goals=None)
    with patch(
        "football_prediction_v19.importers.official_results._make_session",
        return_value=_mock_session([match]),
    ), patch(
        "football_prediction_v19.importers.official_results._get_api_key",
        return_value="fake-key",
    ):
        df = fetch_football_data_results("fake-key", "2026-05-17", "2026-05-17",
                                          leagues=["EPL"])
    row = df.iloc[0]
    assert row["verified"] == "no"
    assert row["home_goals"] is None
    assert row["away_goals"] is None


# ---------------------------------------------------------------------------
# 3. Missing goals with FINISHED status -> verified=no
# ---------------------------------------------------------------------------

def test_finished_status_missing_goals_remains_unverified():
    match = _api_match(status="FINISHED", home_goals=None, away_goals=None)
    with patch(
        "football_prediction_v19.importers.official_results._make_session",
        return_value=_mock_session([match]),
    ), patch(
        "football_prediction_v19.importers.official_results._get_api_key",
        return_value="fake-key",
    ):
        df = fetch_football_data_results("fake-key", "2026-05-17", "2026-05-17",
                                          leagues=["EPL"])
    row = df.iloc[0]
    assert row["verified"] == "no"
    assert row["home_goals"] is None


# ---------------------------------------------------------------------------
# 4. Team aliases resolve in normalize_official_results
# ---------------------------------------------------------------------------

def test_team_aliases_resolve():
    df = pd.DataFrame([{
        "date": "2026-05-17", "league": "EPL",
        "home_team": "Spurs",        # alias -> Tottenham Hotspur  (in team_aliases.json)
        "away_team": "Tottenham",    # another alias -> Tottenham Hotspur
        "home_goals": 1, "away_goals": 0,
        "verified": "yes",
        "source_note": "football-data.org",
        "source_match_id": 99,
        "source_status": "FINISHED",
        "last_updated": "2026-05-17T20:00:00Z",
    }])
    out = normalize_official_results(df)
    # normalize_team_name resolves known aliases from config/team_aliases.json
    assert out.iloc[0]["home_team"] == "Tottenham Hotspur"
    assert out.iloc[0]["away_team"] == "Tottenham Hotspur"


# ---------------------------------------------------------------------------
# 5. Ambiguous match -> verified=no, source_note=ambiguous_match
# ---------------------------------------------------------------------------

def test_ambiguous_match_stays_unverified(tmp_path):
    # Two API rows for the same date+teams
    results = pd.DataFrame([
        {"date": "2026-05-17", "league": "EPL",
         "home_team": "Arsenal FC", "away_team": "Chelsea FC",
         "home_goals": 1, "away_goals": 0, "verified": "yes",
         "source_note": "football-data.org", "source_match_id": 1,
         "source_status": "FINISHED", "last_updated": "2026-05-17T20:00:00Z"},
        {"date": "2026-05-17", "league": "EPL",
         "home_team": "Arsenal FC", "away_team": "Chelsea FC",
         "home_goals": 2, "away_goals": 1, "verified": "yes",
         "source_note": "football-data.org", "source_match_id": 2,
         "source_status": "FINISHED", "last_updated": "2026-05-17T20:00:00Z"},
    ])[OUTPUT_COLUMNS]

    pre_csv = tmp_path / "epl_2026-05-17_daily_report.csv"
    _minimal_pre_report().to_csv(pre_csv, index=False)

    out = merge_official_results_with_daily_reports(results, tmp_path, tmp_path / "scores.csv")
    assert out.iloc[0]["verified"] == "no"
    assert out.iloc[0]["source_note"] == "ambiguous_match"


# ---------------------------------------------------------------------------
# 6. Unsupported league (2. Bundesliga / MLS) -> verified=no
# ---------------------------------------------------------------------------

def test_unsupported_league_is_not_in_league_mapping():
    assert "2. Bundesliga" not in LEAGUE_TO_FD_CODE
    assert "MLS" not in LEAGUE_TO_FD_CODE
    assert "2. Bundesliga" in UNSUPPORTED_LEAGUES
    assert "MLS" in UNSUPPORTED_LEAGUES


def test_unsupported_league_row_stays_unverified(tmp_path):
    # Build results with only EPL data; pre-match has D2 which has no API match
    results = pd.DataFrame([{
        "date": "2026-05-17", "league": "EPL",
        "home_team": "Arsenal FC", "away_team": "Chelsea FC",
        "home_goals": 2, "away_goals": 0, "verified": "yes",
        "source_note": "football-data.org", "source_match_id": 1,
        "source_status": "FINISHED", "last_updated": "2026-05-17T20:00:00Z",
    }])[OUTPUT_COLUMNS]

    # Pre-match report has a 2. Bundesliga row (unsupported)
    d2_report = tmp_path / "d2_2026-05-17_daily_report.csv"
    pd.DataFrame([{
        "date": "2026-05-17", "league": "2. Bundesliga",
        "home_team": "Hertha BSC", "away_team": "Schalke 04",
        "likely_1x2": "Home", "confidence": "LOW",
        "model_home_prob": 0.4, "model_draw_prob": 0.3, "model_away_prob": 0.3,
        "control_10": 1.0, "chaos_10": 2.0,
        "recommended_market_type": "AVOID", "recommended_market_read": "test",
        "recommendation_strength": "LOW", "risk_note": "test",
    }]).to_csv(d2_report, index=False)

    out = merge_official_results_with_daily_reports(results, tmp_path, tmp_path / "scores.csv")
    d2_row = out[out["league"] == "2. Bundesliga"]
    assert len(d2_row) == 1
    assert d2_row.iloc[0]["verified"] == "no"
    assert d2_row.iloc[0]["source_note"] == "no_match_found"
    assert pd.isna(d2_row.iloc[0]["home_goals"]) or d2_row.iloc[0]["home_goals"] is None


# ---------------------------------------------------------------------------
# 7. Missing API key fails clearly
# ---------------------------------------------------------------------------

def test_missing_api_key_raises_environment_error(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="FOOTBALL_DATA_API_KEY"):
        _get_api_key(None)


def test_explicit_api_key_accepted():
    key = _get_api_key("my-test-key")
    assert key == "my-test-key"


# ---------------------------------------------------------------------------
# 8. Output schema correct
# ---------------------------------------------------------------------------

def test_output_schema_correct(tmp_path):
    results = pd.DataFrame([{
        "date": "2026-05-17", "league": "EPL",
        "home_team": "Arsenal FC", "away_team": "Chelsea FC",
        "home_goals": 3, "away_goals": 1, "verified": "yes",
        "source_note": "football-data.org", "source_match_id": 42,
        "source_status": "FINISHED", "last_updated": "2026-05-17T20:00:00Z",
    }])[OUTPUT_COLUMNS]

    pre_csv = tmp_path / "epl_2026-05-17_daily_report.csv"
    _minimal_pre_report().to_csv(pre_csv, index=False)

    out_path = tmp_path / "final_scores.csv"
    out = merge_official_results_with_daily_reports(results, tmp_path, out_path)

    assert out_path.exists()
    reloaded = pd.read_csv(out_path)
    for col in OUTPUT_COLUMNS:
        assert col in reloaded.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# 9. No guessed / estimated scores written
# ---------------------------------------------------------------------------

def test_no_guessed_scores_in_output(tmp_path):
    """verified=yes must only appear when API says FINISHED + goals present."""
    # Simulate: one match FINISHED (ok), one SCHEDULED (no score), one FINISHED missing goals
    matches = [
        _api_match(status="FINISHED", home_goals=1, away_goals=0, match_id=1),
        _api_match(status="SCHEDULED", home_goals=None, away_goals=None, match_id=2,
                   home="Liverpool FC", away="Everton FC"),
        _api_match(status="FINISHED", home_goals=None, away_goals=None, match_id=3,
                   home="Tottenham Hotspur FC", away="West Ham United FC"),
    ]
    with patch(
        "football_prediction_v19.importers.official_results._make_session",
        return_value=_mock_session(matches),
    ), patch(
        "football_prediction_v19.importers.official_results._get_api_key",
        return_value="fake-key",
    ):
        df = fetch_football_data_results("fake-key", "2026-05-17", "2026-05-17",
                                          leagues=["EPL"])

    # Only the one truly FINISHED+goals row may be verified
    verified_rows = df[df["verified"] == "yes"]
    assert len(verified_rows) == 1
    assert verified_rows.iloc[0]["home_goals"] == 1
    assert verified_rows.iloc[0]["away_goals"] == 0

    # All others must be unverified with no goals
    unverified = df[df["verified"] != "yes"]
    assert (unverified["home_goals"].isna()).all()


# ---------------------------------------------------------------------------
# 10. _safe_goals handles edge cases
# ---------------------------------------------------------------------------

def test_safe_goals_handles_none():
    assert _safe_goals({"home": None}, "home") is None


def test_safe_goals_handles_integer():
    assert _safe_goals({"home": 3}, "home") == 3


def test_safe_goals_handles_string_integer():
    assert _safe_goals({"home": "2"}, "home") == 2


def test_safe_goals_handles_missing_key():
    assert _safe_goals({}, "home") is None


# ---------------------------------------------------------------------------
# 11. fetch_football_data_results output has correct columns
# ---------------------------------------------------------------------------

def test_fetch_returns_correct_columns():
    with patch(
        "football_prediction_v19.importers.official_results._make_session",
        return_value=_mock_session([_api_match()]),
    ), patch(
        "football_prediction_v19.importers.official_results._get_api_key",
        return_value="fake-key",
    ):
        df = fetch_football_data_results("fake-key", "2026-05-17", "2026-05-17",
                                          leagues=["EPL"])
    for col in OUTPUT_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# 12. No match found in API -> verified=no, source_note=no_match_found
# ---------------------------------------------------------------------------

def test_no_match_found_stays_unverified(tmp_path):
    # API returns empty list for this competition
    results = pd.DataFrame(columns=OUTPUT_COLUMNS)

    pre_csv = tmp_path / "epl_2026-05-17_daily_report.csv"
    _minimal_pre_report().to_csv(pre_csv, index=False)

    out = merge_official_results_with_daily_reports(results, tmp_path, tmp_path / "scores.csv")
    assert out.iloc[0]["verified"] == "no"
    assert out.iloc[0]["source_note"] == "no_match_found"
    assert pd.isna(out.iloc[0]["home_goals"]) or out.iloc[0]["home_goals"] is None
