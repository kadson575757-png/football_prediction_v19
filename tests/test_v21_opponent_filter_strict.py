import pandas as pd

from football_prediction_v19.analysis.v21_canonical_match_resolver import resolve_canonical_match


def test_v21_opponent_filter_strict(tmp_path):
    catalog = tmp_path / "catalog.csv"
    pd.DataFrame([
        {"canonical_match_id": "ars_che", "match_date": "2025-08-23", "home_team": "Arsenal", "away_team": "Chelsea"},
        {"canonical_match_id": "ars_lee", "match_date": "2025-08-30", "home_team": "Arsenal", "away_team": "Leeds United"},
    ]).to_csv(catalog, index=False)
    result = resolve_canonical_match("Arsenal", "Chelsea", "Premier League", "2025/26", "", catalog_path=catalog)
    assert len(result.candidate_matches) == 1
    assert result.candidate_matches[0]["away_team"] == "Chelsea"
    assert len(result.related_suggestions) == 1
