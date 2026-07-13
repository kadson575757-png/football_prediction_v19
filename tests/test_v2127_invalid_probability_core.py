import math

from football_prediction_v19.analysis.v2127_edge_calibration_integration import _invalid_probabilities


def test_invalid_probability_detection():
    assert _invalid_probabilities((-0.1, 0.5, 0.6))
    assert _invalid_probabilities((0.2, math.nan, 0.8))
    assert _invalid_probabilities((0.2, math.inf, 0.8))
    assert not _invalid_probabilities((0.2, 0.3, 0.5))
