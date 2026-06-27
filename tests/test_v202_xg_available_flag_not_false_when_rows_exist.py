import json

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v20_understat_live_adapter import run_understat_live_adapter


def test_v202_xg_available_flag_not_false_when_rows_exist(tmp_path):
    payload = tmp_path / "understat.json"
    payload.write_text(json.dumps({"matches": [{"date": "2025-08-10", "home_team": "Arsenal", "away_team": "Leeds", "home_xg": 2.0, "away_xg": 0.8}]}), encoding="utf-8")
    context = resolve_analysis_cutoff(build_match_context("Arsenal", "Leeds", "Premier League", "2025/26", "2025-08-23"))
    result = run_understat_live_adapter(resolve_source_league("Premier League", "2025/26"), context, tmp_path / "out", mock_json_path=payload)
    assert result["rows_count"] == 1
    assert result["xg_available"] is True
