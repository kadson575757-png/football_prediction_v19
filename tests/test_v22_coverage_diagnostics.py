from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v22_coverage_diagnostics import write_coverage_diagnostics
from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_coverage_diagnostics(tmp_path):
    corpus = build_real_season_corpus(
        competition="Premier League",
        season="2025/26",
        output_dir=tmp_path / "corpus",
        mock_data_dir=str(make_mock_source_dir(tmp_path)),
    )
    result = write_coverage_diagnostics([corpus["real_season_corpus_csv_path"]], tmp_path / "diag")
    assert result["v22_coverage_diagnostics_status"] == "READY"
    frame = pd.read_csv(Path(result["coverage_by_league_path"]))
    assert "xg_join_rate" in frame.columns

