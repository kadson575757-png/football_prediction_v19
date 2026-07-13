import pytest

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import normalize_probabilities


def test_probability_normalization_clips_and_sums_exactly_to_one():
    probabilities = normalize_probabilities(1.2, -0.1, 0.4)
    assert all(0.0 <= value <= 1.0 for value in probabilities)
    assert sum(probabilities) == 1.0
