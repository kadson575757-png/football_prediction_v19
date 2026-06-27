from pathlib import Path

from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_real_season_corpus_builder(tmp_path):
    result = build_real_season_corpus("Premier League", "2025/26", tmp_path / "out", mock_data_dir=make_mock_source_dir(tmp_path))
    assert result["v22_real_season_corpus_status"] == "READY"
    assert Path(result["real_season_corpus_csv_path"]).exists()
