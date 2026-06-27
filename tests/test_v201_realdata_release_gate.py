from football_prediction_v19.analysis.v201_realdata_release_gate import run_v201_realdata_release_gate


def test_v201_realdata_release_gate_ready(tmp_path):
    result = run_v201_realdata_release_gate(tmp_path)
    assert result["v201_realdata_release_gate_status"] == "V201_READY_TO_TAG_REALDATA_PREVIEW"
    assert result["recommendation"] == "V201_READY_TO_TAG_REALDATA_PREVIEW"
