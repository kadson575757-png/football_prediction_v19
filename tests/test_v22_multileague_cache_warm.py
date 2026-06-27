from scripts.warm_v22_multileague_cache import warm_v22_multileague_cache
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_multileague_cache_warm(tmp_path):
    result = warm_v22_multileague_cache(season="2025/26", competitions="Premier League,Bundesliga", output_dir=str(tmp_path / "out"), mock_data_dir=str(make_mock_source_dir(tmp_path)))
    assert result["v22_cache_warm_status"] == "READY"
    assert result["leagues_requested"] == 2
