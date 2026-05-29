# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import analyze_tier_rule_candidates as analysis  # noqa: E402


def _row(
    *,
    league: str,
    market_tier: str = "A_TIER",
    subtype: str = "TARGET",
    success=True,
    agreement: str = "NONE",
) -> dict:
    return {
        "league": league,
        "market_tier": market_tier,
        "recommended_market_subtype": subtype,
        "type_success": success,
        "ensemble_agreement": agreement,
        "league_warning_flags": "",
        "league_adjusted_strength": "HIGH",
        "chaos_bucket": "low",
        "ctrl_bucket": "high",
        "odds_bucket": "mid",
        "season_phase": "mid",
    }


def _rows(n: int, hits: int, **kwargs) -> list[dict]:
    return [_row(success=i < hits, **kwargs) for i in range(n)]


def _prepared(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)
    return analysis.ensure_analysis_columns(df)


def _candidate_and_stability(rows: list[dict], min_sample: int = 50):
    df = _prepared(rows)
    table = analysis.build_summary_table(df)
    table = analysis.apply_candidate_detection(
        table,
        min_sample=min_sample,
        small_sample=20,
        threshold_pp=3.0,
    )
    stability = analysis.build_stability_table(
        df,
        table,
        min_sample=min_sample,
        threshold_pp=3.0,
    )
    return table, stability


def _label_for(stability: pd.DataFrame, text: str) -> str:
    row = stability[stability["candidate_key"].astype(str).str.contains(text, regex=False)].iloc[0]
    return str(row["stability_label"])


def _write_input(tmp_path: Path, rows: list[dict]) -> Path:
    input_dir = tmp_path / "season_replay"
    input_dir.mkdir()
    pd.DataFrame(rows).to_csv(input_dir / "synthetic_evaluation.csv", index=False)
    return input_dir


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stable_promote_candidate_detected_across_three_leagues():
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 18, league=league, subtype="TARGET")
        rows += _rows(20, 14, league=league, subtype="BASE")

    _, stability = _candidate_and_stability(rows)

    assert _label_for(stability, "recommended_market_subtype=TARGET") == "STABLE_PROMOTE"


def test_stable_downgrade_candidate_detected_across_three_leagues():
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 13, league=league, subtype="TARGET")
        rows += _rows(20, 18, league=league, subtype="BASE")

    _, stability = _candidate_and_stability(rows)

    assert _label_for(stability, "recommended_market_subtype=TARGET") == "STABLE_DOWNGRADE"


def test_stable_no_go_candidate_detected_when_rate_below_65():
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 10, league=league, subtype="TARGET")
        rows += _rows(20, 18, league=league, subtype="BASE")

    _, stability = _candidate_and_stability(rows)

    assert _label_for(stability, "recommended_market_subtype=TARGET") == "STABLE_NO_GO"


def test_league_specific_candidate_detected_when_only_two_leagues_support_it():
    rows = []
    for league in ("L1", "L2"):
        rows += _rows(30, 27, league=league, subtype="TARGET")
        rows += _rows(30, 21, league=league, subtype="BASE")

    _, stability = _candidate_and_stability(rows)

    assert _label_for(stability, "recommended_market_subtype=TARGET") == "LEAGUE_SPECIFIC"


def test_unstable_candidate_detected_when_league_signals_conflict():
    rows = []
    rows += _rows(20, 20, league="L1", subtype="TARGET")
    rows += _rows(20, 10, league="L1", subtype="BASE")
    rows += _rows(20, 12, league="L2", subtype="TARGET")
    rows += _rows(20, 18, league="L2", subtype="BASE")
    rows += _rows(20, 20, league="L3", subtype="TARGET")
    rows += _rows(20, 10, league="L3", subtype="BASE")
    rows += _rows(20, 10, league="L4", subtype="TARGET")
    rows += _rows(20, 18, league="L4", subtype="BASE")

    _, stability = _candidate_and_stability(rows)

    assert _label_for(stability, "recommended_market_subtype=TARGET") == "UNSTABLE"


def test_small_sample_candidate_detected():
    rows = _rows(15, 14, league="L1", subtype="TARGET")
    rows += _rows(15, 10, league="L1", subtype="BASE")

    _, stability = _candidate_and_stability(rows, min_sample=50)

    assert "SMALL_SAMPLE" in set(stability["stability_label"])


def test_recommendation_section_exists(tmp_path):
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 18, league=league, subtype="TARGET")
        rows += _rows(20, 14, league=league, subtype="BASE")
    input_dir = _write_input(tmp_path, rows)

    analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", stability_report=True)
    markdown = (tmp_path / "out" / analysis.STABILITY_MD).read_text(encoding="utf-8")

    assert "## H. Recommended Next Action" in markdown
    assert "Phase 11.2 is diagnostic only. No tier rules were changed." in markdown


def test_stability_report_files_are_written(tmp_path):
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 18, league=league, subtype="TARGET")
        rows += _rows(20, 14, league=league, subtype="BASE")
    input_dir = _write_input(tmp_path, rows)
    out = tmp_path / "out"

    analysis.run(input_dir=input_dir, output_dir=out, stability_report=True)

    assert (out / analysis.STABILITY_CSV).exists()
    assert (out / analysis.STABILITY_MD).exists()


def test_scope_modern_tier_excludes_unknown_market_tier_rows(tmp_path):
    rows = _rows(60, 60, league="L1", market_tier="UNKNOWN", subtype="TARGET")
    rows += _rows(60, 30, league="L1", market_tier="UNKNOWN", subtype="BASE")
    input_dir = _write_input(tmp_path, rows)

    table, _ = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", stability_report=True)

    assert table.empty
    stability = pd.read_csv(tmp_path / "out" / analysis.STABILITY_CSV)
    assert stability.empty


def test_no_market_tier_probability_or_recommended_market_files_modified(tmp_path):
    watched = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/model.py",
        ROOT / "scripts/run_season_replay_audit.py",
    ]
    before = {path: _hash(path) for path in watched}
    rows = []
    for league in ("L1", "L2", "L3"):
        rows += _rows(20, 18, league=league, subtype="TARGET")
        rows += _rows(20, 14, league=league, subtype="BASE")
    input_dir = _write_input(tmp_path, rows)

    analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", stability_report=True)

    after = {path: _hash(path) for path in watched}
    assert after == before
