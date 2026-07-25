"""Input parsing and validation for unified prematch analysis."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


_SEASON_RE = re.compile(r"^\d{4}/\d{2}$")


@dataclass(frozen=True)
class MatchInput:
    competition: str
    season: str
    home_team: str
    away_team: str
    match_date: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_team_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold().replace("football club", "").replace(" fc", ""))


def parse_match_input(value: dict[str, Any]) -> MatchInput:
    required = ("competition", "season", "home_team", "away_team", "match_date")
    missing = [key for key in required if not str(value.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Missing required input fields: {', '.join(missing)}")
    season = str(value["season"]).strip()
    if not _SEASON_RE.fullmatch(season):
        raise ValueError("season must use YYYY/YY format")
    match_date = str(value["match_date"]).strip()
    try:
        date.fromisoformat(match_date)
    except ValueError as exc:
        raise ValueError("match_date must use YYYY-MM-DD format") from exc
    home = str(value["home_team"]).strip()
    away = str(value["away_team"]).strip()
    if normalize_team_key(home) == normalize_team_key(away):
        raise ValueError("home_team and away_team must differ")
    return MatchInput(
        competition=str(value["competition"]).strip(),
        season=season,
        home_team=home,
        away_team=away,
        match_date=match_date,
    )


def load_input_json(path: str | Path) -> MatchInput:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("match"), dict):
        payload = payload["match"]
    if not isinstance(payload, dict):
        raise ValueError("input JSON must contain one match object")
    return parse_match_input(payload)


def load_batch_file(path: str | Path) -> list[MatchInput | tuple[int, Exception]]:
    source = Path(path)
    raw_rows: list[dict[str, Any]]
    if source.suffix.casefold() == ".jsonl":
        raw_rows = [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    elif source.suffix.casefold() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_rows = list(csv.DictReader(handle))
    else:
        raise ValueError("batch input must be CSV or JSONL")
    parsed: list[MatchInput | tuple[int, Exception]] = []
    for index, row in enumerate(raw_rows, start=1):
        try:
            parsed.append(parse_match_input(row))
        except Exception as exc:  # batch rows must fail independently
            parsed.append((index, exc))
    return parsed
