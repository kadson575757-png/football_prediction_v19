# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_api_key_loader import load_v20_api_key_status
from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
from football_prediction_v19.analysis.v20_source_league_resolver import SourceLeagueMapping


def run_api_football_optional_adapter(
    mapping: SourceLeagueMapping,
    context: HistoricalMatchContext,
    output_dir: str | Path,
    *,
    enabled: bool = False,
    enable_network: bool = False,
    mock_json_path: str | Path | None = None,
) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    key_present = load_v20_api_key_status(["APIFOOTBALL_KEY"])["keys"]["APIFOOTBALL_KEY"]["key_present"]
    status = "DISABLED_BY_CONFIG"
    rows: list[dict[str, object]] = []
    if enabled and not key_present and not mock_json_path:
        status = "DISABLED_MISSING_KEY"
    elif enabled and not enable_network and not mock_json_path:
        status = "DISABLED_NETWORK"
    elif enabled and mock_json_path:
        payload = json.loads(Path(mock_json_path).read_text(encoding="utf-8"))
        rows = normalize_api_football_optional_payload(payload)
        status = "SUCCESS"
    elif enabled and enable_network:
        status = "PARTIAL"
    csv_path = out / "api_football_optional_normalized.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    result = {
        "api_football_optional_status": status,
        "api_key_present": bool(key_present),
        "lineups_available": any(r.get("record_type") == "lineup" for r in rows),
        "injuries_available": any(r.get("record_type") == "injury" for r in rows),
        "records_count": len(rows),
        "api_football_optional_normalized_path": str(csv_path.resolve()),
        "warnings": "" if status == "SUCCESS" else "optional source not required for model readiness",
    }
    json_path = out / "api_football_optional_result.json"
    report = out / "api_football_optional_report.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text(f"# v2.0 API-Football Optional Adapter\n\n- status: {status}\n- lineups_available: {str(result['lineups_available']).lower()}\n- injuries_available: {str(result['injuries_available']).lower()}\n\nNo secret values are written.\n", encoding="utf-8")
    result["api_football_optional_result_json_path"] = str(json_path.resolve())
    result["api_football_optional_report_path"] = str(report.resolve())
    return result


def normalize_api_football_optional_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for item in payload.get("lineups", []):
        rows.append({"record_type": "lineup", "team": item.get("team", ""), "value": item.get("formation", "")})
    for item in payload.get("injuries", []):
        rows.append({"record_type": "injury", "team": item.get("team", ""), "value": item.get("player", "")})
    return rows
