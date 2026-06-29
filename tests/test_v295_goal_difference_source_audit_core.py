import pandas as pd

from scripts import audit_v295_goal_difference_sources as mod


def test_v295_source_audit_includes_only_games_before_match_date(monkeypatch, tmp_path):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 3, "away_goals": 0},
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 1},
            {"match_date": "2026-03-02", "home_team": "Team B", "away_team": "Arsenal", "home_goals": 0, "away_goals": 4},
            {"match_date": "2026-02-19", "home_team": "Chelsea", "away_team": "Team C", "home_goals": 1, "away_goals": 2},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.audit_goal_difference_sources(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )
    home_details = pd.read_csv(result["home_matches_csv_path"])

    assert result["home_goal_difference_before_match"] == 3
    assert result["away_goal_difference_before_match"] == -1
    assert result["goal_difference_diff"] == 4
    assert result["leakage_check_status"] == "CLEAN"
    assert result["post_match_games_used_count"] == 0
    assert bool(home_details.loc[home_details["source_match_date"].eq("2026-02-20"), "included_in_goal_difference"].iloc[0]) is True
    assert bool(home_details.loc[home_details["source_match_date"].eq("2026-03-01"), "included_in_goal_difference"].iloc[0]) is False
    assert bool(home_details.loc[home_details["source_match_date"].eq("2026-03-02"), "included_in_goal_difference"].iloc[0]) is False
    assert set(home_details.loc[home_details["source_match_date"].ge("2026-03-01"), "exclusion_reason"]) == {"NOT_BEFORE_MATCH_DATE"}


def test_v295_current_match_is_excluded(monkeypatch, tmp_path):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 5, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Chelsea", "away_team": "Team B", "home_goals": 0, "away_goals": 1},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.audit_goal_difference_sources(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        match_date="2026-03-01",
        output_dir=tmp_path,
    )

    assert result["current_match_excluded"] is True
    assert result["current_match_excluded_count"] == 1


def test_v295_leakage_status_failed_when_post_match_game_is_used():
    details = [
        {"source_match_date": "2026-03-02", "included_in_goal_difference": True},
        {"source_match_date": "2026-02-20", "included_in_goal_difference": True},
    ]

    assert mod._post_match_games_used_count(details, "2026-03-01") == 1


def test_v295_single_match_missing_date_resolves_fixture_or_blocks_cleanly(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mod,
        "resolve_fixture_date",
        lambda *args, **kwargs: {"resolver_status": "NOT_FOUND", "reason": "No fixture rows found"},
    )

    result = mod.audit_goal_difference_sources(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        output_dir=tmp_path,
    )

    assert result["v295_goal_difference_source_audit_status"] == "DATA_BLOCKED"
    assert result["reason"] == "match_date missing and fixture could not be resolved"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
