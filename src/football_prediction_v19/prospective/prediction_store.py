"""Append-only prospective prediction locking."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PREDICTION_FILE = "shadow_predictions.jsonl"


def stable_hash(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def lock_prediction(
    output_dir: str | Path,
    *,
    match: dict,
    kickoff_timestamp: str,
    prediction: dict,
    prediction_timestamp: str | None = None,
    fixture_id: str | None = None,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = prediction_timestamp or datetime.now(timezone.utc).isoformat()
    kickoff = datetime.fromisoformat(kickoff_timestamp.replace("Z", "+00:00"))
    created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    hours_before = (kickoff - created).total_seconds() / 3600.0
    timing_status = _timing_status(hours_before)
    primary = prediction["winner_prediction"]
    shadow = prediction["shadow_winner_prediction"]
    input_payload = {"match": match, "kickoff_timestamp": kickoff_timestamp}
    fixture_key = _fixture_key(match)
    resolved_fixture_id = str(fixture_id or fixture_key)
    record = {
        "lock_schema_version": "2.18.4",
        "prediction_id": stable_hash({"fixture_id": resolved_fixture_id, "prediction_timestamp": timestamp})[:24],
        "fixture_id": resolved_fixture_id,
        "fixture_key": fixture_key,
        "match": match,
        "prediction_timestamp": timestamp,
        "kickoff_timestamp": kickoff_timestamp,
        "hours_before_kickoff": hours_before,
        "prediction_timing_status": timing_status,
        "runner_version": prediction["analysis_version"],
        "primary_model_version": prediction["analysis_version"],
        "shadow_model_version": shadow["model_version"],
        "input_hash": stable_hash(input_payload),
        "primary_prediction_hash": stable_hash(primary),
        "shadow_prediction_hash": stable_hash(shadow),
        "primary_winner_prediction": primary,
        "shadow_winner_prediction": shadow,
        "primary_top_outcome": primary["top_outcome"],
        "shadow_top_outcome": shadow["top_outcome"],
        "primary_shadow_agreement": primary["top_outcome"] == shadow["top_outcome"],
        "data_quality_grade": prediction["data_quality"]["quality_grade"],
        "primary_confidence_band": primary["confidence_band"],
        "post_match_rows_used_count": prediction["asof_audit"]["post_match_rows_used_count"],
        "locked": True,
        "result_known_at_prediction_time": False,
        "shadow_prediction_quality": shadow["shadow_prediction_quality"],
        "requested_home_team_name": shadow["rating_audit"]["requested_home_team_name"],
        "normalized_home_team_name": shadow["rating_audit"]["normalized_home_team_name"],
        "matched_home_history_team_name": shadow["rating_audit"]["matched_home_history_team_name"],
        "home_match_method": shadow["rating_audit"]["home_match_method"],
        "requested_away_team_name": shadow["rating_audit"]["requested_away_team_name"],
        "normalized_away_team_name": shadow["rating_audit"]["normalized_away_team_name"],
        "matched_away_history_team_name": shadow["rating_audit"]["matched_away_history_team_name"],
        "away_match_method": shadow["rating_audit"]["away_match_method"],
        "alias_used": shadow["rating_audit"]["alias_used"],
        "rating_source": shadow["rating_audit"]["rating_source"],
    }
    reasons = list(shadow.get("ineligibility_reasons", []))
    if timing_status == "AFTER_KICKOFF_INVALID":
        reasons.append("AFTER_KICKOFF_INVALID")
    if record["post_match_rows_used_count"]:
        reasons.append("POST_MATCH_ROWS_USED")
    record["eligible_for_prospective_evaluation"] = bool(
        shadow.get("eligible_for_prospective_evaluation", True) and not reasons
    )
    record["ineligibility_reasons"] = list(dict.fromkeys(reasons))
    path = out / PREDICTION_FILE
    existing = {row.get("fixture_id", row["fixture_key"]): row for row in read_locked_predictions(out)}
    if resolved_fixture_id in existing:
        previous = existing[resolved_fixture_id]
        hashes = ("input_hash", "primary_prediction_hash", "shadow_prediction_hash")
        if any(previous[key] != record[key] for key in hashes):
            return {"lock_operation_status": "LOCK_CONFLICT", "fixture_id": resolved_fixture_id, "fixture_key": fixture_key, "locked": False}
        return {**previous, "lock_operation_status": "ALREADY_LOCKED_UNCHANGED"}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {**record, "lock_operation_status": "LOCKED_NEW"}


def read_locked_predictions(output_dir: str | Path) -> list[dict]:
    path = Path(output_dir) / PREDICTION_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_prediction_locks(output_dir: str | Path) -> dict:
    rows = read_locked_predictions(output_dir)
    mismatches = 0
    for row in rows:
        mismatches += stable_hash(row["primary_winner_prediction"]) != row["primary_prediction_hash"]
        mismatches += stable_hash(row["shadow_winner_prediction"]) != row["shadow_prediction_hash"]
        mismatches += not bool(row["locked"])
    return {"locked_prediction_count": len(rows), "prediction_hash_mismatch_count": int(mismatches)}


def _fixture_key(match: dict) -> str:
    fields = ("competition", "season", "match_date", "home_team", "away_team")
    return "|".join(str(match[field]) for field in fields)


def _timing_status(hours_before_kickoff: float) -> str:
    if hours_before_kickoff <= 0:
        return "AFTER_KICKOFF_INVALID"
    if hours_before_kickoff < 24:
        return "LATE"
    if hours_before_kickoff < 72:
        return "STANDARD"
    return "EARLY"
