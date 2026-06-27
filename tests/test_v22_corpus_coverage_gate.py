from football_prediction_v19.analysis.v22_corpus_coverage_gate import run_v22_corpus_coverage_gate


def test_v22_corpus_coverage_gate(tmp_path):
    result = run_v22_corpus_coverage_gate(tmp_path / "gate")
    assert result["v22_corpus_coverage_gate_status"] == "V22_READY_TO_TAG"
    assert result["recommendation"] == "V22_READY_TO_TAG"

