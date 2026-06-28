# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league


def build_supported_evaluation_sample(
    competitions: list[str] | str,
    season: str,
    target_matches: int = 40,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
    output_csv: str | Path = "config/v28_source_supported_eval_sample.csv",
) -> dict[str, object]:
    del source_profile
    comps = _competitions(competitions)
    rows: list[dict[str, object]] = []
    used: list[str] = []
    for competition in comps:
        fixtures = _load_supported_fixtures(competition, season, enable_network=enable_network, cache_only=cache_only)
        if fixtures:
            used.append(competition)
        for fixture in fixtures:
            rows.append(fixture)
            if len(rows) >= target_matches:
                break
        if len(rows) >= target_matches:
            break
    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    columns = ["competition", "season", "home_team", "away_team", "match_date", "expected_result_source"]
    pd.DataFrame(rows, columns=columns).to_csv(out, index=False)
    status = "READY" if len(rows) >= target_matches else ("PARTIAL_SAMPLE" if rows else "DATA_BLOCKED")
    return {
        "v28_sample_builder_status": status,
        "sample_builder_status": status,
        "requested_target_matches": int(target_matches),
        "matches_written": int(len(rows)),
        "competitions_used": ",".join(used),
        "source_used": "football_data",
        "reason": "source-supported sample built" if rows else "no supported source rows found",
        "output_csv": str(out.resolve()),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _load_supported_fixtures(competition: str, season: str, *, enable_network: bool, cache_only: bool) -> list[dict[str, object]]:
    out = Path("outputs/v28_supported_sample_builder") / _slug(f"{competition}_{season}")
    mapping = resolve_source_league(competition, season, out / "mapping")
    context = build_match_context("Sample Home", "Sample Away", competition, season, _season_anchor_date(season))
    live = run_football_data_live_adapter(
        mapping,
        context,
        out / "football_data",
        enable_network=bool(enable_network and not cache_only),
        cache_dir=Path("outputs/cache/v20_live_sources"),
    )
    path = Path(str(live.get("football_data_live_normalized_path", "")))
    if not path.exists():
        return []
    frame = pd.read_csv(path, keep_default_na=False)
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for _, row in frame.iterrows():
        try:
            date = normalize_match_date(str(row.get("Date", "")))
        except Exception:
            continue
        home = str(row.get("HomeTeam", "")).strip()
        away = str(row.get("AwayTeam", "")).strip()
        if not home or not away or not date:
            continue
        if str(row.get("FTHG", "")).strip() == "" or str(row.get("FTAG", "")).strip() == "":
            continue
        key = (date, home, away)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "competition": competition,
                "season": season,
                "home_team": home,
                "away_team": away,
                "match_date": date,
                "expected_result_source": "football_data",
            }
        )
    return rows


def _competitions(value: list[str] | str) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _season_anchor_date(season: str) -> str:
    for token in str(season).replace("/", " ").replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return f"{token}-08-01"
    return "2025-08-01"


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())
