# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext
from football_prediction_v19.analysis.v20_live_source_cache import build_cache_key, read_cache, write_cache
from football_prediction_v19.analysis.v20_source_league_resolver import SourceLeagueMapping
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof


def run_understat_live_adapter(
    mapping: SourceLeagueMapping,
    context: HistoricalMatchContext,
    output_dir: str | Path,
    *,
    enable_network: bool = False,
    cache_dir: str | Path | None = None,
    mock_json_path: str | Path | None = None,
    mock_players_json_path: str | Path | None = None,
    cache_ttl_hours: float = 24,
) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    cache_root = Path(cache_dir or out / "cache")
    cache_key = build_cache_key("understat", mapping.canonical_competition, mapping.season_input, "league_json", {"league": mapping.understat_league_code})
    url = build_understat_league_url(mapping.understat_league_code, mapping.understat_season or mapping.season_input)
    status = "SUCCESS"
    cache_result, cached = read_cache(cache_root, cache_key, cache_ttl_hours)
    cache_write_success = False
    network_attempted = False
    request_blocked = False
    fetch_success = False
    cache_error = ""
    reason = ""
    raw_text = cached
    if raw_text:
        status = "CACHE_HIT"
    elif mock_json_path:
        raw_text = Path(mock_json_path).read_text(encoding="utf-8")
        try:
            write_cache(cache_root, cache_key, raw_text)
            cache_write_success = True
        except Exception as exc:
            cache_error = str(exc)
    elif not mapping.understat_league_code:
        status = "UNSUPPORTED_LEAGUE"
    elif not enable_network:
        status = "DISABLED_NETWORK"; request_blocked = True
    else:
        network_attempted = True
        try:
            raw_text = fetch_or_cache_understat_league(url)
            fetch_success = True
            try:
                write_cache(cache_root, cache_key, raw_text)
                cache_write_success = True
            except Exception as exc:
                cache_error = str(exc)
        except Exception as exc:
            status = "FAILED_FETCH"; reason = str(exc)
    fetch_success = bool(raw_text)
    diag = _cache_diag(cache_result.to_dict(), network_attempted, request_blocked, fetch_success, bool(cached), cache_write_success, cache_error)
    raw_path = out / "understat_live_raw.json"
    matches_path = out / "understat_live_matches_normalized.csv"
    players_path = out / "understat_live_players_normalized.csv"
    if not raw_text:
        pd.DataFrame(columns=["date", "home_team", "away_team", "home_xg", "away_xg"]).to_csv(matches_path, index=False)
        pd.DataFrame(columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"]).to_csv(players_path, index=False)
        return _finish(out, status, raw_path, matches_path, players_path, None, cache_result.to_dict(), 0, diag, url, mapping, reason)
    raw_path.write_text(raw_text, encoding="utf-8")
    try:
        payload = json.loads(raw_text)
        matches = normalize_understat_matches(payload)
        players = normalize_understat_players(json.loads(Path(mock_players_json_path).read_text(encoding="utf-8")) if mock_players_json_path else payload)
    except Exception:
        matches = pd.DataFrame(columns=["date", "home_team", "away_team", "home_xg", "away_xg"])
        players = pd.DataFrame(columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"])
        status = "FAILED_PARSE"
    matches.to_csv(matches_path, index=False)
    players.to_csv(players_path, index=False)
    asof = build_understat_xg_asof(matches_path, players_path, context, out) if not matches.empty else None
    return _finish(out, status, raw_path, matches_path, players_path, asof, cache_result.to_dict(), len(matches), diag, url, mapping, reason, candidate_matches=understat_candidate_matches(matches, context.home_team, context.away_team, context.match_date))


def build_understat_league_url(league_code: str, season_start_year: str | int) -> str:
    year = str(season_start_year)[:4]
    return f"https://understat.com/league/{league_code}/{year}"


def fetch_or_cache_understat_league(url: str, timeout_seconds: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "football-prediction-v20-preview/1.0"})
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"URL error for {url}: {exc.reason}") from exc


def normalize_understat_matches(payload: dict[str, object] | list[object]) -> pd.DataFrame:
    rows = payload.get("matches", payload) if isinstance(payload, dict) else payload
    records = []
    for row in rows if isinstance(rows, list) else []:
        home = row.get("home_team") or (row.get("h", {}).get("title") if isinstance(row.get("h"), dict) else row.get("home"))
        away = row.get("away_team") or (row.get("a", {}).get("title") if isinstance(row.get("a"), dict) else row.get("away"))
        xg = row.get("xG", {}) if isinstance(row.get("xG"), dict) else {}
        records.append({
            "date": row.get("date") or row.get("datetime") or row.get("match_date"),
            "home_team": home,
            "away_team": away,
            "home_xg": row.get("home_xg", xg.get("h", "")),
            "away_xg": row.get("away_xg", xg.get("a", "")),
        })
    return pd.DataFrame(records)


