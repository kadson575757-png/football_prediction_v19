import pandas as pd

from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_corpus_xg_join_when_available(tmp_path):
    result = build_real_season_corpus("Premier League", "2025/26", tmp_path / "out", mock_data_dir=make_mock_source_dir(tmp_path))
    corpus = pd.read_csv(result["real_season_corpus_csv_path"])
    assert corpus["xg_available"].astype(bool).mean() > 0
