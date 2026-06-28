import pandas as pd
from football_prediction_v19.analysis.v24_probability_diagnostics import write_probability_diagnostics


def test_v24_probability_diagnostics_empty_dataset_status(tmp_path):
    path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["home_win_probability", "draw_probability", "away_win_probability"]).to_csv(path, index=False)
    result = write_probability_diagnostics(path, tmp_path / "out")
    assert result["probability_diagnostics_status"] == "EMPTY_DATASET"
    assert "no probability rows available" in (tmp_path / "out" / "probability_distribution_diagnostics.md").read_text(encoding="utf-8")

