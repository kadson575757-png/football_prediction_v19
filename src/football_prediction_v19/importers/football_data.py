from __future__ import annotations

from pathlib import Path
from typing import Sequence

import requests

from ..data import prepare_real_matches_file

# League codes used by football-data.co.uk
LEAGUE_CODES: dict[str, str] = {
    "premier-league": "E0",
    "championship": "E1",
    "league-one": "E2",
    "league-two": "E3",
    "national-league": "EC",
    "scottish-premiership": "SC0",
    "bundesliga": "D1",
    "bundesliga-2": "D2",
    "serie-a": "I1",
    "serie-b": "I2",
    "la-liga": "SP1",
    "segunda-division": "SP2",
    "ligue-1": "F1",
    "ligue-2": "F2",
    "eredivisie": "N1",
    "pro-league": "B1",
    "primeira-liga": "P1",
    "super-lig": "T1",
    "super-league-greece": "G1",
}

_BASE_URL = "https://www.football-data.co.uk/mmz4281"


def build_football_data_url(league_code: str, season: int) -> str:
    """Build the CSV download URL for a given league code and season start year.

    Args:
        league_code: football-data.co.uk code (e.g. "E0") or friendly name (e.g. "premier-league").
        season: four-digit start year of the season, e.g. 2023 for 2023-24.

    Returns:
        Full URL string.
    """
    code = LEAGUE_CODES.get(league_code, league_code)
    yy_start = str(season)[-2:]
    yy_end = str(season + 1)[-2:]
    season_str = f"{yy_start}{yy_end}"
    return f"{_BASE_URL}/{season_str}/{code}.csv"


def download_football_data_csv(url: str, output_path: str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    output.write_bytes(response.content)
    return output


def download_season(
    league_code: str,
    season: int,
    output_dir: str | Path,
) -> Path:
    """Download one league/season CSV from football-data.co.uk.

    Args:
        league_code: football-data.co.uk code (e.g. "E0") or friendly name.
        season: four-digit start year, e.g. 2023 for 2023-24.
        output_dir: directory where the file will be saved.

    Returns:
        Path to the downloaded file.
    """
    code = LEAGUE_CODES.get(league_code, league_code)
    url = build_football_data_url(league_code, season)
    filename = f"{code}_{season}_{season + 1}.csv"
    output_path = Path(output_dir) / filename
    return download_football_data_csv(url, str(output_path))


def bulk_download(
    league_codes: Sequence[str],
    seasons: Sequence[int],
    output_dir: str | Path,
) -> list[Path]:
    """Download multiple league/season CSVs from football-data.co.uk.

    Args:
        league_codes: list of codes or friendly names (e.g. ["E0", "D1"]).
        seasons: list of season start years (e.g. [2022, 2023]).
        output_dir: directory where files will be saved.

    Returns:
        List of paths to downloaded files.
    """
    downloaded: list[Path] = []
    for league_code in league_codes:
        for season in seasons:
            path = download_season(league_code, season, output_dir)
            downloaded.append(path)
    return downloaded


def download_and_prepare(
    league_code: str,
    season: int,
    raw_dir: str | Path,
    processed_dir: str | Path,
) -> dict[str, object]:
    """Download a football-data.co.uk CSV and prepare it for training.

    Args:
        league_code: football-data.co.uk code (e.g. "E0") or friendly name.
        season: four-digit start year, e.g. 2023 for 2023-24.
        raw_dir: directory where the raw CSV is saved.
        processed_dir: directory where the cleaned CSV is saved.

    Returns:
        Dict with keys: league_code, season, raw_path, processed_path, and
        the prepare summary fields (rows_read, rows_written, rows_dropped, …).

    Raises:
        ValueError: if the league code is unknown or the processed output is empty.
        requests.HTTPError: if the download fails.
    """
    code = LEAGUE_CODES.get(league_code, league_code)
    if code not in LEAGUE_CODES.values():
        known = ", ".join(sorted(LEAGUE_CODES))
        raise ValueError(
            f"Unknown league '{league_code}'. "
            f"Use a raw code (e.g. E0, D1) or a friendly name: {known}."
        )

    raw_path = Path(raw_dir) / f"football_data_{code}_{season}.csv"
    processed_path = Path(processed_dir) / f"football_data_{code}_{season}_clean.csv"

    url = build_football_data_url(league_code, season)
    download_football_data_csv(url, str(raw_path))

    summary = normalize_football_data_csv(str(raw_path), str(processed_path))

    if summary["rows_written"] == 0:
        raise ValueError(
            f"Processed file for {code} season {season} is empty — "
            "no complete historical rows found in the downloaded CSV."
        )

    return {
        "league_code": code,
        "season": season,
        "raw_path": str(raw_path),
        "processed_path": str(processed_path),
        **summary,
    }


def normalize_football_data_csv(input_path: str, output_path: str) -> dict[str, int | str]:
    return prepare_real_matches_file(input_path, output_path, input_format="football-data")
