# -*- coding: utf-8 -*-
"""Preview-only filled real match intake sample pack."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.real_match_intake_schema_preview import INTAKE_COLUMNS, _sample_row

FILLED_REAL_MATCH_INTAKE_PACK_PREVIEW_READY = "FILLED_REAL_MATCH_INTAKE_PACK_PREVIEW_READY"
FILLED_REAL_MATCH_INTAKE_PACK_BLOCKED_SCHEMA_MISMATCH = "FILLED_REAL_MATCH_INTAKE_PACK_BLOCKED_SCHEMA_MISMATCH"
FILLED_REAL_MATCH_INTAKE_PACK_NO_BETTING_OUTPUT_BY_DESIGN = "FILLED_REAL_MATCH_INTAKE_PACK_NO_BETTING_OUTPUT_BY_DESIGN"


@dataclass(frozen=True)
class FilledRealMatchIntakePackConfig:
    output_dir: str | Path = "outputs/analysis_preview/filled_real_match_intake_pack"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class FilledRealMatchIntakePackResult:
    filled_real_match_intake_pack_status: str
    rows_written: int
    columns_written: int
    filled_intake_path: str
    minimal_intake_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class FilledRealMatchIntakePackBuilder:
    def __init__(self, config: FilledRealMatchIntakePackConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> FilledRealMatchIntakePackResult:
        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        full = _sample_row()
        minimal = _minimal_row()
        if set(INTAKE_COLUMNS) - set(full) or set(INTAKE_COLUMNS) - set(minimal):
            return self._blocked(FILLED_REAL_MATCH_INTAKE_PACK_BLOCKED_SCHEMA_MISMATCH)
        full_path = out / "filled_real_match_intake.csv"
        minimal_path = out / "filled_real_match_intake_minimal.csv"
        summary_path = out / "filled_real_match_intake_summary.md"
        manifest_path = out / "filled_real_match_intake_manifest.csv"
        pd.DataFrame([full], columns=INTAKE_COLUMNS).to_csv(full_path, index=False)
        pd.DataFrame([minimal], columns=INTAKE_COLUMNS).to_csv(minimal_path, index=False)
        result = FilledRealMatchIntakePackResult(
            FILLED_REAL_MATCH_INTAKE_PACK_PREVIEW_READY, 2, len(INTAKE_COLUMNS),
            str(full_path.resolve()), str(minimal_path.resolve()), str(summary_path.resolve()),
            str(manifest_path.resolve()), FILLED_REAL_MATCH_INTAKE_PACK_PREVIEW_READY,
            False, False, False, False, False,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Filled Real Match Intake Pack Preview", "",
            f"- filled_real_match_intake_pack_status: {result.filled_real_match_intake_pack_status}",
            f"- rows_written: {result.rows_written}",
            "- includes full and minimal_missing_optional local preview CSVs",
            "- diagnostic preview only; no final betting tips, staking, units, ROI, or SUPER_A output", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> FilledRealMatchIntakePackResult:
        return FilledRealMatchIntakePackResult(status, 0, 0, "", "", "", "", status, False, False, False, False, False)


def _minimal_row() -> dict[str, object]:
    row = {column: "" for column in INTAKE_COLUMNS}
    row.update({
        "match_date": "2024-08-25",
        "competition": "Bundesliga",
        "season": "2024",
        "home_team": "Minimal Home",
        "away_team": "Minimal Away",
        "cross_provider_match_key": "manual-bundesliga-2024-minimal-home-minimal-away-2024-08-25",
        "understat_provider_match_id": "manual-understat-minimal-001",
        "fbref_provider_match_id": "manual-fbref-minimal-001",
        "home_open_odds": 2.20,
        "draw_open_odds": 3.30,
        "away_open_odds": 3.10,
        "home_current_odds": 2.15,
        "draw_current_odds": 3.35,
        "away_current_odds": 3.25,
        "market_snapshot_timestamp": "2024-08-25T10:00:00Z",
        "manual_review_required": "true",
        "network_calls_enabled": "false",
        "prediction_logic_enabled": "false",
        "betting_logic_enabled": "false",
        "staking_logic_enabled": "false",
        "roi_logic_enabled": "false",
        "evidence_quality_note": "minimal_missing_optional preview row; blanks are intentional",
    })
    return row


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()
