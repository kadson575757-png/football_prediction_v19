import pandas as pd
import pytest

from football_prediction_v19.analysis.v2127_edge_calibration_integration import (
    analyze_edge_calibration_integration,
    apply_edge_calibration_integration,
    determine_integration_status,
    prepare_integration_rows,
)


def _row(probabilities, edge=0.05):
    home, draw, away = probabilities
    return {
        "actual_result": "HOME",
        "top_probability_outcome": "HOME",
        "home_win_probability": home,
        "draw_probability": draw,
        "away_probability": away,
        "probability_edge": edge,
    }


@pytest.mark.parametrize("probabilities, expected_sum", [
    ((0.5000, 0.2999, 0.2000), 0.9999),
    ((0.5000, 0.3001, 0.2000), 1.0001),
])
def test_rounded_unchanged_source_preserves_sum_without_new_error(probabilities, expected_sum):
    prepared = prepare_integration_rows(pd.DataFrame([_row(probabilities)]))
    result, audit = apply_edge_calibration_integration(prepared)
    row = result.iloc[0]
    assert not row["edge_calibration_applied"]
    assert row["source_probability_sum"] == pytest.approx(expected_sum)
    assert row["calibrated_probability_sum"] == pytest.approx(expected_sum)
    assert row["introduced_probability_sum_error"] <= 1e-12
    assert audit.iloc[0]["introduced_probability_sum_error"] <= 1e-12


def test_applied_row_is_normalized_to_one():
    prepared = prepare_integration_rows(pd.DataFrame([_row((0.5500, 0.2700, 0.1801), edge=0.28)]))
    result, _ = apply_edge_calibration_integration(prepared)
    row = result.iloc[0]
    assert row["edge_calibration_applied"]
    assert row["calibrated_probability_sum_error"] <= 1e-12


def test_existing_source_rounding_error_does_not_fail_integration(tmp_path):
    high_edge = _row((0.5500, 0.2700, 0.1800), edge=0.28)
    rounded_low_edge = _row((0.5000, 0.2999, 0.2000))
    result = analyze_edge_calibration_integration(
        pd.DataFrame([high_edge, rounded_low_edge]),
        pd.DataFrame([high_edge, rounded_low_edge]),
        output_dir=tmp_path,
    )
    assert result["source_sum_warning_count"] == 2
    assert result["unchanged_sum_regression_count"] == 0
    assert result["integration_probe_status"] == "INTEGRATION_PROBE_PASSED"


def test_newly_introduced_sum_error_still_fails_parity():
    metrics = {"brier_improvement": 0.001, "hit_rate_delta": 0.0}
    parity = {
        "base_probability_parity_mismatch_count": 0,
        "unchanged_row_mismatch_count": 0,
        "calibration_formula_mismatch_count": 0,
        "invalid_probability_count": 0,
        "maximum_unchanged_introduced_sum_error": 0.0001,
        "maximum_applied_calibrated_sum_error": 0.0,
        "applied_sum_failure_count": 0,
        "unchanged_sum_regression_count": 1,
    }
    status, _ = determine_integration_status(metrics, metrics, metrics, parity)
    assert status == "INTEGRATION_PROBE_PARITY_FAILED"
