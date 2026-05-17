# -*- coding: utf-8 -*-
"""Helper: append totals-odds test classes to test_smoke.py."""
from pathlib import Path

NEW_TESTS = '''

class TestImportTotalsOdds:
    """Tests for import_totals_odds flexible column aliasing."""

    def _write_csv(self, rows):
        import tempfile
        import csv
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        )
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        f.close()
        return f.name

    def test_canonical_column_names(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "odds_over25": 1.85, "odds_under25": 2.05,
        }])
        try:
            df = import_totals_odds(path)
            assert len(df) == 1
            assert abs(df["odds_over25"].iloc[0] - 1.85) < 0.01
            assert abs(df["odds_under25"].iloc[0] - 2.05) < 0.01
        finally:
            Path(path).unlink(missing_ok=True)

    def test_over25_alias_O25(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "Date": "2024-03-10", "Home": "Arsenal", "Away": "Chelsea",
            "O2.5": 1.88, "U2.5": 2.00,
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].iloc[0] == 1.88
        finally:
            Path(path).unlink(missing_ok=True)

    def test_over25_alias_Over25(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "Home Team": "Arsenal", "Away Team": "Chelsea",
            "Over25": 1.90, "Under25": 1.95,
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].iloc[0] == 1.90
        finally:
            Path(path).unlink(missing_ok=True)

    def test_over25_alias_over_25_odds(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "match_date": "2024-03-10", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea",
            "over_25_odds": 1.75, "under_25_odds": 2.10,
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].iloc[0] == 1.75
        finally:
            Path(path).unlink(missing_ok=True)

    def test_over25_alias_BbAv(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "Date": "2024-03-10", "Home": "Man Utd", "Away": "Liverpool",
            "BbAv>2.5": 1.82, "BbAv<2.5": 2.08,
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].iloc[0] == 1.82
        finally:
            Path(path).unlink(missing_ok=True)

    def test_over25_alias_B365(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "Date": "2024-03-10", "Home": "Arsenal", "Away": "Chelsea",
            "B365>2.5": 1.80, "B365<2.5": 2.10,
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].iloc[0] == 1.80
        finally:
            Path(path).unlink(missing_ok=True)

    def test_under25_optional(self):
        """Under 2.5 column missing -> odds_under25 is NaN."""
        import numpy as np
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "over_25_odds": 1.85,
        }])
        try:
            df = import_totals_odds(path)
            assert "odds_under25" in df.columns
            assert np.isnan(df["odds_under25"].iloc[0])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_numeric_conversion(self):
        """String odds values are coerced to float."""
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "over_25_odds": "1.85", "under_25_odds": "2.05",
        }])
        try:
            df = import_totals_odds(path)
            assert df["odds_over25"].dtype == float
        finally:
            Path(path).unlink(missing_ok=True)

    def test_team_alias_normalization(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Man Utd", "away_team": "Spurs",
            "over_25_odds": 1.85,
        }])
        try:
            df = import_totals_odds(path)
            assert df["home_team"].iloc[0] == "Manchester United"
            assert df["away_team"].iloc[0] == "Tottenham Hotspur"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_over25_column_raises(self):
        import pytest
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "odds_home": 1.80,
        }])
        try:
            with pytest.raises(ValueError, match="Over 2.5"):
                import_totals_odds(path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_market_default_totals(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "over_25_odds": 1.85,
        }])
        try:
            df = import_totals_odds(path)
            assert df["market"].iloc[0] == "totals"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_output_written(self):
        import tempfile
        import pandas as pd
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import import_totals_odds
        path = self._write_csv([{
            "date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
            "over_25_odds": 1.85,
        }])
        out = tempfile.mktemp(suffix=".csv")
        try:
            import_totals_odds(path, output_path=out)
            assert Path(out).exists()
            df2 = pd.read_csv(out)
            assert "odds_over25" in df2.columns
        finally:
            Path(path).unlink(missing_ok=True)
            Path(out).unlink(missing_ok=True)


class TestMergeTotalsOdds:
    """Tests for merge_totals_odds match-and-fill behaviour."""

    def _write_csv(self, rows):
        import tempfile
        import csv
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        )
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        f.close()
        return f.name

    def _matches_csv(self):
        return self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1},
            {"date": "2024-03-11", "home_team": "Liverpool", "away_team": "Man City",
             "home_goals": 1, "away_goals": 1},
            {"date": "2024-03-17", "home_team": "Tottenham Hotspur", "away_team": "Aston Villa",
             "home_goals": 0, "away_goals": 0},
        ])

    def _odds_csv(self):
        return self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "odds_over25": 1.85, "odds_under25": 2.05},
            {"date": "2024-03-11", "home_team": "Liverpool", "away_team": "Manchester City",
             "odds_over25": 1.72, "odds_under25": 2.20},
        ])

    def test_merge_same_date(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp, op = self._matches_csv(), self._odds_csv()
        try:
            df, stats = merge_totals_odds(mp, op)
            assert stats["matched"] == 2
            row = df[df["home_team"].str.contains("Arsenal")].iloc[0]
            assert abs(row["odds_over25"] - 1.85) < 0.01
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_team_alias_resolves_on_merge(self):
        """Odds file using alias 'Man City' matches matches file 'Manchester City'."""
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp = self._matches_csv()
        op = self._write_csv([
            {"date": "2024-03-11", "home_team": "Liverpool", "away_team": "Man City",
             "odds_over25": 1.72, "odds_under25": 2.20},
        ])
        try:
            df, stats = merge_totals_odds(mp, op)
            assert stats["matched"] == 1
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_unmatched_rows_preserved(self):
        import numpy as np
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp, op = self._matches_csv(), self._odds_csv()
        try:
            df, stats = merge_totals_odds(mp, op)
            assert len(df) == 3
            spurs_row = df[df["home_team"].str.contains("Tottenham")].iloc[0]
            assert np.isnan(spurs_row["odds_over25"])
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_date_window_match(self):
        """Odds dated 1 day off still match within default 2-day window."""
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp = self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1},
        ])
        op = self._write_csv([
            {"date": "2024-03-11", "home_team": "Arsenal", "away_team": "Chelsea",
             "odds_over25": 1.85, "odds_under25": 2.05},
        ])
        try:
            df, stats = merge_totals_odds(mp, op, date_window=2)
            assert stats["matched"] == 1
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_no_overwrite_by_default(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp = self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1, "odds_over25": 1.70, "odds_under25": 2.30},
        ])
        op = self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "odds_over25": 1.99, "odds_under25": 1.85},
        ])
        try:
            df, stats = merge_totals_odds(mp, op, overwrite=False)
            assert stats["skipped_non_null"] == 1
            assert abs(df["odds_over25"].iloc[0] - 1.70) < 0.01
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_overwrite_flag(self):
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp = self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "home_goals": 2, "away_goals": 1, "odds_over25": 1.70},
        ])
        op = self._write_csv([
            {"date": "2024-03-10", "home_team": "Arsenal", "away_team": "Chelsea",
             "odds_over25": 1.99},
        ])
        try:
            df, stats = merge_totals_odds(mp, op, overwrite=True)
            assert abs(df["odds_over25"].iloc[0] - 1.99) < 0.01
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)

    def test_output_written(self):
        import tempfile
        import pandas as pd
        from pathlib import Path
        from football_prediction_v19.importers.historical_odds import merge_totals_odds
        mp, op = self._matches_csv(), self._odds_csv()
        out = tempfile.mktemp(suffix=".csv")
        try:
            merge_totals_odds(mp, op, output_path=out)
            assert Path(out).exists()
            df2 = pd.read_csv(out)
            assert "odds_over25" in df2.columns
        finally:
            Path(mp).unlink(missing_ok=True)
            Path(op).unlink(missing_ok=True)
            Path(out).unlink(missing_ok=True)
'''

dest = Path(__file__).resolve().parents[1] / "tests" / "test_smoke.py"
current = dest.read_text(encoding="utf-8")
dest.write_text(current + NEW_TESTS, encoding="utf-8")
print(f"Appended {len(NEW_TESTS.splitlines())} lines to {dest}")
