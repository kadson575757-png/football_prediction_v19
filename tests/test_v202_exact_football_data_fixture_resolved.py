import pandas as pd

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_real_fixture_resolver import resolve_real_fixture


def test_v202_exact_football_data_fixture_resolved(tmp_path):
    csv = tmp_path / "football.csv"
    pd.DataFrame([{"Date": "2025-08-23", "HomeTeam": "Arsenal", "AwayTeam": "Leeds", "FTHG": "", "FTAG": "", "FTR": ""}]).to_csv(csv, index=False)
    ctx = resolve_analysis_cutoff(build_match_context("Arsenal", "Leeds", "Premier League", "2025/26", "2025-08-23"))
    result = resolve_real_fixture(ctx, {"football_data": str(csv)}, tmp_path)
    assert result.fixture_resolution_status == "RESOLVED"
    assert result.exact_match_found is True
