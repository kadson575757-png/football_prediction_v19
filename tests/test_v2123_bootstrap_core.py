from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import paired_bootstrap


def test_paired_bootstrap_is_deterministic_with_fixed_seed():
    improvements = [0.01, 0.02, -0.01, 0.03, 0.00]
    first = paired_bootstrap(improvements, repetitions=500, seed=123)
    second = paired_bootstrap(improvements, repetitions=500, seed=123)
    assert first == second
    assert first["bootstrap_ci_lower"] <= first["bootstrap_mean_improvement"] <= first["bootstrap_ci_upper"]
    assert 0.0 <= first["probability_improvement_positive"] <= 1.0
