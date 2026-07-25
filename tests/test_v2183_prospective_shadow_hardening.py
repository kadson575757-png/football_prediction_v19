from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from football_prediction_v19.prematch.input_schema import MatchInput
from football_prediction_v19.prematch.unified_runner import analyze_match
from football_prediction_v19.prospective.evaluation import evaluate_prospective
from football_prediction_v19.prospective.prediction_store import lock_prediction, read_locked_predictions
from football_prediction_v19.prospective.result_import import import_results


ROOT = Path(__file__).resolve().parents[1]


def _analyze(home: str, away: str, competition: str = "Bundesliga"):
    return analyze_match(
        MatchInput(competition, "2026/27", home, away, "2026-08-20"),
        project_root=ROOT, output_base=ROOT / "outputs/v2183_test_tmp",
        include_shadow_challenger=True, strict_asof=True,
    )


def test_bayern_and_dortmund_aliases_resolve_to_history():
    result = _analyze("Bayern München", "Borussia Dortmund", "German Bundesliga")
    audits = result["shadow_winner_prediction"]["team_rating_audit"]
    assert [row["matched_history_team_name"] for row in audits] == ["Bayern Munich", "Dortmund"]
    assert all(row["match_method"] == "ALIAS" for row in audits)
    assert all(row["alias_used"] for row in audits)
    assert all(row["history_count"] > 0 for row in audits)
    assert result["shadow_winner_prediction"]["eligible_for_prospective_evaluation"] is True


def test_two_unknown_teams_use_conservative_fallback_without_extreme_probability():
    shadow = _analyze("Unknown Alpha", "Unknown Beta")["shadow_winner_prediction"]
    assert shadow["shadow_prediction_quality"] == "INVALID_HISTORY"
    assert shadow["eligible_for_prospective_evaluation"] is False
    assert shadow["rating_audit"]["history_count"] == 0
    assert shadow["rating_audit"]["rating_uncertainty"] == 1.0
    assert abs(shadow["rating_audit"]["rating_difference"]) <= 180
    assert max(shadow[key] for key in ("home_probability", "draw_probability", "away_probability")) < .70


def test_one_unknown_team_shrinks_known_rating_and_raises_uncertainty():
    shadow = _analyze("Bayern Munich", "Unknown Beta")["shadow_winner_prediction"]
    audits = shadow["team_rating_audit"]
    assert audits[0]["history_count"] > 0 and audits[1]["history_count"] == 0
    assert shadow["rating_audit"]["fallback_used"] is True
    assert shadow["rating_audit"]["rating_uncertainty"] == 1.0
    assert abs(shadow["rating_audit"]["rating_difference"]) <= 180
    assert shadow["eligible_for_prospective_evaluation"] is False


def test_lock_schema_preserves_fixture_id_and_all_required_fields(tmp_path):
    prediction = _analyze("Bayern Munich", "Dortmund")
    record = lock_prediction(
        tmp_path, fixture_id="bl-test-001", match=prediction["match"],
        kickoff_timestamp="2099-01-05T12:00:00+00:00",
        prediction_timestamp="2099-01-01T12:00:00+00:00", prediction=prediction,
    )
    required = {
        "prediction_id", "fixture_id", "fixture_key", "prediction_timestamp",
        "kickoff_timestamp", "hours_before_kickoff", "prediction_timing_status",
        "runner_version", "primary_model_version", "shadow_model_version",
        "input_hash", "primary_prediction_hash", "shadow_prediction_hash",
        "locked", "result_known_at_prediction_time", "eligible_for_prospective_evaluation",
        "ineligibility_reasons", "post_match_rows_used_count",
    }
    assert required <= record.keys()
    assert record["fixture_id"] == "bl-test-001"
    assert record["result_known_at_prediction_time"] is False
    assert record["prediction_timing_status"] == "EARLY"


@pytest.mark.parametrize(
    ("hours", "expected"),
    [(100, "EARLY"), (48, "STANDARD"), (8, "LATE"), (-1, "AFTER_KICKOFF_INVALID")],
)
def test_prediction_timing_status(hours, expected, tmp_path):
    prediction = _analyze("Bayern Munich", "Dortmund")
    kickoff = pd.Timestamp("2099-01-10T12:00:00+00:00")
    created = kickoff - pd.Timedelta(hours=hours)
    record = lock_prediction(
        tmp_path / expected, fixture_id=f"id-{expected}", match=prediction["match"],
        kickoff_timestamp=kickoff.isoformat(), prediction_timestamp=created.isoformat(),
        prediction=prediction,
    )
    assert record["hours_before_kickoff"] == pytest.approx(hours)
    assert record["prediction_timing_status"] == expected
    assert record["eligible_for_prospective_evaluation"] is (expected != "AFTER_KICKOFF_INVALID")


def test_duplicate_lock_unchanged_and_conflict_do_not_append(tmp_path):
    prediction = _analyze("Bayern Munich", "Dortmund")
    args = {
        "fixture_id": "bl-test-001", "match": prediction["match"],
        "kickoff_timestamp": "2099-01-05T12:00:00+00:00",
        "prediction_timestamp": "2099-01-01T12:00:00+00:00", "prediction": prediction,
    }
    first = lock_prediction(tmp_path, **args)
    second = lock_prediction(tmp_path, **args)
    changed = json.loads(json.dumps(prediction))
    changed["match"]["match_date"] = "2026-08-21"
    conflict = lock_prediction(tmp_path, **{**args, "match": changed["match"]})
    assert first["lock_operation_status"] == "LOCKED_NEW"
    assert second["lock_operation_status"] == "ALREADY_LOCKED_UNCHANGED"
    assert conflict["lock_operation_status"] == "LOCK_CONFLICT"
    assert len(read_locked_predictions(tmp_path)) == 1


def test_evaluation_excludes_invalid_history_and_after_kickoff(tmp_path):
    prediction = _analyze("Unknown Alpha", "Unknown Beta")
    lock_prediction(
        tmp_path, fixture_id="invalid-1", match=prediction["match"],
        kickoff_timestamp="2099-01-01T12:00:00+00:00",
        prediction_timestamp="2099-01-01T10:00:00+00:00", prediction=prediction,
    )
    import_results(tmp_path, pd.DataFrame([{
        **prediction["match"], "actual_home_goals": 1, "actual_away_goals": 0,
        "result_verified": True,
    }]))
    result = evaluate_prospective(tmp_path)
    assert result["evaluatable_count"] == 0


def test_primary_and_safety_remain_unchanged():
    without = analyze_match(
        MatchInput("Bundesliga", "2026/27", "Bayern Munich", "Dortmund", "2026-08-20"),
        project_root=ROOT, output_base=ROOT / "outputs/v2183_test_tmp/base",
    )
    with_shadow = _analyze("Bayern Munich", "Dortmund")
    assert without["winner_prediction"] == with_shadow["winner_prediction"]
    assert with_shadow["shadow_comparison"]["probability_blending_applied"] is False
    assert with_shadow["asof_audit"]["post_match_rows_used_count"] == 0
    assert all(value is False for value in with_shadow["safety"].values())
