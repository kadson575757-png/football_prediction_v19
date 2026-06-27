import pandas as pd

from football_prediction_v19.analysis.v23_data_block_audit import build_data_block_audit


def test_v23_data_block_audit_has_stage_and_reason(tmp_path):
    frame = pd.DataFrame([{"decision_class": "DATA_BLOCKED", "match_id": "m1", "actual_result": "", "home_team": "A", "away_team": "B", "block_reason_code": "result_missing_for_backtest"}])
    build_data_block_audit(frame, tmp_path)
    audit = pd.read_csv(tmp_path / "data_block_audit.csv")
    assert audit.loc[0, "block_stage"] == "CORPUS"
    assert audit.loc[0, "block_reason_code"] == "result_missing_for_backtest"

