from scripts.run_v20_historical_internet_prediction import run_v20_historical_internet_prediction


def _kwargs(tmp_path, **extra):
    data = {
        "home_team": "Demo Home",
        "away_team": "Demo Away",
        "competition": "Demo League",
        "season": "2025/26",
        "match_date": "2026-02-14",
        "cutoff_policy": "MATCH_DATE_START",
        "source_profile": "config/v20_internet_sources.yaml",
        "output_dir": tmp_path / "out",
        "base_dir": ".",
    }
    data.update(extra)
    return data


def test_runner_mock_mode_still_works(tmp_path):
    result = run_v20_historical_internet_prediction(**_kwargs(tmp_path, mock_data_dir="tests/fixtures/v20_historical_internet_prediction"))
    assert result["live_source_status"] == "MOCK_MODE"
    assert result["decision_class"] in {"MODEL_TIP", "ANALYST_LEAN", "NO_BET"}
    assert result["network_calls_enabled"] is False


def test_runner_cache_only_does_not_use_network_and_blocks_when_cache_missing(tmp_path):
    result = run_v20_historical_internet_prediction(**_kwargs(tmp_path, output_dir=tmp_path / "cache_only", cache_only=True, cache_dir=tmp_path / "cache"))
    assert result["live_source_status"] == "LIVE_SOURCES_BLOCKED"
    assert result["network_calls_enabled"] is False
    assert result["decision_class"] in {"NO_BET", "DATA_BLOCKED"}
