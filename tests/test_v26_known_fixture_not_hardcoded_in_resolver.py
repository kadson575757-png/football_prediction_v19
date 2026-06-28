from pathlib import Path


def test_v26_known_fixture_not_hardcoded_in_resolver():
    text = Path("src/football_prediction_v19/analysis/v26_fixture_date_resolver.py").read_text(encoding="utf-8")
    assert "2026-03-01" not in text
    assert "Arsenal" not in text

