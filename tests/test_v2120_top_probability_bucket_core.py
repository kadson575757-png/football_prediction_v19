from football_prediction_v19.analysis.v2120_prediction_error_patterns import top_probability_bucket


def test_top_probability_bucket_boundaries():
    assert top_probability_bucket(0.349) == "TOP_PROB_LT_035"
    assert top_probability_bucket(0.35) == "TOP_PROB_035_040"
    assert top_probability_bucket(0.40) == "TOP_PROB_040_045"
    assert top_probability_bucket(0.45) == "TOP_PROB_045_050"
    assert top_probability_bucket(0.50) == "TOP_PROB_045_050"
    assert top_probability_bucket(0.501) == "TOP_PROB_GT_050"
