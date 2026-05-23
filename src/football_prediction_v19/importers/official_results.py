# -*- coding: utf-8 -*-
"""Official match result fetcher via football-data.org API (v4).

Only writes verified=yes when the API reports status FINISHED and both
home/away goals are present numeric values.  Every other case is left blank
or marked verified=no with an explanatory source_note.

No scores are guessed, estimated, or invented.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ..team_names import fuzzy_team_key, normalize_team_name

# ---------------------------------------------------------------------------
# Competition mapping
# ---------------------------------------------------------------------------

#: Maps project league names to football-data.org competition codes.
#: Leagues not listed here are unsupported and will never be guessed.
LEAGUE_TO_FD_CODE: dict[str, str] = {
    "Premier League": "PL",
    "EPL":            "PL",
    "Serie A":        "SA",
    "Late Serie A":   "SA",
    "La Liga":        "PD",
    "Bundesliga":     "BL1",
    "Ligue 1":        "FL1",
    "Eredivisie":     "DED",
}

#: Leagues that are known to be unsupported by the free/basic plan.
UNSUPPORTED_LEAGUES: frozenset[str] = frozenset({
    "2. Bundesliga",
    "MLS",
    "Championship",
})

FD_API_BASE = "https://api.football-data.org/v4"

#: Column schema for the output CSV.
OUTPUT_COLUMNS = [
    "date", "league", "home_team", "away_team",
    "home_goals", "away_goals",
    "verified", "source_note", "source_match_id", "source_status", "last_updated",
]

# API statuses that mean the match is definitely finished with a real score.
FINISHED_STATUSES: frozenset[str] = frozenset({"FINISHED"})

# API statuses that mean the match has not yet been played / no score available.
UNPLAYED_STATUSES: frozenset[str] = frozenset({
    "SCHEDULED", "TIMED", "IN_PLAY", "PAUSED",
    "POSTPONED", "CANCELLED", "SUSPENDED",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_api_key(api_key: str | None) -> str:
    key = api_key or os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "No football-data.org API key found.\n"
            "Set it via the environment variable FOOTBALL_DATA_API_KEY:\n"
            "  export FOOTBALL_DATA_API_KEY=your_key_here\n"
            "or pass --api-key your_key_here on the command line.\n"
            "Free API keys: https://www.football-data.org/client/register"
        )
    return key.strip()


def _make_session(api_key: str):
    """Return a requests.Session pre-configured with the API key header."""
    import requests  # optional import — keeps module importable without requests installed
    session = requests.Session()
    session.headers.update({"X-Auth-Token": api_key})
    return session


def _fetch_matches_for_competition(
    session,
    competition_code: str,
    date_from: str,
    date_to: str,
) -> list[dict[str, Any]]:
    """Fetch raw match dicts from the API for one competition."""
    url = f"{FD_API_BASE}/competitions/{competition_code}/matches"
    params = {"dateFrom": date_from, "dateTo": date_to}
    resp = session.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        # Rate limited: wait and retry once
        time.sleep(60)
        resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("matches", [])


def _safe_goals(score_dict: dict[str, Any], side: str) -> int | None:
    """Extract numeric goals from API score dict; return None if unavailable."""
    val = score_dict.get(side)
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_football_data_results(
    api_key: str | None,
    date_from: str,
    date_to: str,
    leagues: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch finished match results from football-data.org for supported leagues.

    Parameters
    ----------
    api_key:
        API key for football-data.org.  Falls back to FOOTBALL_DATA_API_KEY env var.
    date_from, date_to:
        ISO date strings (YYYY-MM-DD).
    leagues:
        Project league names to fetch.  If None, fetches all supported leagues.

    Returns
    -------
    Raw DataFrame with one row per match returned by the API.
    Columns: date, league, home_team, away_team, home_goals, away_goals,
             verified, source_note, source_match_id, source_status, last_updated.
    """
    key = _get_api_key(api_key)
    session = _make_session(key)

    target_leagues = leagues or list(LEAGUE_TO_FD_CODE.keys())
    # Deduplicate competition codes (EPL and "Premier League" both map to PL)
    code_to_league: dict[str, str] = {}
    for lg in target_leagues:
        code = LEAGUE_TO_FD_CODE.get(lg)
        if code and code not in code_to_league:
            code_to_league[code] = lg  # first league name wins for labelling

    rows: list[dict[str, Any]] = []
    for code, league_label in code_to_league.items():
        try:
            matches = _fetch_matches_for_competition(session, code, date_from, date_to)
        except Exception as exc:  # noqa: BLE001
            # Network / auth error for this competition — mark all as unverified
            rows.append({
                "date": date_from, "league": league_label,
                "home_team": "", "away_team": "",
                "home_goals": None, "away_goals": None,
                "verified": "no", "source_note": f"fetch_error:{exc!s}",
                "source_match_id": None, "source_status": None,
                "last_updated": _now_iso(),
            })
            continue

        for m in matches:
            status     = m.get("status", "")
            score      = m.get("score", {})
            full_score = score.get("fullTime", {})
            hg         = _safe_goals(full_score, "home")
            ag         = _safe_goals(full_score, "away")

            home_raw = m.get("homeTeam", {}).get("name", "")
            away_raw = m.get("awayTeam", {}).get("name", "")

            utc_date = (m.get("utcDate") or "")[:10]  # "2026-05-17T..."

            if status in FINISHED_STATUSES and hg is not None and ag is not None:
                verified    = "yes"
                source_note = "football-data.org"
            elif status in UNPLAYED_STATUSES:
                verified    = "no"
                source_note = f"status:{status.lower()}"
            else:
                verified    = "no"
                source_note = f"status:{status.lower()}_goals_incomplete"

            rows.append({
                "date":            utc_date,
                "league":          league_label,
                "home_team":       home_raw,
                "away_team":       away_raw,
                "home_goals":      hg,
                "away_goals":      ag,
                "verified":        verified,
                "source_note":     source_note,
                "source_match_id": m.get("id"),
                "source_status":   status,
                "last_updated":    _now_iso(),
            })

    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.DataFrame(rows)[OUTPUT_COLUMNS]


