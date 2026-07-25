"""Import final results without mutating locked predictions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.prospective.prediction_store import read_locked_predictions, verify_prediction_locks


RESULT_FILE = "prospective_results.jsonl"


def import_results(output_dir: str | Path, results: pd.DataFrame) -> dict:
    out = Path(output_dir)
    before = verify_prediction_locks(out)
    locked = {row["fixture_key"]: row for row in read_locked_predictions(out)}
    existing = _read_results(out)
    imported = 0
    for _, row in results.iterrows():
        match = {key: str(row[key]) for key in ("competition", "season", "match_date", "home_team", "away_team")}
        key = "|".join(match.values())
        if key not in locked:
            raise KeyError(f"no locked prediction for result: {key}")
        home_goals, away_goals = int(row["actual_home_goals"]), int(row["actual_away_goals"])
        result = {
            "fixture_key": key, **match,
            "actual_home_goals": home_goals, "actual_away_goals": away_goals,
            "actual_result": "HOME" if home_goals > away_goals else "AWAY" if away_goals > home_goals else "DRAW",
            "result_verified": _as_bool(row.get("result_verified", True)),
        }
        if key in existing and existing[key] != result:
            raise RuntimeError("imported result cannot be overwritten")
        if key not in existing:
            with (out / RESULT_FILE).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            existing[key] = result
            imported += 1
    after = verify_prediction_locks(out)
    if before != after:
        raise RuntimeError("result import changed locked predictions")
    return {"results_imported_count": imported, **after}


def _read_results(output_dir: str | Path) -> dict[str, dict]:
    path = Path(output_dir) / RESULT_FILE
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["fixture_key"]: row for row in rows}


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y"}
    return bool(value)
