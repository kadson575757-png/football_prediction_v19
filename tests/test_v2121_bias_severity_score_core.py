import pandas as pd

from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import compute_bias_severity_summary


def test_bias_severity_score_formula_and_primary_area():
    home = pd.DataFrame([{"team": "Alpha", "home_overprediction_delta": 0.25, "home_top_miss_count": 3, "wrong_high_confidence_home_count": 2}])
    away = pd.DataFrame([{"team": "Alpha", "away_overprediction_delta": -0.10, "away_top_miss_count": 1, "wrong_high_confidence_away_count": 0}])
    involved = pd.DataFrame([{"team": "Alpha", "involved_miss_count": 4, "wrong_high_confidence_involved_count": 2}])
    alpha = compute_bias_severity_summary(home, away, involved).set_index("team").loc["Alpha"]
    assert alpha["home_bias_severity_score"] == 37.0
    assert alpha["away_bias_severity_score"] == 12.0
    assert alpha["involved_bias_severity_score"] == 14.0
    assert alpha["total_bias_severity_score"] == 63.0
    assert alpha["primary_bias_area"] == "HOME"
