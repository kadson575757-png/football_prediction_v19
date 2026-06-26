# -*- coding: utf-8 -*-
"""Next-data checklist for the v1.9 match workbench preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

V19_NEXT_DATA_TO_FILL_PREVIEW_READY = "V19_NEXT_DATA_TO_FILL_PREVIEW_READY"


@dataclass(frozen=True)
class V19NextDataToFillConfig:
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19NextDataToFillResult:
    next_data_to_fill_status: str
    next_data_to_fill_path: str
    critical_groups_count: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19NextDataToFillRenderer:
    def __init__(self, config: V19NextDataToFillConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19NextDataToFillResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "next_data_to_fill.md"
        groups = _groups()
        path.write_text(_render(groups), encoding="utf-8")
        return V19NextDataToFillResult(V19_NEXT_DATA_TO_FILL_PREVIEW_READY, str(path.resolve()), 4, False, False, False, False, V19_NEXT_DATA_TO_FILL_PREVIEW_READY)


def _groups() -> list[dict[str, str]]:
    return [
        {
            "field group": "Recent Form",
            "field names": "home_recent_matches, away_recent_matches, home_recent_xg_for, away_recent_xg_for, home_recent_xg_against, away_recent_xg_against, home_recent_goals_for, away_recent_goals_for, home_recent_goals_against, away_recent_goals_against",
            "why required": "confirms whether structural xG edge is current",
            "affected gates": "Recent Form",
            "affected market families": "1X2, Goals, Score Family",
            "example format": "numeric values or short recent-match note",
        },
        {
            "field group": "Big Chances",
            "field names": "home_big_chances_for, away_big_chances_for, home_big_chances_against, away_big_chances_against",
            "why required": "validates chance quality behind xG",
            "affected gates": "Big Chances",
            "affected market families": "Goals, BTTS, Score Family",
            "example format": "integer counts",
        },
        {
            "field group": "Availability",
            "field names": "home_goalkeeper_status, away_goalkeeper_status, home_missing_players, away_missing_players, home_suspended_players, away_suspended_players, home_doubtful_players, away_doubtful_players, home_key_absence_count, away_key_absence_count",
            "why required": "turns lineup context from partial to decision-ready",
            "affected gates": "Full Availability Details",
            "affected market families": "1X2, DNB, BTTS",
            "example format": "AVAILABLE or player-name lists",
        },
        {
            "field group": "Market",
            "field names": "home_open_odds, draw_open_odds, away_open_odds, home_closing_odds, draw_closing_odds, away_closing_odds, dnb_home_odds, dnb_away_odds, over_line, over_current_odds, under_current_odds",
            "why required": "checks whether market movement confirms or contradicts the analyst lean",
            "affected gates": "Opening/Closing Market, DNB/OU Market",
            "affected market families": "1X2, Double Chance, DNB, Over/Under",
            "example format": "decimal odds",
        },
    ]


def _render(groups: list[dict[str, str]]) -> str:
    lines = [
        "# v1.9 Next Data To Fill",
        "",
        "## 1. Critical: Required for Bet Candidate Preview",
        "",
        "| field group | field names | why required | affected gates | affected market families | example format |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in groups:
        lines.append("| " + " | ".join(row[column] for column in ["field group", "field names", "why required", "affected gates", "affected market families", "example format"]) + " |")
    lines.extend([
        "",
        "## 2. Important: Needed for Confidence Upgrade",
        "- defensive actions",
        "- tactical notes",
        "- fatigue/rest days",
        "- home/away split",
        "",
        "## 3. Nice-to-have",
        "- referee",
        "- weather",
        "- deeper H2H",
        "- role notes",
        "",
        "## 4. Minimum Input Set To Rerun",
        "- recent xG for/against",
        "- big chances for/against",
        "- goalkeeper status",
        "- missing/suspended/doubtful players",
        "- opening/current/closing odds",
        "",
        "## 5. Copy/Paste CSV Fill Guide",
        "field_name,example_format,notes",
        "home_recent_xg_for,decimal,recent five-match xG for",
        "away_big_chances_for,integer,big chances for",
        "home_goalkeeper_status,text,AVAILABLE or status note",
        "away_closing_odds,decimal,closing decimal odds",
        "",
        "Preview only. Do not invent values; fill only verified evidence.",
        "",
    ])
    return "\n".join(lines)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
