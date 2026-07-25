from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from football_prediction_v19.models.model_registry import active_model_for_role, get_model_registry
from football_prediction_v19.prematch.input_schema import MatchInput, load_batch_file, parse_match_input
from football_prediction_v19.prematch.model_comparison import compare_models
from football_prediction_v19.prematch.output_schema import validate_probability_distribution
from football_prediction_v19.prematch.unified_runner import SAFETY, analyze_match, run_batch


ROOT = Path(__file__).resolve().parents[1]


def _history() -> pd.DataFrame:
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    rows = []
    for index in range(24):
        home = teams[index % 4]
        away = teams[(index + 1 + (index // 4) % 2) % 4]
        if home == away:
            away = teams[(teams.index(home) + 2) % 4]
        rows.append({
            "match_date": f"2025-{1 + index // 4:02d}-{1 + (index % 4) * 5:02d}",
            "competition": "Stub League",
            "season": "2025/26",
            "home_team": home,
            "away_team": away,
            "actual_home_goals": (index * 2 + 1) % 4,
            "actual_away_goals": index % 3,
        })
    return pd.DataFrame(rows)


def _match(home: str = "Alpha", away: str = "Beta", date: str = "2025-07-10") -> MatchInput:
    return MatchInput("Stub League", "2025/26", home, away, date)


def test_input_validation_rejects_invalid_season_and_same_team():
    with pytest.raises(ValueError):
        parse_match_input({"competition": "X", "season": "25", "home_team": "A", "away_team": "B", "match_date": "2025-01-01"})
    with pytest.raises(ValueError):
        parse_match_input({"competition": "X", "season": "2025/26", "home_team": "A FC", "away_team": "A", "match_date": "2025-01-01"})


def test_registry_has_one_primary_and_excludes_rejected_models():
    assert active_model_for_role("PRIMARY_WINNER")["status"] == "ACTIVE"
    registry = get_model_registry()
    assert registry["V2140_GRADIENT_BOOSTING_CHALLENGER"]["status"] == "REJECTED"
    assert registry["V2150_ENRICHED_PREMATCH_CHALLENGER"]["status"] == "REJECTED"


def test_single_runner_writes_stable_outputs_and_preserves_model_roles(tmp_path):
    result = analyze_match(_match(), project_root=ROOT, output_base=tmp_path, history=_history(), strict_asof=True)
    out = Path(result["output_dir"])
    expected = {
        "prediction.json", "prediction.csv", "report.md", "score_matrix.csv",
        "feature_snapshot.csv", "source_audit.csv", "asof_audit.csv",
    }
    assert expected <= {path.name for path in out.iterdir()}
    assert result["winner_prediction"]["authoritative_for_1x2"] is True
    assert result["model_comparison"]["probability_mixing_applied"] is False
    assert result["goal_prediction"]["model_role"] == "SUPPORTING_GOAL_COMPONENT"


def test_probability_and_score_matrix_sums_are_one(tmp_path):
    result = analyze_match(_match(), project_root=ROOT, output_base=tmp_path, history=_history())
    validate_probability_distribution(result["winner_prediction"]["probabilities"])
    validate_probability_distribution(result["goal_prediction"]["outcome_probabilities"])
    matrix = pd.read_csv(Path(result["output_dir"]) / "score_matrix.csv")
    assert float(matrix["probability"].sum()) == pytest.approx(1.0, abs=1e-12)


def test_asof_audit_never_uses_target_or_future_rows(tmp_path):
    history = pd.concat([_history(), pd.DataFrame([{
        "match_date": "2025-08-01", "competition": "Stub League", "season": "2025/26",
        "home_team": "Alpha", "away_team": "Beta", "actual_home_goals": 9, "actual_away_goals": 9,
    }])], ignore_index=True)
    result = analyze_match(_match(), project_root=ROOT, output_base=tmp_path, history=history, strict_asof=True)
    audit = result["asof_audit"]
    assert audit["post_match_rows_used_count"] == 0
    assert audit["maximum_source_date"] < audit["target_match_date"]
    snapshot = pd.read_csv(Path(result["output_dir"]) / "feature_snapshot.csv")
    assert "actual_home_goals" not in snapshot
    assert "actual_away_goals" not in snapshot


def test_low_history_fallback_does_not_block_prediction(tmp_path):
    result = analyze_match(_match(date="2025-01-02"), project_root=ROOT, output_base=tmp_path, history=_history())
    assert result["data_quality"]["quality_tier"] == "LOW"
    assert result["data_quality"]["fallback_used"] is True
    assert result["winner_prediction"]["top_outcome"] in {"HOME", "DRAW", "AWAY"}


def test_scoreline_limit_must_be_at_least_eight(tmp_path):
    with pytest.raises(ValueError):
        analyze_match(_match(), project_root=ROOT, output_base=tmp_path, history=_history(), max_scoreline_goals=7)


def test_comparison_does_not_blend_and_flags_disagreement():
    result = compare_models(
        {"HOME": 0.60, "DRAW": 0.25, "AWAY": 0.15},
        {"HOME": 0.20, "DRAW": 0.25, "AWAY": 0.55},
    )
    assert result["conflict_level"] == "HIGH"
    assert result["probability_mixing_applied"] is False


def test_batch_isolates_invalid_rows_and_writes_aggregates(tmp_path):
    result = run_batch(
        [_match("Alpha", "Beta"), (2, ValueError("bad row")), _match("Gamma", "Delta")],
        project_root=ROOT,
        output_base=tmp_path,
        history=_history(),
    )
    out = Path(result["output_dir"])
    assert result["successful_count"] == 2
    assert result["failed_count"] == 1
    assert {"unified_predictions.csv", "unified_predictions.jsonl", "unified_report.md", "failed_rows.csv"} <= {
        path.name for path in out.iterdir()
    }


def test_csv_and_jsonl_batch_input(tmp_path):
    csv_path = tmp_path / "matches.csv"
    jsonl_path = tmp_path / "matches.jsonl"
    row = _match().as_dict()
    pd.DataFrame([row]).to_csv(csv_path, index=False)
    jsonl_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert isinstance(load_batch_file(csv_path)[0], MatchInput)
    assert isinstance(load_batch_file(jsonl_path)[0], MatchInput)


def test_safety_flags_false_and_network_default_off(tmp_path):
    assert all(value is False for value in SAFETY.values())
    result = analyze_match(_match(), project_root=ROOT, output_base=tmp_path, history=_history())
    assert all(value is False for value in result["safety"].values())


def test_script_and_core_exist_and_help_runs():
    files = [
        ROOT / "scripts/run_unified_prematch_analysis.py",
        ROOT / "src/football_prediction_v19/prematch/unified_runner.py",
        ROOT / "src/football_prediction_v19/models/model_registry.py",
    ]
    assert all(path.exists() for path in files)
    completed = subprocess.run(
        [sys.executable, str(files[0]), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--input-file" in completed.stdout
