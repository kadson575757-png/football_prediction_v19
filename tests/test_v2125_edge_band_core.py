from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import v2124_edge_band


def test_v2125_edge_band_boundaries():
    assert v2124_edge_band(0.03) == "EDGE_0_03"
    assert v2124_edge_band(0.04) == "EDGE_3_05"
    assert v2124_edge_band(0.07) == "EDGE_5_08"
    assert v2124_edge_band(0.09) == "EDGE_8_10"
    assert v2124_edge_band(0.12) == "EDGE_10_15"
    assert v2124_edge_band(0.16) == "EDGE_GT_15"
