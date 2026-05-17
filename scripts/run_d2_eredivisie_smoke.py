"""Local smoke test for 2. Bundesliga (D2) and Eredivisie (N1) league support.

No internet required. Creates tiny synthetic match data, runs the prepare-data
pipeline, and verifies both leagues survive into processed output with correct
league names and team normalizations.

Also confirms no existing Top-5 or MLS workflow is broken.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from football_prediction_v19.data import prepare_real_matches
from football_prediction_v19.importers.football_data import LEAGUE_CODES, build_football_data_url
from football_prediction_v19.team_names import normalize_team_name


def _make_football_data_rows(div: str, n: int = 5) -> pd.DataFrame:
    """Create minimal synthetic football-data.co.uk style rows."""
    teams = {
        "D2": [
            ("Hamburger SV", "FC Schalke 04"),
            ("Hertha BSC", "1. FC Nürnberg"),
            ("Fortuna Düsseldorf", "Karlsruher SC"),
            ("SpVgg Greuther Fürth", "Hannover 96"),
            ("SV Darmstadt 98", "1. FC Kaiserslautern"),
        ],
        "N1": [
            ("AFC Ajax", "PSV Eindhoven"),
            ("Feyenoord", "AZ Alkmaar"),
            ("FC Twente", "FC Utrecht"),
            ("SC Heerenveen", "NEC Nijmegen"),
            ("PEC Zwolle", "Heracles Almelo"),
        ],
    }
    rows = []
    for i, (home, away) in enumerate(teams[div][:n]):
        rows.append({
            "Div": div,
            "Date": f"20/08/202{i % 3 + 2}",
            "HomeTeam": home,
            "AwayTeam": away,
            "FTHG": 1,
            "FTAG": 1,
            "FTR": "D",
            "B365H": 2.50,
            "B365D": 3.20,
            "B365A": 2.80,
        })
    return pd.DataFrame(rows)


def check(condition: bool, label: str) -> None:
    status = "  [OK]" if condition else "  [FAIL]"
    print(f"{status} {label}")
    if not condition:
        sys.exit(1)


def main() -> None:
    print("=== D2 / Eredivisie Smoke Test ===\n")

    # ── 1. League code mapping ─────────────────────────────────────────
    print("1. League code mapping")
    check("bundesliga-2" in LEAGUE_CODES, "LEAGUE_CODES contains 'bundesliga-2'")
    check(LEAGUE_CODES["bundesliga-2"] == "D2", "bundesliga-2 -> D2")
    check("2-bundesliga" in LEAGUE_CODES, "LEAGUE_CODES contains '2-bundesliga'")
    check(LEAGUE_CODES["2-bundesliga"] == "D2", "2-bundesliga -> D2")
    check("eredivisie" in LEAGUE_CODES, "LEAGUE_CODES contains 'eredivisie'")
    check(LEAGUE_CODES["eredivisie"] == "N1", "eredivisie -> N1")

    # ── 2. _DIV_TO_LEAGUE renaming ─────────────────────────────────────
    print("\n2. _DIV_TO_LEAGUE human-readable names")
    from football_prediction_v19.data import _DIV_TO_LEAGUE
    check(_DIV_TO_LEAGUE.get("D2") == "2. Bundesliga", "D2 -> '2. Bundesliga'")
    check(_DIV_TO_LEAGUE.get("N1") == "Eredivisie", "N1 -> 'Eredivisie'")

    # ── 3. URL building ────────────────────────────────────────────────
    print("\n3. URL building")
    url_d2 = build_football_data_url("D2", 2023)
    check("D2.csv" in url_d2, f"D2 URL contains D2.csv: {url_d2}")
    url_n1 = build_football_data_url("N1", 2023)
    check("N1.csv" in url_n1, f"N1 URL contains N1.csv: {url_n1}")
    url_friendly = build_football_data_url("bundesliga-2", 2023)
    check("D2.csv" in url_friendly, "friendly 'bundesliga-2' resolves to D2.csv")
    url_friendly2 = build_football_data_url("2-bundesliga", 2023)
    check("D2.csv" in url_friendly2, "friendly '2-bundesliga' resolves to D2.csv")

    # ── 4. Team alias normalization — 2. Bundesliga ───────────────────
    print("\n4. 2. Bundesliga team alias normalization")
    d2_cases = [
        ("Schalke", "FC Schalke 04"),
        ("Schalke 04", "FC Schalke 04"),
        ("Hertha Berlin", "Hertha BSC"),
        ("HSV", "Hamburger SV"),
        ("Hamburg", "Hamburger SV"),
        ("Hannover", "Hannover 96"),
        ("Nurnberg", "1. FC Nürnberg"),
        ("Nürnberg", "1. FC Nürnberg"),
        ("1. FC Nurnberg", "1. FC Nürnberg"),
        ("Kaiserslautern", "1. FC Kaiserslautern"),
        ("Dusseldorf", "Fortuna Düsseldorf"),
        ("Karlsruhe", "Karlsruher SC"),
        ("Greuther Furth", "SpVgg Greuther Fürth"),
        ("Paderborn", "SC Paderborn 07"),
        ("Magdeburg", "1. FC Magdeburg"),
        ("Braunschweig", "Eintracht Braunschweig"),
        ("Darmstadt", "SV Darmstadt 98"),
        ("Kiel", "Holstein Kiel"),
        ("St. Pauli", "FC St. Pauli"),
        ("Ulm", "SSV Ulm 1846"),
        ("Preussen Munster", "Preußen Münster"),
        ("Elversberg", "SV Elversberg"),
        ("Bielefeld", "Arminia Bielefeld"),
    ]
    for alias, canonical in d2_cases:
        result = normalize_team_name(alias)
        check(result == canonical, f"'{alias}' -> '{canonical}' (got '{result}')")

    # ── 5. Team alias normalization — Eredivisie ──────────────────────
    print("\n5. Eredivisie team alias normalization")
    n1_cases = [
        ("Ajax", "AFC Ajax"),
        ("PSV", "PSV Eindhoven"),
        ("AZ", "AZ Alkmaar"),
        ("Twente", "FC Twente"),
        ("Utrecht", "FC Utrecht"),
        ("Heerenveen", "SC Heerenveen"),
        ("Groningen", "FC Groningen"),
        ("NEC", "NEC Nijmegen"),
        ("Nijmegen", "NEC Nijmegen"),
        ("Heracles", "Heracles Almelo"),
        ("Zwolle", "PEC Zwolle"),
        ("Sittard", "Fortuna Sittard"),
        ("RKC", "RKC Waalwijk"),
        ("Almere City", "Almere City FC"),
        ("Volendam", "FC Volendam"),
        ("Excelsior", "Excelsior Rotterdam"),
        ("Go Ahead", "Go Ahead Eagles"),
        ("NAC", "NAC Breda"),
    ]
    for alias, canonical in n1_cases:
        result = normalize_team_name(alias)
        check(result == canonical, f"'{alias}' -> '{canonical}' (got '{result}')")

    # ── 6. prepare_real_matches for D2 ────────────────────────────────
    print("\n6. prepare_real_matches preserves 2. Bundesliga name")
    d2_raw = _make_football_data_rows("D2")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        d2_raw.to_csv(f, index=False)
        d2_path = f.name
    try:
        d2_clean = prepare_real_matches(pd.read_csv(d2_path, encoding="utf-8"), input_format="football-data")
        check(len(d2_clean) == 5, f"D2: 5 rows prepared (got {len(d2_clean)})")
        leagues = d2_clean["league"].unique().tolist()
        check("2. Bundesliga" in leagues, f"D2: league name is '2. Bundesliga' (got {leagues})")
    finally:
        Path(d2_path).unlink(missing_ok=True)

    # ── 7. prepare_real_matches for N1 ────────────────────────────────
    print("\n7. prepare_real_matches preserves Eredivisie name")
    n1_raw = _make_football_data_rows("N1")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        n1_raw.to_csv(f, index=False)
        n1_path = f.name
    try:
        n1_clean = prepare_real_matches(pd.read_csv(n1_path, encoding="utf-8"), input_format="football-data")
        check(len(n1_clean) == 5, f"N1: 5 rows prepared (got {len(n1_clean)})")
        leagues = n1_clean["league"].unique().tolist()
        check("Eredivisie" in leagues, f"N1: league name is 'Eredivisie' (got {leagues})")
    finally:
        Path(n1_path).unlink(missing_ok=True)

    # ── 8. Mixed D2 + N1 + existing leagues survive together ──────────
    print("\n8. Mixed D2 + N1 + Top-5 leagues survive together")
    existing_rows = []
    for div, home, away in [
        ("D1", "Bayern Munich", "Borussia Dortmund"),
        ("E0", "Arsenal", "Chelsea"),
        ("SP1", "Real Madrid", "Barcelona"),
        ("D2", "Hamburger SV", "FC Schalke 04"),
        ("N1", "AFC Ajax", "PSV Eindhoven"),
    ]:
        existing_rows.append({
            "Div": div, "Date": "20/08/2023",
            "HomeTeam": home, "AwayTeam": away,
            "FTHG": 2, "FTAG": 1, "FTR": "H",
            "B365H": 1.80, "B365D": 3.50, "B365A": 4.00,
        })
    mixed_raw = pd.DataFrame(existing_rows)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        mixed_raw.to_csv(f, index=False)
        mixed_path = f.name
    try:
        mixed_clean = prepare_real_matches(pd.read_csv(mixed_path, encoding="utf-8"), input_format="football-data")
        check(len(mixed_clean) == 5, f"Mixed: 5 rows prepared (got {len(mixed_clean)})")
        expected_leagues = {"Bundesliga", "Premier League", "La Liga", "2. Bundesliga", "Eredivisie"}
        actual_leagues = set(mixed_clean["league"].unique())
        check(expected_leagues == actual_leagues, f"Mixed: correct league names {actual_leagues}")
    finally:
        Path(mixed_path).unlink(missing_ok=True)

    # ── 9. Existing MLS aliases still work ────────────────────────────
    print("\n9. Existing MLS aliases still work")
    mls_cases = [
        ("NE Revolution", "New England Revolution"),
        ("SJ Earthquakes", "San Jose Earthquakes"),
        ("Minnesota Utd", "Minnesota United"),
        ("LAFC", "Los Angeles FC"),
        ("LA FC", "Los Angeles FC"),
    ]
    for alias, canonical in mls_cases:
        result = normalize_team_name(alias)
        check(result == canonical, f"MLS: '{alias}' -> '{canonical}'")

    # ── 10. Existing Premier League aliases still work ─────────────────
    print("\n10. Existing Premier League aliases still work")
    pl_cases = [
        ("Man Utd", "Manchester United"),
        ("Spurs", "Tottenham Hotspur"),
        ("Brighton", "Brighton & Hove Albion"),
        ("Wolves", "Wolverhampton Wanderers"),
    ]
    for alias, canonical in pl_cases:
        result = normalize_team_name(alias)
        check(result == canonical, f"PL: '{alias}' -> '{canonical}'")

    print("\n=== All smoke tests passed ===")


if __name__ == "__main__":
    main()
