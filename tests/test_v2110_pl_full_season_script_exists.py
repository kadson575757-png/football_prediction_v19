from pathlib import Path


def test_v2110_full_season_script_exists_and_core_importable():
    path = Path("scripts/run_v2110_premier_league_2025_26_full_season_analysis.py")
    assert path.exists()

    from scripts.run_v2110_premier_league_2025_26_full_season_analysis import run_full_season_analysis

    assert callable(run_full_season_analysis)

