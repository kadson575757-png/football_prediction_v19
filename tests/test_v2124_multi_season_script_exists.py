from pathlib import Path


def test_v2124_script_exists_and_core_importable():
    assert Path("scripts/evaluate_v2124_pl_multi_season_robustness.py").exists()
    from scripts.evaluate_v2124_pl_multi_season_robustness import evaluate_v2124_pl_multi_season_robustness
    from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness

    assert callable(evaluate_v2124_pl_multi_season_robustness)
    assert callable(evaluate_pl_multi_season_robustness)
