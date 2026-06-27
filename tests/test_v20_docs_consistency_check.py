from football_prediction_v19.analysis.v20_docs_consistency_check import run_v20_docs_consistency_check


def test_docs_consistency_check_passes():
    assert run_v20_docs_consistency_check(".")["docs_consistency_status"] == "PASSED"
