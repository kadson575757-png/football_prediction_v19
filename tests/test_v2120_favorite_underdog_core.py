from football_prediction_v19.analysis.v2120_prediction_error_patterns import favorite_gap_bucket, favorite_side


def test_favorite_side_and_gap_buckets():
    assert favorite_side(0.45, 0.43) == "BALANCED"
    assert favorite_side(0.45, 0.42) == "BALANCED"
    assert favorite_side(0.50, 0.40) == "HOME"
    assert favorite_side(0.35, 0.45) == "AWAY"
    assert favorite_gap_bucket(0.45, 0.43) == "BALANCED"
    assert favorite_gap_bucket(0.45, 0.41) == "SMALL_FAVORITE_GAP"
    assert favorite_gap_bucket(0.50, 0.42) == "MEDIUM_FAVORITE_GAP"
    assert favorite_gap_bucket(0.55, 0.40) == "LARGE_FAVORITE_GAP"
