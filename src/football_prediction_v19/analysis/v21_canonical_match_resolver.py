# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league


@dataclass(frozen=True)
class CanonicalMatchResolution:
    status: str
    canonical_match_id: str = ""
    selected_match: dict[str, object] | None = None
    candidate_matches: tuple[dict[str, object], ...] = ()
    related_suggestions: tuple[dict[str, object], ...] = ()
    team_alias_suggestions: tuple[dict[str, object], ...] = ()
    recommended_run_commands: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["selected_match"] = self.selected_match or {}
        data["candidate_matches"] = list(self.candidate_matches)
        data["related_suggestions"] = list(self.related_suggestions)
        data["team_alias_suggestions"] = list(self.team_alias_suggestions)
        data["recommended_run_commands"] = list(self.recommended_run_commands)
        return data


def resolve_canonical_match(home_team: str, away_team: str, competition: str, season: str, match_date: str = "", *, catalog_path: str | Path, output_dir: str | Path | None = None) -> CanonicalMatchResolution:
    catalog = pd.read_csv(catalog_path, keep_default_na=False)
    home_norm = normalize_team_or_league(home_team)
    away_norm = normalize_team_or_league(away_team)
    date_norm = normalize_match_date(match_date) if match_date else ""
    pair_mask = catalog["home_team"].map(normalize_team_or_league).eq(home_norm) & catalog["away_team"].map(normalize_team_or_league).eq(away_norm)
    exact = catalog[pair_mask & catalog["match_date"].astype(str).map(normalize_match_date).eq(date_norm)] if date_norm else catalog.iloc[0:0]
    candidates = catalog[pair_mask]
    related = catalog[
        ((catalog["home_team"].map(normalize_team_or_league).eq(home_norm)) | (catalog["away_team"].map(normalize_team_or_league).eq(home_norm)) | (catalog["home_team"].map(normalize_team_or_league).eq(away_norm)) | (catalog["away_team"].map(normalize_team_or_league).eq(away_norm)))
        & ~pair_mask
    ]
    if len(exact) == 1:
        selected = exact.iloc[0].to_dict()
        status, reason = "RESOLVED", "exact pair and date found in season fixture catalog"
    elif len(candidates) == 1 and date_norm:
        selected = candidates.iloc[0].to_dict()
        status, reason = "RESOLVED_DATE_TOLERANCE", "pair found with a different date"
    elif len(candidates) > 1:
        selected = {}
        status, reason = "AMBIGUOUS", "multiple pair candidates found"
    elif len(candidates) == 1:
        selected = candidates.iloc[0].to_dict()
        status, reason = "PARTIAL", "pair found without exact date confirmation"
    else:
        selected = {}
        status, reason = "NOT_FOUND", "pair not found in season fixture catalog"
    candidate_records = candidates.to_dict(orient="records")
    related_records = related.head(25).to_dict(orient="records")
    commands = tuple(_command(row, competition, season) for row in (candidate_records or related_records[:5]))
    result = CanonicalMatchResolution(
        status=status,
        canonical_match_id=str(selected.get("canonical_match_id", "")) if selected else "",
        selected_match=selected,
        candidate_matches=tuple(candidate_records),
        related_suggestions=tuple(related_records),
        team_alias_suggestions=tuple(_alias_suggestions(home_team, away_team, catalog)),
        recommended_run_commands=commands,
        reason=reason,
    )
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "canonical_match_resolution.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        (out / "canonical_match_resolution.md").write_text(f"# v2.1 Canonical Match Resolution\n\n- status: {status}\n- reason: {reason}\n- candidates: {len(candidate_records)}\n- related_suggestions: {len(related_records)}\n", encoding="utf-8")
    return result


def _command(row: dict[str, object], competition: str, season: str) -> str:
    return f'python scripts/run_v21_predict_winner.py --home-team "{row.get("home_team", "")}" --away-team "{row.get("away_team", "")}" --competition "{competition}" --season "{season}" --match-date "{row.get("match_date", "")}"'


def _alias_suggestions(home_team: str, away_team: str, catalog: pd.DataFrame) -> list[dict[str, str]]:
    rows = []
    for wanted in [home_team, away_team]:
        wanted_norm = normalize_team_or_league(wanted)
        for col in ["home_team", "away_team"]:
            for team in sorted(set(catalog[col].astype(str))):
                if wanted != team and wanted_norm == normalize_team_or_league(team):
                    rows.append({"input_team": wanted, "catalog_team": team, "normalized": wanted_norm})
    return rows
