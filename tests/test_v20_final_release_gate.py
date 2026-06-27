from football_prediction_v19.analysis.v20_final_release_gate import run_v20_final_release_gate


def test_final_release_gate_ready(tmp_path):
    result = run_v20_final_release_gate(tmp_path, ".")
    assert result["v20_final_release_gate_status"] == "V20_READY_TO_TAG_PREVIEW"
    assert result["recommendation"] == "V20_READY_TO_TAG_PREVIEW"
