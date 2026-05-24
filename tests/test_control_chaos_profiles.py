from football_prediction_v19.diagnostics.control_chaos_profiles import build_control_chaos_profile


def base_row(**overrides):
    row = {
        "odds_home": 1.65,
        "odds_draw": 4.0,
        "odds_away": 5.0,
        "model_home_prob": 0.62,
        "model_draw_prob": 0.22,
        "model_away_prob": 0.16,
        "control_score": 7.4,
        "chaos_score": 2.2,
        "likely_1x2": "Home",
    }
    row.update(overrides)
    return row


def test_strong_home_favorite_high_control_low_chaos():
    profile = build_control_chaos_profile(base_row())

    assert profile["favorite_side"] == "HOME_FAVORITE"
    assert profile["home_favorite_strength"] == "strong_home_fav"
    assert profile["control_bucket"] == "HIGH"
    assert profile["chaos_bucket"] == "LOW"
    assert profile["probability_profile"] == "clean_home_favorite"
    assert profile["direction_read"] == "home_favorite_direction_strong"
    assert profile["goals_read"] == "under_3_5_compatible_not_automatic"
    assert profile["risk_warning"] == "low"
    assert profile["score_family"] == "2-0, 2-1, 3-0"


def test_strong_home_favorite_high_control_high_chaos():
    profile = build_control_chaos_profile(base_row(chaos_score=6.2))

    assert profile["probability_profile"] == "home_favorite_but_volatile"
    assert profile["direction_read"] == "home_favorite_direction_ok"
    assert profile["goals_read"] == "btts_or_upset_risk_elevated"
    assert profile["risk_warning"] == "medium_or_high"
    assert profile["score_family"] == "2-1, 3-1, 2-2"


def test_strong_away_favorite_high_control_low_chaos():
    profile = build_control_chaos_profile(
        base_row(
            odds_home=4.2,
            odds_draw=3.8,
            odds_away=1.85,
            model_home_prob=0.18,
            model_draw_prob=0.24,
            model_away_prob=0.58,
            likely_1x2="Away",
            chaos_score=2.5,
        )
    )

    assert profile["favorite_side"] == "AWAY_FAVORITE"
    assert profile["away_favorite_strength"] == "strong_away_fav"
    assert profile["probability_profile"] == "clean_away_favorite"
    assert profile["direction_read"] == "away_favorite_direction_strong"
    assert profile["goals_read"] == "over_2_5_more_interesting"
    assert profile["risk_warning"] == "low"
    assert profile["score_family"] == "0-2, 1-2, 1-3, 0-3"


def test_low_control_high_chaos():
    profile = build_control_chaos_profile(base_row(control_score=3.2, chaos_score=6.8))

    assert profile["control_bucket"] == "LOW"
    assert profile["chaos_bucket"] == "HIGH"
    assert profile["probability_profile"] == "dangerous_unclear"
    assert profile["direction_read"] == "weak_1x2_conviction"
    assert profile["goals_read"] == "btts_draw_upset_risk"
    assert profile["risk_warning"] == "high"


def test_low_control_low_chaos():
    profile = build_control_chaos_profile(base_row(control_score=3.2, chaos_score=2.4))

    assert profile["probability_profile"] == "low_conviction_calm"
    assert profile["direction_read"] == "weak_direction"
    assert profile["goals_read"] == "unclear_or_low_event"
    assert profile["risk_warning"] == "medium"


def test_missing_odds_handled_gracefully():
    profile = build_control_chaos_profile(base_row(odds_home=None, odds_draw=None, odds_away=None))

    assert profile["favorite_side"] == "NO_CLEAR_FAVORITE"
    assert profile["home_favorite_strength"] == "weak_home_fav"
    assert profile["away_favorite_strength"] == "weak_away_fav"
    assert profile["probability_profile"] == "standard_uncertain"


def test_scores_are_treated_as_zero_to_ten():
    profile = build_control_chaos_profile(base_row(control_score=12.0, chaos_score=-4.0))

    assert profile["control_score"] == 10.0
    assert profile["chaos_score"] == 0.0
    assert profile["control_bucket"] == "HIGH"
    assert profile["chaos_bucket"] == "LOW"


def test_no_betting_recommendation_is_produced():
    profile = build_control_chaos_profile(base_row())

    assert profile["diagnostic_only"] is True
    assert profile["is_betting_recommendation"] is False
    assert profile["bet_recommendation"] is None
