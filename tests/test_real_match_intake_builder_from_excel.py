# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.real_match_intake_schema_preview import INTAKE_COLUMNS
from scripts.build_real_match_intake_from_excel import build_real_match_intake_from_excel
from scripts.run_match_analysis_preview import run_match_analysis_preview


def _write_evidence(input_dir: Path, *, partial: bool = False) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    stats = pd.DataFrame([
        {
            "team": "Lazio",
            "xg_for": 48.18,
            "xg_against": 49.45,
            "recent_xg_for": 6.4,
            "recent_xg_against": 5.1,
            "formation": "4-3-3",
            "tactical_profile": "wide 4-3-3 with left-side attacks",
            "set_piece_xg_for": 6.09,
            "set_piece_xg_against": 2.38,
            "set_piece_xg_ratio": 2.56,
            "rest_days": 6,
            "travel_fatigue_note": "home match; no travel concern",
            "missing_players": "Romagnoli suspended",
            "key_absences": "Romagnoli",
            "goalkeeper_status": "Provedel available",
            "venue": "Stadio Olimpico",
            "country": "Italy",
            "timezone": "Europe/Rome",
            "tactical_matchup_score": 6.5,
            "formation_matchup_note": "Lazio width vs Atalanta back three",
            "pressing_matchup_note": "Atalanta pressure risk",
            "transition_matchup_note": "Atalanta dangerous in transition",
            "defensive_line_risk_note": "Lazio high line must protect depth",
        },
        {
            "team": "Atalanta",
            "xg_for": 70.82,
            "xg_against": 54.06,
            "recent_xg_for": 8.2,
            "recent_xg_against": 4.8,
            "formation": "3-4-2-1",
            "tactical_profile": "central progression and transition side",
            "set_piece_xg_for": 3.19,
            "set_piece_xg_against": 4.76,
            "set_piece_xg_ratio": 0.67,
            "rest_days": 5,
            "travel_fatigue_note": "away travel to Rome",
            "missing_players": "Scamacca questionable",
            "key_absences": "Scamacca",
            "goalkeeper_status": "Carnesecchi available",
        },
    ])
    if partial:
        stats = stats.drop(columns=["recent_xg_for", "recent_xg_against", "set_piece_xg_ratio"])
    players = pd.DataFrame([
        {"team": "Lazio", "player": "Pedro", "goals": 5, "assists": 1, "xg": 12.2, "xa": 2.1, "big_chances": 3},
        {"team": "Lazio", "player": "Mattia Zaccagni", "goals": 3, "assists": 4, "xg": 9.3, "xa": 5.2, "big_chances": 1},
        {"team": "Atalanta", "player": "Nikola Krstovic", "goals": 10, "assists": 2, "xg": 18.4, "xa": 3.2, "big_chances": 4},
        {"team": "Atalanta", "player": "Charles De Ketelaere", "goals": 4, "assists": 6, "xg": 11.1, "xa": 10.6, "big_chances": 2},
    ])
    stats.to_excel(input_dir / "team-statistics-serie-a.xlsx", index=False)
    players.to_excel(input_dir / "team-players-serie-a.xlsx", index=False)


def test_excel_evidence_files_are_detected_and_mapped(tmp_path: Path) -> None:
    evidence = tmp_path / "data" / "manual" / "evidence"
    _write_evidence(evidence)
    output = tmp_path / "data" / "manual" / "real_match_intake.csv"
    result = build_real_match_intake_from_excel(
        input_dir=evidence,
        output=output,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        base_dir=tmp_path,
    )
    assert result["real_match_intake_excel_builder_status"] == "REAL_MATCH_INTAKE_EXCEL_BUILDER_READY"
    assert int(result["input_files_detected"]) == 2
    frame = pd.read_csv(output, keep_default_na=False)
    row = frame.iloc[0]
    assert set(INTAKE_COLUMNS).issubset(set(frame.columns))
    assert row["home_team"] == "Lazio"
    assert row["away_team"] == "Atalanta"
    assert row["competition"] == "Serie A"
    assert row["cross_provider_match_key"] == "manual-serie-a-2025-26-lazio-atalanta-2026-02-14"
    assert float(row["home_team_xg_for"]) == 48.18
    assert float(row["away_team_xg_for"]) == 70.82
    assert "Pedro" in row["home_main_scorer"]
    assert "Charles De Ketelaere" in row["away_main_creator"]
    assert row["home_formation"] == "4-3-3"
    assert row["away_formation"] == "3-4-2-1"
    assert row["network_calls_enabled"] is False or str(row["network_calls_enabled"]).lower() == "false"
    assert Path(str(result["summary_csv_path"])).exists()
    assert Path(str(result["summary_md_path"])).exists()


