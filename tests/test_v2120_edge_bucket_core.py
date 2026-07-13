from football_prediction_v19.analysis.v2120_prediction_error_patterns import edge_bucket


def test_edge_bucket_boundaries():
    assert edge_bucket(0.03) == "EDGE_0_03"
    assert edge_bucket(0.031) == "EDGE_0_05"
    assert edge_bucket(0.08) == "EDGE_0_08"
    assert edge_bucket(0.10) == "EDGE_0_10"
    assert edge_bucket(0.15) == "EDGE_0_15"
    assert edge_bucket(0.151) == "EDGE_GT_15"
