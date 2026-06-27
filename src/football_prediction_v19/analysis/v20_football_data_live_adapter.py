# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    url = build_football_data_url(mapping.season_input, mapping.football_data_code)
    status = "SUCCESS"
    raw_text = ""
    cache_result, cached = read_cache(cache_root, cache_key, cache_ttl_hours)
    cache_write_success = False
    network_attempted = False
    request_blocked = False
    fetch_success = False
    cache_error = ""
    reason = ""
    if cached:
        raw_text = cached
        status = "CACHE_HIT"
    elif mock_csv_path:
        raw_text = Path(mock_csv_path).read_text(encoding="utf-8")
        try:
            write_cache(cache_root, cache_key, raw_text)
            cache_write_success = True
        except Exception as exc:
            cache_error = str(exc)
    elif not mapping.football_data_code:
        status = "UNSUPPORTED_LEAGUE"
    elif not enable_network:
        status = "DISABLED_NETWORK"; request_blocked = True
    else:
        network_attempted = True
        try:
            raw_text = fetch_or_cache_football_data_csv(url)
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
    raw_path = out / "football_data_live_raw.csv"
    normalized_path = out / "football_data_live_normalized.csv"
    if not raw_text:
        _empty_football_csv(normalized_path)
        result = _result(status, out, raw_path, normalized_path, None, reason, cache_result.to_dict(), 0, diag, url, mapping)
        _write_report(out, result)
        return result
    raw_path.write_text(raw_text, encoding="utf-8")
    df = pd.read_csv(io.StringIO(raw_text), keep_default_na=False)
    normalized = normalize_football_data_csv(df)
    normalized.to_csv(normalized_path, index=False)
    asof = build_football_data_asof(normalized_path, context, out)
    result = _result(status, out, raw_path, normalized_path, asof, reason, cache_result.to_dict(), len(normalized), diag, url, mapping, candidate_matches=football_data_candidate_matches(normalized, context.home_team, context.away_team, context.match_date))
    _write_report(out, result)
    return result


def normalize_football_data_live_frame(df: pd.DataFrame) -> pd.DataFrame:
    return normalize_football_data_csv(df)


def build_football_data_url(season: str, league_code: str) -> str:
    from football_prediction_v19.analysis.v20_source_league_resolver import football_data_season_code
    return f"https://www.football-data.co.uk/mmz4281/{football_data_season_code(season)}/{league_code}.csv"


def fetch_or_cache_football_data_csv(url: str, timeout_seconds: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "football-prediction-v20-preview/1.0"})
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"URL error for {url}: {exc.reason}") from exc


def normalize_football_data_csv(df: pd.DataFrame) -> pd.DataFrame:
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


def football_data_candidate_matches(df: pd.DataFrame, home_team: str, away_team: str, match_date: str, date_tolerance_days: int = 1) -> list[dict[str, object]]:
    if df.empty:
        return []
    dates = _parse_dates(df["Date"])
    target = pd.to_datetime(match_date)
    home_norm = _norm(home_team); away_norm = _norm(away_team)
    rows = []
    for idx, row in df.iterrows():
        hn = _norm(row.get("HomeTeam", "")); an = _norm(row.get("AwayTeam", ""))
        same_pair = hn == home_norm and an == away_norm
        fuzzy_pair = home_norm in hn or hn in home_norm or away_norm in an or an in away_norm
        date_delta = abs((dates.iloc[idx] - target).days) if pd.notna(dates.iloc[idx]) else 9999
        if same_pair or fuzzy_pair:
            confidence = 1.0 if same_pair and date_delta == 0 else (0.85 if same_pair and date_delta <= date_tolerance_days else 0.55)
            rows.append({"source": "football_data", "home_team": row.get("HomeTeam", ""), "away_team": row.get("AwayTeam", ""), "date": row.get("Date", ""), "score": f"{row.get('FTHG', '')}-{row.get('FTAG', '')}", "confidence": confidence, "reason": "exact" if confidence == 1.0 else ("date_tolerance" if date_delta <= date_tolerance_days else "season_team_pair")})
    return rows[:20]


def _empty_football_csv(path: Path) -> None:
    pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "B365H", "B365D", "B365A"]).to_csv(path, index=False)


def _result(status: str, out: Path, raw_path: Path, normalized_path: Path, asof: dict[str, object] | None, warnings: str | None, cache: dict[str, object], rows: int, cache_diagnostics: dict[str, object], url: str, mapping: SourceLeagueMapping, candidate_matches: list[dict[str, object]] | None = None) -> dict[str, object]:
    payload = {
        "football_data_live_status": status,
        "status": status,
        "reason": warnings or _status_reason(status),
        "url": url,
        "season_code": mapping.football_data_season_code,
        "league_code": mapping.football_data_code,
        "cache_key": cache.get("cache_key", ""),
        "cache_path": cache.get("cache_path", ""),
        "cache_written": bool(cache_diagnostics.get("cache_write_success")),
        "fetch_attempted": bool(cache_diagnostics.get("network_attempted")),
        "fetch_success": bool(cache_diagnostics.get("fetch_success")),
        "records_count": rows,
        "rows_count": rows,
        "cache_used": status == "CACHE_HIT",
        "football_data_live_raw_path": str(raw_path.resolve()),
        "football_data_live_normalized_path": str(normalized_path.resolve()),
        "cache_status": cache,
        "cache_diagnostics": cache_diagnostics,
        "warnings": warnings or "",
        "candidate_matches": candidate_matches or [],
        "recommended_fix": "" if status in {"SUCCESS", "CACHE_HIT"} else f"Check URL/cache/source availability for {url}",
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
                f"- url: {result.get('url')}",
                f"- cache_written: {str(result.get('cache_written')).lower()}",
                f"- candidate_matches: {len(result.get('candidate_matches', []))}",
                f"- records_count: {result['records_count']}",
                f"- cache_used: {str(result['cache_used']).lower()}",
                f"- table_available: {str(result.get('table_available', False)).lower()}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result["football_data_live_adapter_report_path"] = str(path.resolve())


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
    }.get(status, status.lower())


def _norm(value: object) -> str:
    return " ".join(str(value).strip().lower().replace("-", " ").split())


def _parse_dates(values: object) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce", format="%Y-%m-%d")
    if parsed.isna().all():
        parsed = pd.to_datetime(values, errors="coerce", dayfirst=True)
    return parsed
