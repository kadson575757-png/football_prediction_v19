from scripts import run_v27_prematch_evaluation


def test_v2101_evaluation_console_is_probability_first(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.run_v27_prematch_evaluation.run_prematch_evaluation",
        lambda **kwargs: {
            "v27_prematch_evaluation_status": "READY",
            "matches_requested": 2,
            "matches_evaluated": 2,
            "probability_rows_count": 2,
            "probability_output_rate": 1.0,
            "top_probability_home_count": 1,
            "top_probability_draw_count": 0,
            "top_probability_away_count": 1,
            "top_probability_hit_count": 1,
            "top_probability_miss_count": 1,
            "top_probability_hit_rate": 0.5,
            "insufficient_source_data_count": 0,
            "decision_count": 2,
            "winner_pick_count": 1,
            "winner_lean_count": 1,
            "no_decision_count": 0,
            "data_blocked_count": 0,
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        },
    )

    assert run_v27_prematch_evaluation.main(["--input", "unused.csv"]) == 0
    output = capsys.readouterr().out

    assert "probability_evaluation_status=READY" in output
    assert "probability_rows_count=2" in output
    assert "probability_output_rate=1.0" in output
    assert "top_probability_hit_rate=0.5" in output
    assert "automatic_betting_enabled=false" in output
    assert "staking_logic_enabled=false" in output
    assert "roi_logic_enabled=false" in output
    for token in [
        "decision_count=",
        "winner_pick_count=",
        "winner_lean_count=",
        "no_decision_count=",
        "no_decision_rate=",
        "data_blocked_count=",
        "data_blocked_rate=",
    ]:
        assert token not in output