def understat_candidate_matches(df: pd.DataFrame, home_team: str, away_team: str, match_date: str, date_tolerance_days: int = 1) -> list[dict[str, object]]:
    if df.empty:
        return []
    dates = pd.to_datetime(df["date"], errors="coerce")
    target = pd.to_datetime(match_date)
    home_norm = _norm(home_team); away_norm = _norm(away_team)
    rows = []
    for idx, row in df.iterrows():
        hn = _norm(row.get("home_team", "")); an = _norm(row.get("away_team", ""))
        same_pair = hn == home_norm and an == away_norm
        fuzzy_pair = home_norm in hn or hn in home_norm or away_norm in an or an in away_norm
        delta = abs((dates.iloc[idx] - target).days) if pd.notna(dates.iloc[idx]) else 9999
        if same_pair or fuzzy_pair:
            confidence = 1.0 if same_pair and delta == 0 else (0.85 if same_pair and delta <= date_tolerance_days else 0.55)
            rows.append({"source": "understat", "home_team": row.get("home_team", ""), "away_team": row.get("away_team", ""), "date": row.get("date", ""), "match_id": row.get("id", ""), "confidence": confidence, "reason": "exact" if confidence == 1.0 else ("date_tolerance" if delta <= date_tolerance_days else "season_team_pair")})
    return rows[:20]


def normalize_understat_players(payload: dict[str, object] | list[object]) -> pd.DataFrame:
    rows = payload.get("players", []) if isinstance(payload, dict) else []
    records = []
    for row in rows:
        records.append({
            "date": row.get("date", ""),
            "player": row.get("player") or row.get("player_name", ""),
            "team": row.get("team", ""),
            "minutes": row.get("minutes", 0),
            "goals": row.get("goals", 0),
            "assists": row.get("assists", 0),
            "xg": row.get("xg", row.get("xG", 0)),
            "xa": row.get("xa", row.get("xA", 0)),
            "npxg": row.get("npxg", row.get("npxG", row.get("xg", row.get("xG", 0)))),
        })
    return pd.DataFrame(records, columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"])


def _finish(out: Path, status: str, raw_path: Path, matches_path: Path, players_path: Path, asof: dict[str, object] | None, cache: dict[str, object], rows: int, cache_diagnostics: dict[str, object], url: str, mapping: SourceLeagueMapping, reason: str = "", candidate_matches: list[dict[str, object]] | None = None) -> dict[str, object]:
    result = {
        "understat_live_status": status,
        "status": status,
        "reason": reason or _status_reason(status),
        "url": url,
        "league_code": mapping.understat_league_code,
        "season_start_year": mapping.understat_season,
        "cache_key": cache.get("cache_key", ""),
        "cache_path": cache.get("cache_path", ""),
        "cache_written": bool(cache_diagnostics.get("cache_write_success")),
        "fetch_attempted": bool(cache_diagnostics.get("network_attempted")),
        "fetch_success": bool(cache_diagnostics.get("fetch_success")),
        "records_count": rows,
        "rows_count": rows,
        "parse_success": status != "FAILED_PARSE",
        "cache_used": status == "CACHE_HIT",
        "understat_live_raw_path": str(raw_path.resolve()),
        "understat_live_matches_normalized_path": str(matches_path.resolve()),
        "understat_live_players_normalized_path": str(players_path.resolve()),
        "cache_status": cache,
        "cache_diagnostics": cache_diagnostics,
        "candidate_matches": candidate_matches or [],
    }
    if asof:
        result.update(asof)
    else:
        team_path = out / "understat_xg_asof_team.csv"
        player_path = out / "understat_xg_asof_player.csv"
        pd.DataFrame(columns=["team", "matches_count", "xg_for", "xg_against", "xg_diff"]).to_csv(team_path, index=False)
        pd.DataFrame(columns=["player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"]).to_csv(player_path, index=False)
        asof_report = out / "understat_xg_asof_report.md"
        asof_report.write_text("# v2.0 Understat xG As-Of Report\n\nNo xG rows.\n", encoding="utf-8")
        result.update({"understat_xg_asof_status": "PARTIAL", "xg_available": False, "player_xg_available": False, "understat_xg_asof_team_path": str(team_path.resolve()), "understat_xg_asof_player_path": str(player_path.resolve()), "understat_xg_asof_report_path": str(asof_report.resolve())})
    (out / "understat_live_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report = out / "understat_live_adapter_report.md"
    report.write_text(f"# v2.0 Understat Live Adapter\n\n- status: {status}\n- url: {url}\n- reason: {result['reason']}\n- records_count: {rows}\n- cache_written: {str(result.get('cache_written')).lower()}\n- candidate_matches: {len(result.get('candidate_matches', []))}\n- xg_available: {str(result.get('xg_available', False)).lower()}\n", encoding="utf-8")
    result["understat_live_result_json_path"] = str((out / "understat_live_result.json").resolve())
    result["understat_live_adapter_report_path"] = str(report.resolve())
    return result


def _cache_diag(cache: dict[str, object], network_attempted: bool, request_blocked: bool, fetch_success: bool, cache_hit: bool, cache_write_success: bool, cache_error: str) -> dict[str, object]:
    return {
        "cache_lookup_attempted": True,
        "cache_hit": cache_hit,
        "expected_cache_path": cache.get("cache_path", ""),
        "network_attempted": network_attempted,
        "request_blocked": request_blocked,
        "fetch_success": fetch_success,
        "cache_write_attempted": fetch_success and not cache_hit,
        "cache_write_success": cache_write_success,
        "cache_error": cache_error,
    }


def _status_reason(status: str) -> str:
    return {
        "SUCCESS": "source normalized successfully",
        "CACHE_HIT": "cache hit",
        "DISABLED_NETWORK": "network disabled and cache unavailable",
        "UNSUPPORTED_LEAGUE": "league code unavailable",
        "FAILED_FETCH": "network fetch failed",
        "FAILED_PARSE": "payload parse failed",
    }.get(status, status.lower())


def _norm(value: object) -> str:
    return " ".join(str(value).strip().lower().replace("-", " ").split())
