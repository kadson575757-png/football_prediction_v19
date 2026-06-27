# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class LeagueSupportEntry:
    canonical_name: str
    football_data_code: str = ""
    football_data_supported: bool = False
    understat_league_code: str = ""
    understat_supported: bool = False
    odds_api_sport_key: str = ""
    api_football_league_id: str = ""
    season_format: str = "YYYY/YY"
    team_alias_source: str = "built_in"
    prediction_tier: str = "UNSUPPORTED"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_league_support_matrix(path: str | Path = "config/v21_league_support.yaml") -> list[LeagueSupportEntry]:
    text = Path(path).read_text(encoding="utf-8")
    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "leagues:":
            continue
        if line.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            line = line[2:].strip()
        if ":" in line and current is not None:
            key, value = line.split(":", 1)
            current[key.strip()] = _parse_value(value.strip())
    if current:
        rows.append(current)
    return [LeagueSupportEntry(**row) for row in rows]


def resolve_league_support(competition: str, path: str | Path = "config/v21_league_support.yaml") -> LeagueSupportEntry:
    norm = normalize_team_or_league(competition)
    for entry in load_league_support_matrix(path):
        if normalize_team_or_league(entry.canonical_name) == norm:
            return entry
    return LeagueSupportEntry(canonical_name=str(competition).strip(), prediction_tier="UNSUPPORTED")


def write_league_support_outputs(output_dir: str | Path, path: str | Path = "config/v21_league_support.yaml") -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries = [entry.to_dict() for entry in load_league_support_matrix(path)]
    json_path = out / "league_support_matrix.json"
    csv_path = out / "league_support_matrix.csv"
    md_path = out / "league_support_matrix.md"
    json_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    pd.DataFrame(entries).to_csv(csv_path, index=False)
    lines = ["# v2.1 League Support Matrix", "", "| League | Tier | football-data | Understat |", "|---|---:|---:|---:|"]
    for row in entries:
        lines.append(f"| {row['canonical_name']} | {row['prediction_tier']} | {str(row['football_data_supported']).lower()} | {str(row['understat_supported']).lower()} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"league_support_matrix_json_path": str(json_path.resolve()), "league_support_matrix_csv_path": str(csv_path.resolve()), "league_support_matrix_md_path": str(md_path.resolve())}


def normalize_team_or_league(value: object) -> str:
    aliases = {
        "leeds": "leeds united",
        "leeds utd": "leeds united",
        "man utd": "manchester united",
        "man united": "manchester united",
        "spurs": "tottenham",
        "psg": "paris saint germain",
        "super lig": "super lig",
        "süper lig": "super lig",
    }
    text = " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())
    return aliases.get(text, text)


def _parse_value(value: str) -> object:
    clean = value.strip().strip('"').strip("'")
    if clean.lower() == "true":
        return True
    if clean.lower() == "false":
        return False
    return clean