def test_missing_optional_excel_columns_do_not_crash_and_require_review(tmp_path: Path) -> None:
    evidence = tmp_path / "data" / "manual" / "evidence"
    _write_evidence(evidence, partial=True)
    output = tmp_path / "data" / "manual" / "real_match_intake.csv"
    result = build_real_match_intake_from_excel(
        input_dir=evidence,
        output=output,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        base_dir=tmp_path,
    )
    row = pd.read_csv(output, keep_default_na=False).iloc[0]
    assert result["real_match_intake_excel_builder_status"] == "REAL_MATCH_INTAKE_EXCEL_BUILDER_READY"
    assert int(row["missing_required_fields_count"]) == 0
    assert int(row["missing_optional_fields_count"]) > 0
    assert str(row["manual_review_required"]).lower() == "true"


def test_generated_intake_runs_preview_report_with_real_teams(tmp_path: Path) -> None:
    evidence = tmp_path / "data" / "manual" / "evidence"
    _write_evidence(evidence)
    output = tmp_path / "data" / "manual" / "real_match_intake.csv"
    build_real_match_intake_from_excel(
        input_dir=evidence,
        output=output,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        base_dir=tmp_path,
    )
    result = run_match_analysis_preview(real_match_intake=output, base_dir=tmp_path)
    assert result["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert result["human_24_block_report_status"] == "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
    assert int(result["sections_rendered"]) == 24
    assert int(result["required_sections_rendered"]) == 24
    assert result["home_team"] == "Lazio"
    assert result["away_team"] == "Atalanta"
    report = (tmp_path / "outputs" / "analysis_preview" / "human_24_block_report" / "human_24_block_match_report_preview.md").read_text(encoding="utf-8")
    assert "Lazio vs Atalanta on 2026-02-14 (Serie A 2025/26)" in report
    assert "Home FC" not in report
    assert "Away FC" not in report
    assert "Bundesliga 2024" not in report


def test_no_evidence_does_not_overwrite_existing_valid_intake_and_runner_still_works(tmp_path: Path) -> None:
    evidence = tmp_path / "data" / "manual" / "evidence"
    _write_evidence(evidence)
    output = tmp_path / "data" / "manual" / "real_match_intake.csv"
    build_real_match_intake_from_excel(
        input_dir=evidence,
        output=output,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        base_dir=tmp_path,
    )
    before = output.read_text(encoding="utf-8")
    empty_evidence = tmp_path / "data" / "manual" / "empty_evidence"
    empty_evidence.mkdir(parents=True)

    result = build_real_match_intake_from_excel(input_dir=empty_evidence, output=output, base_dir=tmp_path)

    assert result["real_match_intake_excel_builder_status"] == "REAL_MATCH_INTAKE_EXCEL_BUILDER_NO_EVIDENCE_FILES"
    assert int(result["input_files_detected"]) == 0
    assert not bool(result["output_written"])
    assert bool(result["existing_output_protected"])
    assert output.read_text(encoding="utf-8") == before
    assert Path(str(result["summary_csv_path"])).exists()
    assert Path(str(result["summary_md_path"])).exists()
    summary_md = Path(str(result["summary_md_path"])).read_text(encoding="utf-8")
    assert "No Excel evidence files found" in summary_md
    assert "Place team-statistics*.xlsx and team-players*.xlsx into data/manual/evidence" in summary_md

    runner = run_match_analysis_preview(real_match_intake=output, base_dir=tmp_path)
    assert runner["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert runner["human_24_block_report_status"] == "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
    assert runner["home_team"] == "Lazio"
    assert runner["away_team"] == "Atalanta"
    assert int(runner["sections_rendered"]) == 24
    assert int(runner["required_sections_rendered"]) == 24


def test_no_evidence_empty_output_requires_explicit_opt_in(tmp_path: Path) -> None:
    empty_evidence = tmp_path / "data" / "manual" / "empty_evidence"
    empty_evidence.mkdir(parents=True)
    output = tmp_path / "data" / "manual" / "real_match_intake.csv"

    blocked = build_real_match_intake_from_excel(input_dir=empty_evidence, output=output, base_dir=tmp_path)
    assert blocked["real_match_intake_excel_builder_status"] == "REAL_MATCH_INTAKE_EXCEL_BUILDER_NO_EVIDENCE_FILES"
    assert not bool(blocked["output_written"])
    assert not output.exists()

    allowed = build_real_match_intake_from_excel(input_dir=empty_evidence, output=output, base_dir=tmp_path, allow_empty_output=True)
    assert allowed["real_match_intake_excel_builder_status"] == "REAL_MATCH_INTAKE_EXCEL_BUILDER_NO_EVIDENCE_FILES"
    assert bool(allowed["output_written"])
    assert output.exists()
    row = pd.read_csv(output, keep_default_na=False).iloc[0]
    assert int(row["missing_required_fields_count"]) == 5
