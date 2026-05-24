from football_prediction_v19.diagnostics.recommended_market import build_recommended_market


def row(**overrides):
    data = {
        "league": "Ligue 1",
        "likely_1x2": "Home",
        "model_home_prob": 0.68,
        "model_draw_prob": 0.20,
        "model_away_prob": 0.12,
        "odds_home": 1.55,
        "odds_draw": 4.2,
        "odds_away": 6.0,
        "control_score_10": 5.8,
        "chaos_score_10": 2.4,
        "confidence": "HIGH",
        "favorite_side": "HOME_FAVORITE",
        "favorite_strength": "strong_home_fav",
        "goals": "unclear",
        "over25_signal": "unclear",
        "btts_signal": "unclear",
        "under35_signal": "",
        "data_warning": False,
    }
    data.update(overrides)
    return data


def test_high_confidence_favorite_medium_control_low_chaos_direction():
    rec = build_recommended_market(row())

    assert rec["recommended_market_type"] == "DIRECTION"
    assert rec["recommendation_strength"] == "MEDIUM"


def test_favorite_good_probability_low_control_double_chance():
    rec = build_recommended_market(row(control_score_10=3.4, chaos_score_10=2.6, confidence="MEDIUM"))

    assert rec["recommended_market_type"] == "DOUBLE_CHANCE"
    assert rec["recommended_market_read"] == "home_or_draw_1X"


def test_low_control_high_chaos_unclear_goals_avoid():
    rec = build_recommended_market(row(control_score_10=1.0, chaos_score_10=6.0, confidence="LOW", model_home_prob=0.38))

    assert rec["recommended_market_type"] == "AVOID"
    assert rec["avoid_reason"]


def test_strong_over_btts_signal_low_control_btts_over():
    rec = build_recommended_market(
        row(
            league="Ligue 1",
            control_score_10=1.8,
            chaos_score_10=4.2,
            confidence="LOW",
            over25_signal="OVER likely",
            btts_signal="BTTS YES likely",
            both_over=True,
            both_btts=True,
        )
    )

    assert rec["recommended_market_type"] == "BTTS_OVER"


def test_under_signal_low_chaos_weak_btts_under():
    rec = build_recommended_market(
        row(
            control_score_10=2.4,
            chaos_score_10=2.2,
            confidence="LOW",
            goals="Under2.5",
            over25_signal="UNDER likely",
            btts_signal="BTTS NO likely",
            under35_signal="UNDER 3.5 useful lean",
        )
    )

    assert rec["recommended_market_type"] == "UNDER"


def test_data_warning_with_1x2_read_observe_or_avoid():
    rec = build_recommended_market(row(data_warning=True, confidence="NO-CONFIDENCE"))

    assert rec["recommended_market_type"] in {"OBSERVE_ONLY", "AVOID"}
    assert rec["diagnostic_only"] is True


def test_eredivisie_strong_goals_signal_can_produce_btts_over():
    rec = build_recommended_market(
        row(
            league="Eredivisie",
            control_score_10=2.0,
            chaos_score_10=2.5,
            confidence="LOW",
            over25_signal="OVER likely",
            btts_signal="BTTS YES likely",
        )
    )

    assert rec["recommended_market_type"] == "BTTS_OVER"


def test_epl_low_control_unclear_read_becomes_avoid_or_observe():
    rec = build_recommended_market(
        row(
            league="EPL",
            control_score_10=2.0,
            chaos_score_10=2.0,
            confidence="LOW",
            goals="unclear",
            over25_signal="unclear",
            btts_signal="unclear",
        )
    )

    assert rec["recommended_market_type"] in {"AVOID", "OBSERVE_ONLY"}


def test_no_betting_roi_or_ledger_fields_returned():
    rec = build_recommended_market(row())

    forbidden = {"stake", "roi", "profit", "ledger_entry", "bet_recommendation"}
    assert forbidden.isdisjoint(rec)
    assert rec["diagnostic_only"] is True


def test_missing_optional_keys_handled_gracefully():
    rec = build_recommended_market({})

    assert rec["recommended_market_type"] in {"AVOID", "OBSERVE_ONLY"}
    assert rec["risk_note"]
