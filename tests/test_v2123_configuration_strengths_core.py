from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import build_configurations


def test_nine_configuration_strength_and_history_combinations():
    configurations = build_configurations()
    assert len(configurations) == 9
    assert {item["correction_strength"] for item in configurations} == {0.005, 0.01, 0.015}
    assert {item["minimum_history"] for item in configurations} == {5, 8, 10}
    assert len({item["configuration"] for item in configurations}) == 9
