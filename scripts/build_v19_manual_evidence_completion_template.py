# -*- coding: utf-8 -*-
"""Build a preview-only manual v1.9 evidence completion CSV template."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

TEMPLATE_STATUS = "V19_MANUAL_EVIDENCE_COMPLETION_TEMPLATE_READY"
DEFAULT_OUTPUT = "data/manual/v19_manual_evidence_completion_template.csv"

COMPLETION_COLUMNS = [
    "home_team", "away_team", "competition", "season", "match_date", "cross_provider_match_key",
    "home_open_odds", "draw_open_odds", "away_open_odds", "home_current_odds", "draw_current_odds",
    "away_current_odds", "home_closing_odds", "draw_closing_odds", "away_closing_odds",
    "over_line", "over_open_odds", "under_open_odds", "over_current_odds", "under_current_odds",
    "dnb_home_odds", "dnb_away_odds", "handicap_line", "handicap_home_odds", "handicap_away_odds",
    "home_possession", "away_possession", "home_shots", "away_shots", "home_shots_on_target",
    "away_shots_on_target", "home_tackles", "away_tackles", "home_interceptions", "away_interceptions",
    "home_blocks", "away_blocks", "home_clearances", "away_clearances", "home_progressive_passes",
    "away_progressive_passes", "home_progressive_carries", "away_progressive_carries",
    "home_pass_completion", "away_pass_completion",
    "home_lineup_status", "away_lineup_status", "home_goalkeeper_status", "away_goalkeeper_status",
    "home_defensive_line_status", "away_defensive_line_status", "home_missing_players",
    "away_missing_players", "home_suspended_players", "away_suspended_players", "home_doubtful_players",
    "away_doubtful_players", "home_key_absence_count", "away_key_absence_count",
    "home_big_chances_for", "away_big_chances_for", "home_big_chances_against",
    "away_big_chances_against", "home_recent_matches", "away_recent_matches",
    "home_recent_goals_for", "away_recent_goals_for", "home_recent_goals_against",
    "away_recent_goals_against", "home_recent_xg_for", "away_recent_xg_for",
    "home_recent_xg_against", "away_recent_xg_against", "home_recent_conversion_note",
    "away_recent_conversion_note",
    "tactical_matchup_score", "home_tactical_profile", "away_tactical_profile",
    "formation_matchup_note", "pressing_matchup_note", "transition_matchup_note",
    "defensive_line_risk_note", "home_rest_days", "away_rest_days", "home_travel_fatigue_note",
    "away_travel_fatigue_note", "do_so_fatigue_modifier", "xg_zone_correction_flag",
    "xg_zone_correction_note",
    "h2h_summary", "analyst_manual_note", "evidence_completion_review_required",
]


def build_v19_manual_evidence_completion_template(
    output: str | Path = DEFAULT_OUTPUT,
    *,
    base_dir: str | Path = ROOT,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    out = Path(output)
    output_path = (base / out).resolve() if not out.is_absolute() else out.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row = {column: "" for column in COMPLETION_COLUMNS}
    row.update({
        "home_team": "Lazio",
        "away_team": "Atalanta",
        "competition": "Serie A",
        "season": "2025/26",
        "match_date": "2026-02-14",
        "cross_provider_match_key": "manual-serie-a-2025-26-lazio-atalanta-2026-02-14",
        "evidence_completion_review_required": "true",
    })
    pd.DataFrame([row], columns=COMPLETION_COLUMNS).to_csv(output_path, index=False)
    return {
        "v19_manual_evidence_completion_template_status": TEMPLATE_STATUS,
        "columns_written": len(COMPLETION_COLUMNS),
        "rows_written": 1,
        "output_path": str(output_path),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "recommendation": TEMPLATE_STATUS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = build_v19_manual_evidence_completion_template(output=args.output, base_dir=args.base_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
