from __future__ import annotations

from pathlib import Path

import pytest

from football_prediction_v19.prematch.input_schema import MatchInput
from football_prediction_v19.prematch.unified_runner import analyze_match
from football_prediction_v19.prospective.prediction_store import lock_prediction, read_locked_predictions


ROOT = Path(__file__).resolve().parents[1]
QUALITY_VALUES = {"HIGH", "MEDIUM", "LOW", "INVALID_HISTORY"}
METHOD_VALUES = {"EXACT", "NORMALIZED_EXACT", "ALIAS", "LEAGUE_FALLBACK", "UNRESOLVED"}


def _prediction(home="Bayern München", away="Borussia Dortmund"):
    return analyze_match(
        MatchInput("German Bundesliga", "2026/27", home, away, "2026-08-20"),
        project_root=ROOT, output_base=ROOT / "outputs/v2184_test_tmp",
        include_shadow_challenger=True, strict_asof=True,
    )


def test_quality_and_complete_rating_audit_are_present():
    shadow = _prediction()["shadow_winner_prediction"]
    audit = shadow["rating_audit"]
    required = {
        "requested_home_team_name", "normalized_home_team_name",
        "matched_home_history_team_name", "home_match_method",
        "requested_away_team_name", "normalized_away_team_name",
        "matched_away_history_team_name", "away_match_method",
        "alias_used", "home_alias_used", "away_alias_used", "rating_source",
        "fallback_used", "fallback_reason", "home_history_count",
        "away_history_count", "history_count", "rating_difference", "rating_uncertainty",
    }
    assert required <= audit.keys()
    assert shadow["shadow_prediction_quality"] in QUALITY_VALUES
    assert audit["home_match_method"] in METHOD_VALUES
    assert audit["away_match_method"] in METHOD_VALUES


def test_bayern_and_dortmund_matching_is_auditable():
    audit = _prediction()["shadow_winner_prediction"]["rating_audit"]
    assert audit["requested_home_team_name"] == "Bayern München"
    assert audit["normalized_home_team_name"] == "bayernmunchen"
    assert audit["matched_home_history_team_name"] == "Bayern Munich"
    assert audit["home_match_method"] == "ALIAS"
    assert audit["requested_away_team_name"] == "Borussia Dortmund"
    assert audit["matched_away_history_team_name"] == "Dortmund"
    assert audit["away_match_method"] == "ALIAS"
    assert audit["alias_used"] is audit["home_alias_used"] is audit["away_alias_used"] is True
    assert audit["rating_source"] == "PRIOR_COMPETITION_HISTORY"
    assert audit["home_history_count"] == audit["away_history_count"] == audit["history_count"] == 102


def test_quality_and_eligibility_are_consistent():
    valid = _prediction()["shadow_winner_prediction"]
    invalid = _prediction("Unknown Alpha", "Unknown Beta")["shadow_winner_prediction"]
    assert valid["shadow_prediction_quality"] == "MEDIUM"
    assert valid["eligible_for_prospective_evaluation"] is True
    assert valid["rating_audit"]["fallback_used"] is False
    assert invalid["shadow_prediction_quality"] == "INVALID_HISTORY"
    assert invalid["eligible_for_prospective_evaluation"] is False
    assert invalid["rating_audit"]["fallback_used"] is True


def test_audit_completion_does_not_change_probabilities():
    result = _prediction()
    shadow = result["shadow_winner_prediction"]
    expected = (0.6167341501460655, 0.23070142056443968, 0.15256442928949482)
    actual = (shadow["home_probability"], shadow["draw_probability"], shadow["away_probability"])
    assert actual == pytest.approx(expected, abs=1e-15)
    assert result["winner_prediction"]["home_probability"] == pytest.approx(0.39416058394160586, abs=1e-15)
    assert shadow["rating_audit"]["rating_difference"] == pytest.approx(189.00128005469765, abs=1e-12)
    assert result["asof_audit"]["post_match_rows_used_count"] == 0


def test_lock_stores_flat_quality_and_matching_fields(tmp_path):
    prediction = _prediction()
    record = lock_prediction(
        tmp_path, fixture_id="bl-test-001", match=prediction["match"],
        kickoff_timestamp="2099-01-05T12:00:00+00:00",
        prediction_timestamp="2099-01-01T12:00:00+00:00", prediction=prediction,
    )
    required = {
        "shadow_prediction_quality", "requested_home_team_name",
        "normalized_home_team_name", "matched_home_history_team_name",
        "home_match_method", "requested_away_team_name",
        "normalized_away_team_name", "matched_away_history_team_name",
        "away_match_method", "alias_used", "rating_source",
    }
    assert required <= record.keys()
    assert all(record[key] not in (None, "") for key in required)
    assert record["shadow_prediction_quality"] == "MEDIUM"
    assert record["eligible_for_prospective_evaluation"] is True


def test_identical_lock_stays_unchanged_and_conflict_is_protected(tmp_path):
    prediction = _prediction()
    kwargs = {
        "fixture_id": "bl-test-001", "match": prediction["match"],
        "kickoff_timestamp": "2099-01-05T12:00:00+00:00",
        "prediction_timestamp": "2099-01-01T12:00:00+00:00", "prediction": prediction,
    }
    first = lock_prediction(tmp_path, **kwargs)
    second = lock_prediction(tmp_path, **kwargs)
    changed = _prediction()
    changed["match"]["match_date"] = "2026-08-21"
    conflict = lock_prediction(tmp_path, **{**kwargs, "match": changed["match"]})
    assert first["lock_operation_status"] == "LOCKED_NEW"
    assert second["lock_operation_status"] == "ALREADY_LOCKED_UNCHANGED"
    assert conflict["lock_operation_status"] == "LOCK_CONFLICT"
    assert len(read_locked_predictions(tmp_path)) == 1
