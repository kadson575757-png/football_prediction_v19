import pandas as pd

from scripts.run_v2110_premier_league_2025_26_full_season_analysis import build_pl_fixture_list


def test_v2110_pl_fixture_list_deduplicates_and_reports_coverage():
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea"},
        {"match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea"},
        {"match_date": "2025-08-17", "home_team": "Liverpool", "away_team": "Everton"},
    ])

    unique, summary = build_pl_fixture_list(fixtures, expected_count=4)

    assert len(unique) == 2
    assert summary["fixtures_found"] == 3
    assert summary["fixtures_unique"] == 2
    assert summary["duplicate_count"] == 1
    assert summary["expected_fixture_count"] == 4
    assert summary["fixture_coverage_rate"] == 0.5
    assert summary["missing_fixture_warning"] is True

