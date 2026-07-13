import football_prediction_v19.analysis.v2126_external_league_edge_calibration as module


def test_external_module_has_fixed_configuration_and_no_selection_api():
    assert module.FIXED_CONFIGURATION == "HIGH_EDGE_SHARPEN_005"
    assert not hasattr(module, "select_best_configuration")
    assert not hasattr(module, "choose_configuration")
