from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import requests as _requests_module
except ImportError:
    _requests_module = None  # type: ignore

from ..team_names import normalize_team_name

SPORT_KEY = "soccer_usa_mls"
BASE_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"

OUTPUT_COLUMNS = [
    "date", "home_team", "away_team",
    "odds_home", "odds_draw", "odds_away",
    "bookmaker", "market", "updated_at",
]


def fetch_mls_odds(
    api_key: str,
    output_path: str | Path | None = None,
    regions: str = "us",
    markets: str = "h2h",
    odds_format: str = "decimal",
    bookmaker: str | None = None,
) -> pd.DataFrame:
    """Fetch upcoming MLS odds from The Odds API.

    Requires a valid API key from https://the-odds-api.com
    Store as environment variable THE_ODDS_API_KEY or pass via --api-key.
    """
    import football_prediction_v19.importers.the_odds_api as _self
    _req = _self._requests_module
    if _req is None:
        raise ImportError("The 'requests' library is required. Install it with: pip install requests")

    url = BASE_URL.format(sport=SPORT_KEY)
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": odds_format,
    }
    response = _req.get(url, params=params, timeout=30)
    if response.status_code == 401:
        raise ValueError("Invalid API key. Set THE_ODDS_API_KEY or use --api-key.")
    if response.status_code == 422:
        raise ValueError(f"API request error (422): {response.text}")
    response.raise_for_status()

    payload = response.json()
    if not payload:
        raise ValueError(
            "The Odds API returned no MLS events. "
            "The season may be out of season or the sport key may be incorrect. "
            f"Sport key used: {SPORT_KEY}"
        )

    df = parse_the_odds_api_events(payload, preferred_bookmaker=bookmaker)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df


def parse_the_odds_api_events(
    payload: list[dict[str, Any]],
    preferred_bookmaker: str | None = None,
) -> pd.DataFrame:
    """Parse The Odds API JSON response into a normalized DataFrame."""
    rows = []
    for event in payload:
        home_team = normalize_team_name(event.get("home_team", ""))
        away_team = normalize_team_name(event.get("away_team", ""))
        commence_time = event.get("commence_time", "")
        try:
            date_str = pd.to_datetime(commence_time, utc=True).strftime("%Y-%m-%d")
        except Exception:
            date_str = str(commence_time)[:10]

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        # Select bookmaker
        selected = None
        if preferred_bookmaker:
            for bm in bookmakers:
                key = bm.get("key", "").lower()
                title = bm.get("title", "").lower()
                if preferred_bookmaker.lower() in (key, title):
                    selected = bm
                    break
        if selected is None:
            selected = bookmakers[0]

        bm_key = selected.get("key", "")
        updated_at = selected.get("last_update", "")

        # Find h2h market
        h2h = None
        for mkt in selected.get("markets", []):
            if mkt.get("key") == "h2h":
                h2h = mkt
                break
        if h2h is None:
            continue

        outcomes = {o["name"]: o["price"] for o in h2h.get("outcomes", [])}

        # Map outcomes: home team name -> odds_home, away team name -> odds_away, Draw -> odds_draw
        odds_home = outcomes.get(event.get("home_team", ""), None)
        odds_away = outcomes.get(event.get("away_team", ""), None)
        odds_draw = outcomes.get("Draw", None)

        if odds_home is None and odds_away is None:
            continue

        rows.append({
            "date": date_str,
            "home_team": home_team,
            "away_team": away_team,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
            "bookmaker": bm_key,
            "market": "h2h",
            "updated_at": updated_at,
        })

    if not rows:
        raise ValueError(
            "No h2h odds found in the API response. "
            "Check that the 'h2h' market is available for MLS events."
        )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
