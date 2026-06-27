# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_api_key_loader import load_v20_api_key_status
from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
from football_prediction_v19.analysis.v20_live_source_cache import build_cache_key, read_cache, write_cache
from football_prediction_v19.analysis.v20_odds_asof_adapter import build_odds_asof
from football_prediction_v19.analysis.v20_source_league_resolver import SourceLeagueMapping


def run_odds_api_historical_adapter(
    mapping: SourceLeagueMapping,
    context: HistoricalMatchContext,
    output_dir: str | Path,
    *,
    enable_network: bool = False,
    cache_dir: str | Path | None = None,
    mock_json_path: str | Path | None = None,
    cache_ttl_hours: float = 24,
) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    key_status = load_v20_api_key_status(["THE_ODDS_API_KEY"])["keys"]["THE_ODDS_API_KEY"]["key_present"]
    cache_root = Path(cache_dir or out / "cache")
    cache_key = build_cache_key("odds_api", mapping.canonical_competition, mapping.season_input, "historical_snapshot", {"sport": mapping.odds_api_sport_key, "match": context.match_id})
    cache_result, cached = read_cache(cache_root, cache_key, cache_ttl_hours)
    status = "SUCCESS"
    raw_text = cached
    if raw_text:
        status = "CACHE_HIT"
    elif mock_json_path:
        raw_text = Path(mock_json_path).read_text(encoding="utf-8")
        write_cache(cache_root, cache_key, raw_text)
    elif not mapping.odds_api_sport_key:
        status = "UNSUPPORTED_SPORT_KEY"
    elif not key_status:
        status = "DISABLED_MISSING_KEY"
    elif not enable_network:
        status = "DISABLED_NETWORK"
    else:
        status = "FAILED"
    raw_path = out / "odds_api_raw.json"
    normalized_path = out / "odds_api_normalized.csv"
    totals_path = out / "odds_api_totals_normalized.csv"
    if not raw_text:
        _empty_odds(normalized_path); _empty_odds(totals_path)
        return _finish(out, status, raw_path, normalized_path, totals_path, None, cache_result.to_dict(), key_status)
    raw_path.write_text(raw_text, encoding="utf-8")
    frame = normalize_odds_api_payload(json.loads(raw_text), context)
    one_x_two = frame[frame["market"].eq("1X2")].copy()
    totals = frame[frame["market"].eq("OU25")].copy()
    one_x_two.to_csv(normalized_path, index=False)
    totals.to_csv(totals_path, index=False)
    asof = build_odds_asof(normalized_path, totals_path, context, out)
    if frame.empty:
        status = "MATCH_NOT_FOUND"
    elif one_x_two.empty:
        status = "MARKET_NOT_AVAILABLE"
    return _finish(out, status, raw_path, normalized_path, totals_path, asof, cache_result.to_dict(), key_status)


def normalize_odds_api_payload(payload: dict[str, object] | list[object], context: HistoricalMatchContext) -> pd.DataFrame:
    events = payload.get("events", payload) if isinstance(payload, dict) else payload
    rows = []
    for event in events if isinstance(events, list) else []:
        home = str(event.get("home_team", ""))
        away = str(event.get("away_team", ""))
        if not _team_match(home, context.home_team) or not _team_match(away, context.away_team):
            continue
        snapshot = event.get("snapshot_time") or event.get("commence_time") or f"{context.match_date}T00:00:00"
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                key = market.get("key", "")
                for outcome in market.get("outcomes", []):
                    name = str(outcome.get("name", "")).lower()
                    if key in {"h2h", "1x2"}:
                        selection = "DRAW" if name == "draw" else ("HOME" if _team_match(str(outcome.get("name", "")), home) else "AWAY")
                        rows.append(_row(context, snapshot, "1X2", selection, outcome.get("price", "")))
                    elif key in {"totals", "over_under"}:
                        selection = "OVER_2_5" if name.startswith("over") else "UNDER_2_5"
                        rows.append(_row(context, snapshot, "OU25", selection, outcome.get("price", "")))
    return pd.DataFrame(rows, columns=["match_date", "home_team", "away_team", "snapshot_time", "market", "selection", "odds", "bookmaker"])


def _row(context: HistoricalMatchContext, snapshot: str, market: str, selection: str, odds: object) -> dict[str, object]:
    return {"match_date": context.match_date, "home_team": context.home_team, "away_team": context.away_team, "snapshot_time": snapshot, "market": market, "selection": selection, "odds": odds, "bookmaker": "odds_api"}


def _team_match(value: str, target: str) -> bool:
    return " ".join(value.lower().split()) == " ".join(target.lower().split())


def _empty_odds(path: Path) -> None:
    pd.DataFrame(columns=["match_date", "home_team", "away_team", "snapshot_time", "market", "selection", "odds", "bookmaker"]).to_csv(path, index=False)


def _finish(out: Path, status: str, raw_path: Path, normalized_path: Path, totals_path: Path, asof: dict[str, object] | None, cache: dict[str, object], key_present: bool) -> dict[str, object]:
    result = {
        "odds_api_status": status,
        "api_key_present": bool(key_present),
        "cache_used": status == "CACHE_HIT",
        "odds_api_raw_path": str(raw_path.resolve()),
        "odds_api_normalized_path": str(normalized_path.resolve()),
        "odds_api_totals_normalized_path": str(totals_path.resolve()),
        "cache_status": cache,
    }
    if asof:
        result.update(asof)
    else:
        clean_path = out / "odds_asof_clean.csv"
        excluded_path = out / "odds_asof_excluded.csv"
        _empty_odds(clean_path); _empty_odds(excluded_path)
        asof_report = out / "odds_asof_report.md"
        asof_report.write_text("# v2.0 Odds As-Of Report\n\nNo valid odds.\n", encoding="utf-8")
        result.update({"odds_asof_status": "PARTIAL", "odds_available": False, "odds_1x2_available": False, "odds_totals_available": False, "odds_asof_clean_path": str(clean_path.resolve()), "odds_asof_excluded_path": str(excluded_path.resolve()), "odds_asof_report_path": str(asof_report.resolve())})
    (out / "odds_api_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = out / "odds_api_adapter_report.md"
    report.write_text(f"# v2.0 Odds API Historical Adapter\n\n- status: {status}\n- api_key_present: {str(key_present).lower()}\n- odds_1x2_available: {str(result.get('odds_1x2_available', False)).lower()}\n\nNo API key value is written.\n", encoding="utf-8")
    result["odds_api_result_json_path"] = str((out / "odds_api_result.json").resolve())
    result["odds_api_adapter_report_path"] = str(report.resolve())
    return result
