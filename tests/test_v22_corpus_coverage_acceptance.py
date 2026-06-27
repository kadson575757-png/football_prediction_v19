from pathlib import Path

from football_prediction_v19.analysis.v22_corpus_coverage_gate import run_v22_corpus_coverage_gate


def test_v22_corpus_coverage_acceptance(tmp_path):
    run_v22_corpus_coverage_gate(tmp_path / "gate")
    assert Path(tmp_path / "gate" / "v22_corpus_coverage_gate_result.json").exists()
    assert Path(tmp_path / "gate" / "v22_corpus_coverage_gate_summary.csv").exists()

