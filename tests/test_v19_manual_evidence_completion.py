# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.build_real_match_input_pack_preview import build_real_match_input_pack_preview
from scripts.build_v19_manual_evidence_completion_template import (
    COMPLETION_COLUMNS,
    TEMPLATE_STATUS,
    build_v19_manual_evidence_completion_template,
)
from scripts.run_match_analysis_preview import run_match_analysis_preview


ROOT = Path(__file__).resolve().parents[1]
BASE_INTAKE = ROOT / "data" / "manual" / "real_match_intake.csv"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def test_v19_manual_evidence_completion_template_writes_expected_columns(tmp_path: Path) -> None:
    output = tmp_path / "v19_manual_evidence_completion_template.csv"
    result = build_v19_manual_evidence_completion_template(output=output, base_dir=ROOT)
    frame = pd.read_csv(output, keep_default_na=False)

    assert result["v19_manual_evidence_completion_template_status"] == TEMPLATE_STATUS
    assert list(frame.columns) == COMPLETION_COLUMNS
    for column in [
        "home_current_odds",
        "home_possession",
        "home_lineup_status",
        "home_recent_xg_for",
        "tactical_matchup_score",
        "h2h_summary",
    ]:
        assert column in frame.columns


def test_manual_evidence_completion_fills_blanks_without_empty_overwrite(tmp_path: Path) -> None:
    intake = pd.read_csv(BASE_INTAKE, keep_default_na=False)
    intake.loc[0, "home_possession"] = ""
    intake.loc[0, "home_current_odds"] = "9.99"
    intake_path = tmp_path / "real_match_intake.csv"
    intake.to_csv(intake_path, index=False)

    completion = pd.read_csv(COMPLETION_FIXTURE, keep_default_na=False)
    completion["home_current_odds"] = completion["home_current_odds"].astype(object)
    completion.loc[0, "home_current_odds"] = ""
    completion_path = tmp_path / "completion.csv"
    completion.to_csv(completion_path, index=False)

    result = build_real_match_input_pack_preview(
        real_match_intake_path=intake_path,
        manual_evidence_completion_path=completion_path,
        base_dir=tmp_path,
    )

    assert result["real_match_input_pack_status"] == "REAL_MATCH_INPUT_PACK_PREVIEW_READY"
    assert result["manual_evidence_completion_status"] == "MANUAL_EVIDENCE_COMPLETION_APPLIED"
    assert int(result["fields_completed_count"]) > 0
    assert "Match Stats/Control" in str(result["completed_evidence_groups"])
    completed = pd.read_csv(
        tmp_path / "outputs" / "analysis_preview" / "manual_evidence_completion" / "real_match_intake_completed.csv",
        keep_default_na=False,
    )
    assert str(completed.loc[0, "home_possession"]) == "50"
    assert str(completed.loc[0, "home_current_odds"]) == "9.99"


def test_runner_accepts_completion_and_report_surfaces_counts(tmp_path: Path) -> None:
    intake_path = tmp_path / "real_match_intake.csv"
    pd.read_csv(BASE_INTAKE, keep_default_na=False).to_csv(intake_path, index=False)

    result = run_match_analysis_preview(
        real_match_intake=intake_path,
        manual_evidence_completion=COMPLETION_FIXTURE,
        base_dir=tmp_path,
    )

    assert result["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert result["manual_evidence_completion_status"] == "MANUAL_EVIDENCE_COMPLETION_APPLIED"
    assert int(result["fields_completed_count"]) > 0
    assert result["human_24_block_report_status"] == "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
    assert int(result["sections_rendered"]) == 24
    assert int(result["required_sections_rendered"]) == 24
    assert not any(
        bool(result[key])
        for key in [
            "network_calls_enabled",
            "prediction_logic_enabled",
            "betting_logic_enabled",
            "staking_logic_enabled",
            "roi_logic_enabled",
        ]
    )

    report = (
        tmp_path
        / "outputs"
        / "analysis_preview"
        / "human_24_block_report"
        / "human_24_block_match_report_preview.md"
    ).read_text(encoding="utf-8")
    assert "Manual evidence completion status: MANUAL_EVIDENCE_COMPLETION_APPLIED" in report
    assert "fields_completed_count:" in report
    assert "Market/Odds" in report
    assert "missing shots on target, odds, recent form and lineups block score-family generation" not in report
    assert "Manual completion adds possession, shot volume and shots-on-target context" in report
    assert "score-family diagnostics are readable" in report
    assert "No production recommendation" in report
