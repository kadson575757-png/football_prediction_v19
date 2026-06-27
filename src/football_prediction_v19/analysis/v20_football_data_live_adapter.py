# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_football_data_asof_adapter import build_football_data_asof
from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
from football_prediction_v19.analysis.v20_live_source_cache import build_cache_key, read_cache, write_cache
from football_prediction_v19.analysis.v20_source_league_resolver import SourceLeagueMapping


def run_football_data_live_adapter(
    mapping: SourceLeagueMapping,
    context: HistoricalMatchContext,
    output_dir: str | Path,
    *,
    enable_network: bool = False,
    cache_dir: str | Path | None = None,
    mock_csv_path: str | Path | None = None,
    cache_ttl_hours: float = 24,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache_root = Path(cache_dir or out / "cache")
    cache_key = build_cache_key("football_data_co_uk", mapping.canonical_competition, mapping.season_input, "season_csv", {"code": mapping.football_data_code})
    status = "SUCCESS"
    raw_text = ""
    cache_result, cached = read_cache(cache_root, cache_key, cache_ttl_hours)
    if cached:
        raw_text = cached
        status = "CACHE_HIT"
    elif mock_csv_path:
        raw_text = Path(mock_csv_path).read_text(encoding="utf-8")
        write_cache(cache_root, cache_key, raw_text)
    elif not mapping.football_data_code:
        status = "UNSUPPORTED_LEAGUE"
    elif not enable_network:
        status = "DISABLED_NETWORK"
    else:
        status = "FAILED"
    raw_path = out / "football_data_live_raw.csv"
    normalized_path = out / "football_data_live_normalized.csv"
    if not raw_text:
        _empty_football_csv(normalized_path)
        result = _result(status, out, raw_path, normalized_path, None, None, cache_result.to_dict(), 0)
        _write_report(out, result)
        return result
    raw_path.write_text(raw_text, encoding="utf-8")
    df = pd.read_csv(io.StringIO(raw_text), keep_default_na=False)
    normalized = normalize_football_data_live_frame(df)
    normalized.to_csv(normalized_path, index=False)
    asof = build_football_data_asof(normalized_path, context, out)
    result = _result(status, out, raw_path, normalized_path, asof, None, cache_result.to_dict(), len(normalized))
    _write_report(out, result)
    return result


def normalize_football_data_live_frame(df: pd.DataFrame) -> pd.DataFrame:
    required = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
    frame = df.copy()
    for column in required:
        if column not in frame.columns:
            frame[column] = ""
    odds_aliases = {"B365H": "B365H", "B365D": "B365D", "B365A": "B365A"}
    for source, target in odds_aliases.items():
        if source not in frame.columns:
            frame[target] = ""
    return frame[required + ["B365H", "B365D", "B365A"]].copy()


def _empty_football_csv(path: Path) -> None:
    pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "B365H", "B365D", "B365A"]).to_csv(path, index=False)


def _result(status: str, out: Path, raw_path: Path, normalized_path: Path, asof: dict[str, object] | None, warnings: str | None, cache: dict[str, object], rows: int) -> dict[str, object]:
    payload = {
        "football_data_live_status": status,
        "records_count": rows,
        "cache_used": status == "CACHE_HIT",
        "football_data_live_raw_path": str(raw_path.resolve()),
        "football_data_live_normalized_path": str(normalized_path.resolve()),
        "cache_status": cache,
        "warnings": warnings or "",
    }
    if asof:
        payload.update(asof)
    else:
        table_path = out / "football_data_asof_table.csv"
        form_path = out / "football_data_asof_form.csv"
        pd.DataFrame(columns=["team", "played", "points", "points_per_game"]).to_csv(table_path, index=False)
        pd.DataFrame(columns=["team", "recent_form_points_5", "recent_goals_for_5", "recent_goals_against_5"]).to_csv(form_path, index=False)
        report_path = out / "football_data_asof_report.md"
        report_path.write_text("# v2.0 football-data As-Of Report\n\nNo available rows.\n", encoding="utf-8")
        payload.update({"football_data_asof_status": "PARTIAL", "table_available": False, "form_available": False, "matches_used": 0, "football_data_asof_table_path": str(table_path.resolve()), "football_data_asof_form_path": str(form_path.resolve()), "football_data_asof_report_path": str(report_path.resolve())})
    (out / "football_data_live_result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["football_data_live_result_json_path"] = str((out / "football_data_live_result.json").resolve())
    return payload


def _write_report(out: Path, result: dict[str, object]) -> None:
    path = out / "football_data_live_adapter_report.md"
    path.write_text(
        "\n".join(
            [
                "# v2.0 football-data Live Adapter",
                "",
                f"- status: {result['football_data_live_status']}",
                f"- records_count: {result['records_count']}",
                f"- cache_used: {str(result['cache_used']).lower()}",
                f"- table_available: {str(result.get('table_available', False)).lower()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result["football_data_live_adapter_report_path"] = str(path.resolve())
