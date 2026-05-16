from __future__ import annotations

from pathlib import Path

import pandas as pd

from .team_names import normalize_team_name

_FIXTURE_OUTPUT_COLUMNS = [
    "date",
    "season",
    "league",
    "home_team",
    "away_team",
    "venue",
    "referee",
    "odds_home",
    "odds_draw",
    "odds_away",
    "formation_home_xg90",
    "formation_away_xg90",
    "fatigue_home",
    "fatigue_away",
]

_FOOTBALL_DATA_COLUMN_MAP = {
    "Date": "date",
    "HomeTeam": "home_team",
    "AwayTeam": "away_team",
    "B365H": "odds_home",
    "B365D": "odds_draw",
    "B365A": "odds_away",
}

_FLOAT_DEFAULTS: dict[str, float] = {
    "formation_home_xg90": 0.0,
    "formation_away_xg90": 0.0,
    "fatigue_home": 0.0,
    "fatigue_away": 0.0,
}

_STRING_DEFAULTS: dict[str, str] = {
    "venue": "",
    "referee": "",
}


def _detect_format(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    if "HomeTeam" in cols and "AwayTeam" in cols:
        return "football-data"
    if "home_team" in cols and "away_team" in cols:
        return "native"
    raise ValueError(
        "Cannot detect fixture format. Expected either native columns "
        "(home_team, away_team) or football-data columns (HomeTeam, AwayTeam)."
    )


def _validate_required(df: pd.DataFrame) -> None:
    for col in ("date", "home_team", "away_team"):
        if col not in df.columns:
            raise ValueError(
                f"Required column '{col}' is missing from the fixture file. "
                "Each fixture must have a date, home_team, and away_team."
            )
        blank = df[col].isna() | (df[col].astype(str).str.strip() == "")
        if blank.any():
            bad = df.index[blank].tolist()
            raise ValueError(
                f"Column '{col}' has empty values on rows: {bad}. "
                "Every fixture must have a valid date, home team, and away team."
            )


def prepare_fixtures(
    df: pd.DataFrame,
    input_format: str = "auto",
    default_season: str | None = None,
    default_league: str | None = None,
) -> pd.DataFrame:
    """Prepare a raw fixtures DataFrame into a prediction-ready fixtures CSV.

    Args:
        df: Raw input DataFrame.
        input_format: "auto", "native", or "football-data".
        default_season: Fallback season string if the column is missing/empty.
        default_league: Fallback league string if the column is missing/empty.

    Returns:
        Cleaned DataFrame with exactly the columns needed by predict-fixtures.

    Raises:
        ValueError: on unsupported format, empty input, or missing required fields.
    """
    if df.empty:
        raise ValueError(
            "The input fixture file is empty. "
            "Add at least one fixture row before running prepare-fixtures."
        )

    fmt = input_format
    if fmt == "auto":
        fmt = _detect_format(df)
    if fmt not in ("native", "football-data"):
        raise ValueError(
            f"Unsupported fixture format '{fmt}'. "
            "Use 'auto', 'native', or 'football-data'."
        )

    out = df.copy()

    if fmt == "football-data":
        for src, dst in _FOOTBALL_DATA_COLUMN_MAP.items():
            if src in out.columns and dst not in out.columns:
                out = out.rename(columns={src: dst})

    _validate_required(out)

    # Normalize team names
    out["home_team"] = out["home_team"].apply(normalize_team_name)
    out["away_team"] = out["away_team"].apply(normalize_team_name)

    # Parse dates
    # Try ISO-first (YYYY-MM-DD), then fall back to DD/MM/YYYY for football-data dates.
    raw_dates = out["date"].astype(str)
    parsed = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    still_bad = parsed.isna()
    if still_bad.any():
        parsed[still_bad] = pd.to_datetime(
            raw_dates[still_bad], format="%d/%m/%Y", errors="coerce"
        )
    out["date"] = parsed
    bad_dates = out["date"].isna()
    if bad_dates.any():
        raise ValueError(
            f"Could not parse dates on rows: {out.index[bad_dates].tolist()}. "
            "Use formats like '2024-05-01' or '01/05/2024'."
        )

    # Season / league defaults
    _season_default = str(default_season) if default_season is not None else "Unknown"
    _league_default = str(default_league) if default_league is not None else "Unknown"

    if "season" not in out.columns:
        out["season"] = _season_default
    else:
        out["season"] = out["season"].fillna(_season_default).astype(str).str.strip()
        out.loc[out["season"] == "", "season"] = _season_default

    if "league" not in out.columns:
        out["league"] = _league_default
    else:
        out["league"] = out["league"].fillna(_league_default).astype(str).str.strip()
        out.loc[out["league"] == "", "league"] = _league_default

    # String optional columns
    for col, default in _STRING_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
        else:
            out[col] = out[col].fillna(default).astype(str).str.strip()

    # Float optional columns
    for col, default in _FLOAT_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(default)

    # Odds — leave as NaN if absent, convert to numeric otherwise
    for col in ("odds_home", "odds_draw", "odds_away"):
        if col not in out.columns:
            out[col] = float("nan")
        else:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.sort_values("date").reset_index(drop=True)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    return out[_FIXTURE_OUTPUT_COLUMNS]


def prepare_fixtures_file(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
    default_season: str | None = None,
    default_league: str | None = None,
) -> dict[str, object]:
    """Read, prepare, and save a fixtures CSV file.

    Returns a summary dict with input/output paths and row counts.
    """
    df = pd.read_csv(input_path)
    out = prepare_fixtures(
        df,
        input_format=input_format,
        default_season=default_season,
        default_league=default_league,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows_in": len(df),
        "rows_out": len(out),
    }
