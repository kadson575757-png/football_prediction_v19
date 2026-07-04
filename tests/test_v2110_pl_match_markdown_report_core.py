from scripts.run_v2110_premier_league_2025_26_full_season_analysis import render_match_markdown_report


def test_v2110_match_markdown_report_contains_required_sections_and_safety():
    markdown = render_match_markdown_report({
        "competition": "Premier League",
        "season": "2025/26",
        "match_date": "2025-08-16",
        "as_of_date": "2025-08-15",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "fixture_source": "football_data",
        "home_win_probability": 0.42,
        "draw_probability": 0.30,
        "away_win_probability": 0.28,
        "top_probability_outcome": "HOME",
        "probability_edge": 0.12,
        "probability_edge_band": "MEDIUM",
        "uncertainty_level": "MEDIUM",
        "data_quality_band": "PARTIAL",
        "xg_available": False,
        "odds_available": False,
        "source_quality_band": "PARTIAL",
        "asof_guard_status": "CLEAN",
        "leakage_warning": False,
    })

    assert "## Match" in markdown
    assert "## Final Probability Output" in markdown
    assert "## Indicator Quality Table" in markdown
    assert "## Shadow Probability Table" in markdown
    assert "## Mix Table" in markdown
    assert "automatic_betting_enabled=false" in markdown
    assert "staking_logic_enabled=false" in markdown
    assert "roi_logic_enabled=false" in markdown
    lowered = markdown.lower()
    assert "profit" not in lowered
    assert "yield" not in lowered
    assert "bankroll" not in lowered

