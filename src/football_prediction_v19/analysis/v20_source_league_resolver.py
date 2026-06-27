# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class SourceLeagueMapping:
    competition_input: str
    canonical_competition: str
    season_input: str
    football_data_code: str = ""
    football_data_season_code: str = ""
    understat_league_code: str = ""
    understat_season: str = ""
    odds_api_sport_key: str = ""
    api_football_league_id: str = ""
    warnings: tuple[str, ...] = ()
    status: str = "UNSUPPORTED"

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        return data


_LEAGUES = {
    "premier league": ("Premier League", "E0", "EPL", "soccer_epl", ""),
    "english premier league": ("Premier League", "E0", "EPL", "soccer_epl", ""),
    "bundesliga": ("Bundesliga", "D1", "Bundesliga", "soccer_germany_bundesliga", ""),
    "serie a": ("Serie A", "I1", "Serie_A", "soccer_italy_serie_a", ""),
    "la liga": ("La Liga", "SP1", "La_liga", "soccer_spain_la_liga", ""),
    "laliga": ("La Liga", "SP1", "La_liga", "soccer_spain_la_liga", ""),
    "ligue 1": ("Ligue 1", "F1", "Ligue_1", "soccer_france_ligue_one", ""),
    "eredivisie": ("Eredivisie", "N1", "", "", ""),
    "2. bundesliga": ("2. Bundesliga", "D2", "", "", ""),
    "demo league": ("Demo League", "DEMO", "Demo_League", "soccer_demo", ""),
}


def resolve_source_league(competition: str, season: str, output_dir: str | Path | None = None) -> SourceLeagueMapping:
    key = _norm(competition)
    season_code = football_data_season_code(season)
    if key not in _LEAGUES:
        mapping = SourceLeagueMapping(
            competition_input=competition,
            canonical_competition=competition.strip(),
            season_input=season,
            warnings=("unsupported competition for configured live sources",),
            status="UNSUPPORTED",
        )
    else:
        canonical, fd_code, understat_code, odds_key, api_id = _LEAGUES[key]
        warnings = []
        if not understat_code:
            warnings.append("understat league code unavailable")
        if not odds_key:
            warnings.append("odds api sport key unavailable")
        status = "RESOLVED" if fd_code and understat_code and odds_key else "PARTIAL"
        mapping = SourceLeagueMapping(
            competition_input=competition,
            canonical_competition=canonical,
            season_input=season,
            football_data_code=fd_code,
            football_data_season_code=season_code,
            understat_league_code=understat_code,
            understat_season=season[:4] if season[:4].isdigit() else season,
            odds_api_sport_key=odds_key,
            api_football_league_id=api_id,
            warnings=tuple(warnings),
            status=status,
        )
    if output_dir is not None:
        write_source_league_mapping(mapping, output_dir)
    return mapping


def football_data_season_code(season: str) -> str:
    match = re.search(r"(\d{4})", str(season))
    if not match:
        return str(season)
    start = int(match.group(1))
    return f"{str(start)[-2:]}{str(start + 1)[-2:]}"


def write_source_league_mapping(mapping: SourceLeagueMapping, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "source_league_mapping.json"
    md_path = out / "source_league_mapping.md"
    json_path.write_text(json.dumps(mapping.to_dict(), indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# v2.0 Source League Mapping",
                "",
                f"- status: {mapping.status}",
                f"- canonical_competition: {mapping.canonical_competition}",
                f"- football_data_code: {mapping.football_data_code or 'MISSING'}",
                f"- understat_league_code: {mapping.understat_league_code or 'MISSING'}",
                f"- odds_api_sport_key: {mapping.odds_api_sport_key or 'MISSING'}",
                f"- warnings: {', '.join(mapping.warnings) if mapping.warnings else 'none'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"source_league_mapping_json_path": str(json_path.resolve()), "source_league_mapping_md_path": str(md_path.resolve())}


def _norm(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())
