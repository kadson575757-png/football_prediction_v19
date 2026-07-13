import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import evaluate_edge_calibration_status


def test_stability_evaluation_robust_unstable_and_not_helpful():
    robust = pd.DataFrame([
        {"brier_improvement": 0.01, "hit_rate_delta": 0.0, "net_corrected_count": 0},
        {"brier_improvement": 0.02, "hit_rate_delta": -0.001, "net_corrected_count": 1},
        {"brier_improvement": -0.001, "hit_rate_delta": 0.0, "net_corrected_count": 0},
    ])
    assert evaluate_edge_calibration_status(robust)[0] == "EDGE_CALIBRATION_ROBUST"
    unstable = robust.copy()
    unstable.loc[1, "brier_improvement"] = -0.001
    assert evaluate_edge_calibration_status(unstable)[0] == "EDGE_CALIBRATION_UNSTABLE"
    not_helpful = robust.copy()
    not_helpful["brier_improvement"] = -0.01
    assert evaluate_edge_calibration_status(not_helpful)[0] == "EDGE_CALIBRATION_NOT_HELPFUL"
