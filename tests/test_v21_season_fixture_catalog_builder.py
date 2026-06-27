from pathlib import Path

from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog


def test_v21_season_fixture_catalog_builder(tmp_path):
    result = build_v21_season_fixture_catalog("Premier League", "2025/26", tmp_path, mock_data_dir="tests/fixtures/v20_live_source_adapters")
    assert result["v21_season_fixture_catalog_status"] == "READY"
    assert result["matches_total"] > 0
    assert Path(result["season_fixture_catalog_csv_path"]).exists()