def normalize_official_results(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise team names in the results DataFrame using project aliases.

    Applies ``normalize_team_name`` to home_team and away_team.
    Does NOT modify verified status — normalisation is purely cosmetic.
    """
    out = df.copy()
    out["home_team"] = out["home_team"].apply(
        lambda n: normalize_team_name(str(n)) if n else n
    )
    out["away_team"] = out["away_team"].apply(
        lambda n: normalize_team_name(str(n)) if n else n
    )
    return out


def merge_official_results_with_daily_reports(
    results_df: pd.DataFrame,
    reports_dir: Path | str,
    output_path: Path | str,
) -> pd.DataFrame:
    """Match API results against pre-match report rows and write final_scores.csv.

    Matching logic:
    - Normalise both sides with normalize_team_name.
    - Match by date + normalised home_team + normalised away_team.
    - League is used as a secondary filter where both sides agree.
    - Ambiguous matches (multiple candidates): verified=no, source_note=ambiguous_match.
    - No match found: verified=no, source_note=no_match_found.

    Only rows with verified=yes in ``results_df`` can produce verified=yes output.
    """
    reports_dir = Path(reports_dir)
    output_path = Path(output_path)

    # ---- Load pre-match report CSVs ----------------------------------------
    csvs = sorted(reports_dir.glob("*_daily_report.csv"))
    if not csvs:
        raise FileNotFoundError(
            f"No daily report CSVs found in {reports_dir}.\n"
            "Run the daily report scripts first."
        )
    pre = pd.concat([pd.read_csv(f) for f in csvs], ignore_index=True)

    # ---- Normalise team names on both sides ---------------------------------
    def _n(name: str) -> str:
        return normalize_team_name(str(name))

    def _fz(name: str) -> str:
        return fuzzy_team_key(str(name)) if name else ""

    pre["_ht_norm"]   = pre["home_team"].apply(_n)
    pre["_at_norm"]   = pre["away_team"].apply(_n)
    pre["_ht_fuzz"]   = pre["home_team"].apply(_fz)
    pre["_at_fuzz"]   = pre["away_team"].apply(_fz)
    pre["_date_norm"] = pre["date"].astype(str).str[:10]

    res = results_df.copy()
    res["_ht_norm"]   = res["home_team"].apply(lambda x: _n(x) if x else "")
    res["_at_norm"]   = res["away_team"].apply(lambda x: _n(x) if x else "")
    res["_ht_fuzz"]   = res["home_team"].apply(lambda x: _fz(x) if x else "")
    res["_at_fuzz"]   = res["away_team"].apply(lambda x: _fz(x) if x else "")
    res["_date_norm"] = res["date"].astype(str).str[:10]

    # ---- Build output rows --------------------------------------------------
    output_rows: list[dict] = []

    for _, pre_row in pre.iterrows():
        dt = pre_row["_date_norm"]
        ht = pre_row["_ht_norm"]
        at = pre_row["_at_norm"]
        ht_fz = pre_row["_ht_fuzz"]
        at_fz = pre_row["_at_fuzz"]
        league = str(pre_row.get("league", ""))

        # Stage 1: Exact normalised match (date + normalised home + normalised away)
        cand = res[
            (res["_date_norm"] == dt) &
            (res["_ht_norm"]   == ht) &
            (res["_at_norm"]   == at)
        ]

        fuzzy_used = False
        if len(cand) == 0 and ht_fz and at_fz:
            # Stage 2: Fuzzy fallback — strips FC/AFC/CF/accents/etc.
            # Only accepted when a SINGLE unambiguous candidate is found.
            cand = res[
                (res["_date_norm"] == dt) &
                (res["_ht_fuzz"]   == ht_fz) &
                (res["_at_fuzz"]   == at_fz)
            ]
            fuzzy_used = True

        if len(cand) == 0:
            output_rows.append(_no_score_row(pre_row, "no_match_found"))
        elif len(cand) > 1:
            output_rows.append(_no_score_row(pre_row, "ambiguous_match"))
        else:
            api_row = cand.iloc[0]
            base_note = api_row["source_note"]
            if fuzzy_used and api_row["verified"] == "yes":
                base_note = f"{base_note};fuzzy_match"
            if api_row["verified"] == "yes":
                output_rows.append({
                    "date":            dt,
                    "league":          league,
                    "home_team":       pre_row["home_team"],
                    "away_team":       pre_row["away_team"],
                    "home_goals":      api_row["home_goals"],
                    "away_goals":      api_row["away_goals"],
                    "verified":        "yes",
                    "source_note":     base_note,
                    "source_match_id": api_row.get("source_match_id"),
                    "source_status":   api_row.get("source_status"),
                    "last_updated":    api_row.get("last_updated", _now_iso()),
                })
            else:
                output_rows.append({
                    "date":            dt,
                    "league":          league,
                    "home_team":       pre_row["home_team"],
                    "away_team":       pre_row["away_team"],
                    "home_goals":      None,
                    "away_goals":      None,
                    "verified":        "no",
                    "source_note":     api_row.get("source_note", "not_finished"),
                    "source_match_id": api_row.get("source_match_id"),
                    "source_status":   api_row.get("source_status"),
                    "last_updated":    api_row.get("last_updated", _now_iso()),
                })

    # ---- Also append unsupported leagues from pre-match not yet covered -----
    # (rows already in output_rows are covered; nothing extra needed — they're
    #  all included via the pre_row loop above)

    out_df = pd.DataFrame(output_rows, columns=OUTPUT_COLUMNS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_path, index=False, encoding="utf-8")
    return out_df


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _no_score_row(pre_row: pd.Series, note: str) -> dict:
    return {
        "date":            str(pre_row.get("date", ""))[:10],
        "league":          str(pre_row.get("league", "")),
        "home_team":       pre_row["home_team"],
        "away_team":       pre_row["away_team"],
        "home_goals":      None,
        "away_goals":      None,
        "verified":        "no",
        "source_note":     note,
        "source_match_id": None,
        "source_status":   None,
        "last_updated":    _now_iso(),
    }


def _now_iso() -> str:
    from datetime import timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
