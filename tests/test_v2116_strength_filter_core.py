import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import strength_filter_mask


def test_v2116_strength_filter_variants_remove_dissimilar_references():
    refs = pd.DataFrame([
        {"reference_home_strength_score": 1.2, "reference_away_strength_score": 0.8, "reference_strength_gap": 0.4, "reference_strength_quality": "READY"},
        {"reference_home_strength_score": 2.2, "reference_away_strength_score": 0.8, "reference_strength_gap": 1.4, "reference_strength_quality": "READY"},
    ])
    target = {"home_strength_score": 1.1, "away_strength_score": 0.9, "strength_gap": 0.2, "strength_quality": "READY"}
    assert strength_filter_mask(refs, target, "STRENGTH_HOME_AWAY").tolist() == [True, False]
    assert strength_filter_mask(refs, target, "STRENGTH_GAP_ONLY").tolist() == [True, False]
    assert strength_filter_mask(refs, target, "STRENGTH_LOOSE").tolist() == [True, False]
    assert strength_filter_mask(refs, target, "STRENGTH_STRICT").tolist() == [True, False]


def test_v2116_ready_only_filter_requires_ready_target_and_reference():
    refs = pd.DataFrame([
        {"reference_home_strength_score": 1.0, "reference_away_strength_score": 1.0, "reference_strength_gap": 0.0, "reference_strength_quality": "READY"},
        {"reference_home_strength_score": 1.0, "reference_away_strength_score": 1.0, "reference_strength_gap": 0.0, "reference_strength_quality": "LOW"},
    ])
    target = {"home_strength_score": 1.0, "away_strength_score": 1.0, "strength_gap": 0.0, "strength_quality": "READY"}
    assert strength_filter_mask(refs, target, "STRENGTH_READY_ONLY").tolist() == [True, False]
