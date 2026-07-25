from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from football_prediction_v19.models.model_registry import get_model
from football_prediction_v19.prematch.input_schema import MatchInput
from football_prediction_v19.prematch.shadow_winner_adapter import MODEL_NAME
from football_prediction_v19.prematch.unified_runner import analyze_match, run_batch
from football_prediction_v19.prospective.evaluation import evaluate_prospective
from football_prediction_v19.prospective.prediction_store import (
    lock_prediction,
    read_locked_predictions,
    stable_hash,
    verify_prediction_locks,
)
from football_prediction_v19.prospective.result_import import import_results


ROOT = Path(__file__).resolve().parents[1]


def _history() -> pd.DataFrame:
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    rows = []
    for index in range(32):
        home, away = teams[index % 4], teams[(index + 1) % 4]
        rows.append({
            "competition": "Stub League", "season": "2025/26",
            "match_date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=index),
            "home_team": home, "away_team": away,
            "actual_home_goals": (index + 1) % 4, "actual_away_goals": index % 3,
        })
    return pd.DataFrame(rows)


def _match(home="Alpha", away="Beta") -> MatchInput:
    return MatchInput("Stub League", "2025/26", home, away, "2025-03-01")


def _shadow_result(tmp_path) -> dict:
    return analyze_match(
        _match(), project_root=ROOT, output_base=tmp_path,
        history=_history(), include_shadow_challenger=True, strict_asof=True,
    )


def test_shadow_registry_is_non_authoritative_and_frozen():
    model = get_model(MODEL_NAME)
    assert model["status"] == "SHADOW_APPROVED"
    assert model["role"] == "SHADOW_WINNER_CHALLENGER"
    assert model["authoritative_for_1x2"] is False
    assert model["may_replace_primary"] is False
    assert model["probability_blending_enabled"] is False
    manifest = json.loads((ROOT / "models/primary_plus_rating_meta_v2182_manifest.json").read_text())
    assert manifest["rating_config"]["config_name"] == "ELO_GOAL_DIFFERENCE_K30_HA60_S20"
    assert manifest["meta_c"] == 1.0


def test_shadow_only_appears_when_enabled_and_primary_is_unchanged(tmp_path):
    baseline = analyze_match(_match(), project_root=ROOT, output_base=tmp_path / "base", history=_history())
    shadow = _shadow_result(tmp_path / "shadow")
    assert "shadow_winner_prediction" not in baseline
    assert baseline["winner_prediction"] == shadow["winner_prediction"]
    assert shadow["winner_prediction"]["authoritative_for_1x2"] is True
    assert shadow["shadow_winner_prediction"]["authoritative_for_1x2"] is False


def test_shadow_probabilities_and_comparison_are_valid(tmp_path):
    result = _shadow_result(tmp_path)
    shadow = result["shadow_winner_prediction"]
    assert sum(shadow[key] for key in ("home_probability", "draw_probability", "away_probability")) == pytest.approx(1, abs=1e-12)
    assert all(0 <= shadow[key] <= 1 for key in ("home_probability", "draw_probability", "away_probability"))
    assert result["shadow_comparison"]["probability_blending_applied"] is False
    assert result["asof_audit"]["post_match_rows_used_count"] == 0


def test_shadow_json_and_markdown_are_optional(tmp_path):
    result = _shadow_result(tmp_path)
    out = Path(result["output_dir"])
    payload = json.loads((out / "prediction.json").read_text())
    report = (out / "report.md").read_text()
    assert payload["shadow_winner_prediction"]["model_name"] == MODEL_NAME
    assert "## Shadow Challenger" in report
    assert "does not overwrite the primary prediction" in report


def test_batch_with_shadow_keeps_primary_separate(tmp_path):
    result = run_batch(
        [_match(), _match("Gamma", "Delta")],
        project_root=ROOT, output_base=tmp_path, history=_history(),
        include_shadow_challenger=True,
    )
    assert result["successful_count"] == 2
    assert all("shadow_winner_prediction" in row for row in result["predictions"])
    assert all(row["shadow_comparison"]["probability_blending_applied"] is False for row in result["predictions"])


def test_prediction_hash_and_lock_are_immutable(tmp_path):
    prediction = _shadow_result(tmp_path / "analysis")
    record = lock_prediction(
        tmp_path / "store", match=prediction["match"],
        kickoff_timestamp="2099-01-01T12:00:00+00:00",
        prediction=prediction, prediction_timestamp="2099-01-01T10:00:00+00:00",
    )
    assert record["locked"] is True
    assert record["shadow_prediction_hash"] == stable_hash(record["shadow_winner_prediction"])
    assert verify_prediction_locks(tmp_path / "store")["prediction_hash_mismatch_count"] == 0
    changed = json.loads(json.dumps(prediction))
    changed["shadow_winner_prediction"]["home_probability"] += .01
    conflict = lock_prediction(
        tmp_path / "store", match=prediction["match"],
        kickoff_timestamp="2099-01-01T12:00:00+00:00",
        prediction=changed, prediction_timestamp="2099-01-01T10:00:00+00:00",
    )
    assert conflict["lock_operation_status"] == "LOCK_CONFLICT"


def test_result_import_does_not_change_predictions(tmp_path):
    prediction = _shadow_result(tmp_path / "analysis")
    store = tmp_path / "store"
    lock_prediction(
        store, match=prediction["match"], kickoff_timestamp="2099-01-01T12:00:00+00:00",
        prediction=prediction, prediction_timestamp="2099-01-01T10:00:00+00:00",
    )
    before = (store / "shadow_predictions.jsonl").read_bytes()
    result = pd.DataFrame([{**prediction["match"], "actual_home_goals": 2, "actual_away_goals": 1}])
    imported = import_results(store, result)
    assert imported["results_imported_count"] == 1
    assert (store / "shadow_predictions.jsonl").read_bytes() == before


def test_prospective_evaluation_agreement_draw_and_small_sample(tmp_path):
    prediction = _shadow_result(tmp_path / "analysis")
    store = tmp_path / "store"
    lock_prediction(
        store, match=prediction["match"], kickoff_timestamp="2099-01-01T12:00:00+00:00",
        prediction=prediction, prediction_timestamp="2099-01-01T10:00:00+00:00",
    )
    import_results(store, pd.DataFrame([{**prediction["match"], "actual_home_goals": 1, "actual_away_goals": 1}]))
    evaluation = evaluate_prospective(store)
    assert evaluation["evaluatable_count"] == 1
    assert evaluation["prospective_gate"] == "PROSPECTIVE_SAMPLE_TOO_SMALL"
    assert evaluation["agreement_count"] + evaluation["disagreement_count"] == 1
    assert "shadow_draw_precision" in evaluation and "shadow_draw_recall" in evaluation
    assert (store / "prospective_shadow_by_agreement.csv").exists()


def test_safety_flags_remain_false(tmp_path):
    result = _shadow_result(tmp_path)
    assert all(value is False for value in result["safety"].values())
