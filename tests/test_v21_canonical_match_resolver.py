import pandas as pd

from football_prediction_v19.analysis.v21_canonical_match_resolver import resolve_canonical_match


def test_v21_canonical_match_resolver(tmp_path):
    catalog = tmp_path / "catalog.csv"
    pd.DataFrame([{"canonical_match_id": "pl_ars_lee", "match_date": "2025-08-23", "home_team": "Arsenal", "away_team": "Leeds United", "prediction_tier": "TIER_1_FULL_XG"}]).to_csv(catalog, index=False)
    result = resolve_canonical_match("Arsenal", "Leeds", "Premier League", "2025/26", "23/08/2025", catalog_path=catalog, output_dir=tmp_path)
    assert result.status == "RESOLVED"
    assert result.canonical_match_id == "pl_ars_lee"
