import pandas as pd

from football_prediction_v19.analysis.v23_data_block_audit import build_data_block_audit


def test_v23_data_blocked_only_for_hard_reasons(tmp_path):
    frame = pd.DataFrame([{"decision_class": "DATA_BLOCKED", "actual_result": "", "block_reason_code": "result_missing_for_backtest"}])
    build_data_block_audit(frame, tmp_path)
    audit = pd.read_csv(tmp_path / "data_block_audit.csv")
    assert bool(audit.loc[0, "is_hard_block"])

