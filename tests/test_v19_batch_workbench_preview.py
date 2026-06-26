# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v19_batch_workbench_preview import run_v19_batch_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
BATCH_CONFIG = ROOT / "tests" / "fixtures" / "batch_workbench" / "lazio_atalanta_batch_config.csv"


def test_batch_workbench_processes_lazio_atalanta_config(tmp_path: Path) -> None:
    result = run_v19_batch_workbench_preview(
        batch_config=BATCH_CONFIG,
        output_dir=tmp_path / "batch",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["batch_workbench_status"] == "V19_BATCH_WORKBENCH_PREVIEW_READY"
    assert result["batch_workbench_enabled"] is True
    assert result["portfolio_dashboard_enabled"] is True
    assert result["candidate_shortlist_preview_enabled"] is True
    assert result["batch_no_bet_review_enabled"] is True
    assert int(result["matches_total"]) == 1
    assert int(result["matches_succeeded"]) == 1
    assert int(result["matches_failed"]) == 0

    out = Path(str(result["batch_output_dir"]))
    for name in [
        "batch_dashboard.md",
        "portfolio_summary.md",
        "candidate_shortlist.md",
        "no_bet_review.md",
        "missing_data_priority_board.md",
        "market_family_portfolio.md",
        "readiness_ranking.csv",
        "readiness_ranking.md",
        "batch_results.json",
        "batch_results.csv",
        "batch_bundle_index.csv",
    ]:
        assert (out / name).exists()


def test_batch_results_json_dashboard_and_reports(tmp_path: Path) -> None:
    result = run_v19_batch_workbench_preview(batch_config=BATCH_CONFIG, output_dir=tmp_path / "batch", emit_all=True, base_dir=ROOT)
    out = Path(str(result["batch_output_dir"]))
    payload = json.loads((out / "batch_results.json").read_text(encoding="utf-8"))
    assert payload["batch_workbench_status"] == "V19_BATCH_WORKBENCH_PREVIEW_READY"
    assert payload["matches_total"] == 1
    assert payload["matches_succeeded"] == 1
    assert payload["matches_failed"] == 0
    assert payload["safety"]["network_calls_enabled"] is False
    assert payload["safety"]["betting_logic_enabled"] is False
    assert payload["safety"]["staking_logic_enabled"] is False
    assert payload["safety"]["roi_logic_enabled"] is False
    assert payload["safety"]["batch_workbench_enabled"] is True

    dashboard = (out / "batch_dashboard.md").read_text(encoding="utf-8")
    for phrase in ["v1.9 Batch Workbench Dashboard", "Match Overview", "Portfolio Read", "Candidate Shortlist Preview", "No-Bet / Blocked Matches", "Missing Data Priorities", "Safety Footer"]:
        assert phrase in dashboard

    shortlist = (out / "candidate_shortlist.md").read_text(encoding="utf-8")
    for phrase in ["Lazio", "Atalanta", "ANALYST_LEAN_ONLY", "Fill critical missing data before promotion"]:
        assert phrase in shortlist

    no_bet = (out / "no_bet_review.md").read_text(encoding="utf-8")
    for phrase in ["Missing Recent Form", "Missing Big Chances", "Missing Availability", "Missing Market Movement", "High Conflict"]:
        assert phrase in no_bet

    priority = (out / "missing_data_priority_board.md").read_text(encoding="utf-8")
    for phrase in ["Recent Form", "Big Chances", "Availability", "Opening/Closing Market", "DNB/OU Market"]:
        assert phrase in priority

    market = (out / "market_family_portfolio.md").read_text(encoding="utf-8")
    for phrase in ["1X2", "Double Chance", "DNB", "Over/Under", "BTTS", "Score Family", "No-Bet"]:
        assert phrase in market

    ranking = pd.read_csv(out / "readiness_ranking.csv", keep_default_na=False)
    assert int(ranking.loc[0, "evidence_readiness_score"]) == 85
    assert ranking.loc[0, "conflict_score"] == "HIGH"
    assert str(ranking.loc[0, "promotion_allowed"]).lower() == "false"


def test_batch_invalid_config_row_does_not_crash_entire_batch(tmp_path: Path) -> None:
    config = tmp_path / "invalid_batch.csv"
    config.write_text(
        "match_id,input_dir,home_team,away_team,competition,season,match_date,manual_evidence_completion,run_transition_lab,notes\n"
        "valid,tests/fixtures/excel_evidence/lazio_atalanta_2026_02_14,Lazio,Atalanta,Serie A,2025/26,2026-02-14,tests/fixtures/manual_evidence_completion/lazio_atalanta_completion.csv,false,valid row\n"
        "invalid,,Lazio,,Serie A,2025/26,2026-02-14,,false,invalid row\n",
        encoding="utf-8",
    )
    result = run_v19_batch_workbench_preview(batch_config=config, output_dir=tmp_path / "batch", emit_all=True, base_dir=ROOT)
    assert result["batch_workbench_status"] == "V19_BATCH_WORKBENCH_PREVIEW_READY"
    assert int(result["matches_total"]) == 2
    assert int(result["matches_succeeded"]) == 1
    assert int(result["matches_failed"]) >= 1
    payload = json.loads(Path(str(result["batch_results_json_path"])).read_text(encoding="utf-8"))
    failed = [m for m in payload["matches"] if m["status"] == "FAILED"]
    assert failed
    assert "Missing required fields" in failed[0]["error_message"]
