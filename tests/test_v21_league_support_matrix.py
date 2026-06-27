from football_prediction_v19.analysis.v21_league_support import load_league_support_matrix, resolve_league_support, write_league_support_outputs


def test_v21_league_support_matrix(tmp_path):
    entries = load_league_support_matrix()
    names = {entry.canonical_name for entry in entries}
    assert {"Premier League", "Bundesliga", "Serie A", "La Liga", "Ligue 1"}.issubset(names)
    assert resolve_league_support("Premier League").prediction_tier == "TIER_1_FULL_XG"
    paths = write_league_support_outputs(tmp_path)
    assert paths["league_support_matrix_csv_path"].endswith("league_support_matrix.csv")
