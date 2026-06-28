import pandas as pd

from football_prediction_v19.analysis.v27_result_resolver import resolve_match_result


def test_v27_result_resolver_mock_home_draw_away(tmp_path):
    corpus = tmp_path / "corpus.csv"
    pd.DataFrame(
        [
            {"competition": "Premier League", "season": "2025/26", "match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 1},
            {"competition": "Premier League", "season": "2025/26", "match_date": "2026-03-02", "home_team": "Liverpool", "away_team": "Everton", "home_goals": 1, "away_goals": 1},
            {"competition": "Premier League", "season": "2025/26", "match_date": "2026-03-03", "home_team": "Fulham", "away_team": "Arsenal", "home_goals": 0, "away_goals": 3},
        ]
    ).to_csv(corpus, index=False)

    assert resolve_match_result("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01", corpus_path=corpus)["result"] == "HOME_WIN"
    assert resolve_match_result("Premier League", "2025/26", "Liverpool", "Everton", "2026-03-02", corpus_path=corpus)["result"] == "DRAW"
    assert resolve_match_result("Premier League", "2025/26", "Fulham", "Arsenal", "2026-03-03", corpus_path=corpus)["result"] == "AWAY_WIN"


def test_v27_result_resolver_no_network_without_enable_network(monkeypatch, tmp_path):
    corpus = tmp_path / "empty.csv"
    pd.DataFrame(columns=["competition", "season", "match_date", "home_team", "away_team"]).to_csv(corpus, index=False)

    def fail_live_adapter(*args, **kwargs):
        raise AssertionError("network fallback must not run without enable_network")

    monkeypatch.setattr("football_prediction_v19.analysis.v27_result_resolver.run_football_data_live_adapter", fail_live_adapter)
    result = resolve_match_result("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01", corpus_path=corpus, enable_network=False)
    assert result["result_status"] == "NOT_FOUND"
    assert result["result"] == "RESULT_UNKNOWN"

