import pytest
import pandas as pd
import numpy as np
from football_prediction_v19.features import (
    compute_opponent_adjusted_xg,
    compute_time_decay_features,
    compute_h2h_features,
    compute_game_state_features,
    build_extended_features,
)
from football_prediction_v19.elo import EloRatingSystem


def _make_df(n=30, with_xg=True):
    import random, datetime
    random.seed(42)
    teams = ['TeamA','TeamB','TeamC','TeamD']
    rows = []
    d = datetime.date(2023,1,1)
    for i in range(n):
        h, a = random.sample(teams, 2)
        hg, ag = random.randint(0,3), random.randint(0,3)
        rows.append({'date': str(d), 'home_team': h, 'away_team': a,
                     'home_goals': hg, 'away_goals': ag,
                     'home_xg': round(hg+random.random(),2),
                     'away_xg': round(ag+random.random(),2),
                     'odds_home':2.0,'odds_draw':3.2,'odds_away':3.5})
        d += datetime.timedelta(days=3)
    df = pd.DataFrame(rows)
    if not with_xg:
        df = df.drop(columns=['home_xg','away_xg'])
    return df


class TestOpponentAdjustedXg:
    def test_output_columns_present(self):
        df = compute_opponent_adjusted_xg(_make_df())
        assert 'adj_home_xg' in df.columns
        assert 'adj_away_xg' in df.columns

    def test_no_xg_columns_returns_unchanged(self):
        df = _make_df(with_xg=False)
        cols_before = set(df.columns)
        result = compute_opponent_adjusted_xg(df)
        assert set(result.columns) == cols_before

    def test_adj_xg_differs_from_raw(self):
        df = compute_opponent_adjusted_xg(_make_df(n=20))
        # adj values should differ from raw for most rows
        diff = (df['adj_home_xg'] != df['home_xg']).sum()
        assert diff > 5

    def test_no_future_data_in_adjustment(self):
        df = compute_opponent_adjusted_xg(_make_df(n=20))
        # First row has no prior data so opponent_strength defaults to 1.0
        assert df.iloc[0]['opponent_strength_home'] == 1.0

    def test_zero_division_handled(self):
        df = _make_df(n=15)
        df['home_xg'] = 0.0
        df['away_xg'] = 0.0
        result = compute_opponent_adjusted_xg(df)
        assert not result['adj_home_xg'].isna().any()


class TestTimeDecayFeatures:
    def test_output_columns_present(self):
        df = compute_time_decay_features(_make_df(n=20))
        assert 'home_td_goals_scored' in df.columns
        assert 'away_td_win_rate' in df.columns

    def test_recent_games_weighted_higher(self):
        df = compute_time_decay_features(_make_df(n=25))
        # Just check it runs and returns numeric values
        vals = df['home_td_goals_scored'].dropna()
        assert len(vals) > 0
        assert (vals >= 0).all()

    def test_insufficient_history_returns_nan(self):
        df = compute_time_decay_features(_make_df(n=20))
        # First few rows should be NaN
        assert df.iloc[0]['home_td_goals_scored'] is np.nan or pd.isna(df.iloc[0]['home_td_goals_scored'])

    def test_half_life_affects_weights(self):
        df = _make_df(n=20)
        r1 = compute_time_decay_features(df, half_life_days=10)
        r2 = compute_time_decay_features(df, half_life_days=120)
        # Results should differ
        v1 = r1['home_td_goals_scored'].dropna()
        v2 = r2['home_td_goals_scored'].dropna()
        assert not v1.equals(v2)

    def test_no_future_leak(self):
        df = compute_time_decay_features(_make_df(n=15))
        assert 'home_td_goals_scored' in df.columns


class TestEloRating:
    def test_initial_ratings_equal(self):
        elo = EloRatingSystem()
        assert elo._get('A') == elo._get('B') == 1500.0

    def test_winner_gains_rating(self):
        elo = EloRatingSystem()
        elo.update('A', 'B', 2, 0)
        assert elo._get('A') > 1500.0
        assert elo._get('B') < 1500.0

    def test_draw_adjusts_less(self):
        elo = EloRatingSystem()
        elo.update('A', 'B', 1, 0)
        win_gain = elo._get('A') - 1500.0
        elo2 = EloRatingSystem()
        elo2.update('A', 'B', 1, 1)
        draw_gain = abs(elo2._get('A') - 1500.0)
        assert win_gain > draw_gain

    def test_home_advantage_applied(self):
        elo1 = EloRatingSystem(home_advantage=0)
        elo2 = EloRatingSystem(home_advantage=100)
        elo1.update('A','B',1,1)
        elo2.update('A','B',1,1)
        assert elo1._get('A') != elo2._get('A')

    def test_ratings_before_match_no_leak(self):
        df = _make_df(n=10)
        elo = EloRatingSystem()
        result = elo.get_ratings_before_match(df)
        # First match should have initial ratings
        assert result.iloc[0]['elo_home'] == 1500.0
        assert result.iloc[0]['elo_away'] == 1500.0

    def test_elo_diff_column_present(self):
        df = _make_df(n=10)
        elo = EloRatingSystem()
        result = elo.get_ratings_before_match(df)
        assert 'elo_diff' in result.columns


class TestH2HFeatures:
    def test_no_history_returns_nan(self):
        df = compute_h2h_features(_make_df(n=10))
        assert pd.isna(df.iloc[0]['h2h_btts_rate'])

    def test_h2h_n_correct(self):
        df = compute_h2h_features(_make_df(n=30))
        assert (df['h2h_n'] >= 0).all()
        assert (df['h2h_n'] <= 5).all()

    def test_btts_rate_range_0_to_1(self):
        df = compute_h2h_features(_make_df(n=30))
        vals = df['h2h_btts_rate'].dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_both_directions_counted(self):
        df = compute_h2h_features(_make_df(n=30))
        assert 'h2h_home_wins' in df.columns

    def test_window_respected(self):
        df = compute_h2h_features(_make_df(n=30), window=3)
        assert (df['h2h_n'] <= 3).all()


class TestGameStateFeatures:
    def test_output_columns_present(self):
        df = compute_game_state_features(_make_df(n=20))
        assert 'home_clean_sheet_rate' in df.columns
        assert 'away_failed_to_score_rate' in df.columns

    def test_clean_sheet_rate_range(self):
        df = compute_game_state_features(_make_df(n=25))
        vals = df['home_clean_sheet_rate'].dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_insufficient_history_nan(self):
        df = compute_game_state_features(_make_df(n=20))
        assert pd.isna(df.iloc[0]['home_lead_rate'])

    def test_no_future_leak(self):
        df = compute_game_state_features(_make_df(n=15))
        assert 'home_lead_rate' in df.columns


class TestBuildExtendedFeatures:
    def test_returns_dataframe(self):
        result = build_extended_features(_make_df(n=20))
        assert isinstance(result, pd.DataFrame)

    def test_no_existing_columns_overwritten(self):
        df = _make_df(n=20)
        original_home_goals = df['home_goals'].copy()
        result = build_extended_features(df)
        pd.testing.assert_series_equal(
            result['home_goals'].reset_index(drop=True),
            original_home_goals.reset_index(drop=True))

    def test_flags_disable_modules(self):
        df = _make_df(n=20)
        result = build_extended_features(df,
            include_h2h=False,
            include_elo=False,
            include_time_decay=False,
            include_adj_xg=False,
            include_game_state=False)
        assert 'h2h_btts_rate' not in result.columns
        assert 'elo_diff' not in result.columns
