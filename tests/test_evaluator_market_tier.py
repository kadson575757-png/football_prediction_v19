# -*- coding: utf-8 -*-
"""Tests for the market-tier summary sections added to evaluate_daily_recommendations.

Covers:
- _parse_bool_success: robust coercion of success values
- _tier_score_bucket: bucket label assignment
- market-tier grouping counts (A_TIER, B_TIER, HARD_NO_GO)
- unmatched / unverified rows excluded
- tier score bucket rendering
- existing evaluator summary still produces expected sections

All tests use the public helpers directly or drive evaluate() with synthetic DataFrames.
No network calls, no file I/O to live data.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

# Import helpers under test
from scripts.evaluate_daily_recommendations import (
    _parse_bool_success,
    _tier_score_bucket,
    evaluate,
)

# ---------------------------------------------------------------------------
# _parse_bool_success
# ---------------------------------------------------------------------------

class TestParseBoolSuccess:
    @pytest.mark.parametrize("val,expected", [
        (True,    True),
        (False,   False),
        (1,       True),
        (0,       False),
        ("True",  True),
        ("False", False),
        ("true",  True),
        ("false", False),
        ("TRUE",  True),
        ("FALSE", False),
        ("1",     True),
        ("0",     False),
        ("yes",   True),
        ("no",    False),
        ("YES",   True),
        ("NO",    False),
    ])
    def test_known_values(self, val, expected):
        assert _parse_bool_success(val) is expected

    @pytest.mark.parametrize("val", [None, float("nan"), "", "  ", "maybe", "n/a"])
    def test_unknown_values_return_none(self, val):
        assert _parse_bool_success(val) is None


# ---------------------------------------------------------------------------
# _tier_score_bucket
# ---------------------------------------------------------------------------

class TestTierScoreBucket:
    @pytest.mark.parametrize("score,bucket", [
        (100,  "80+"),
        (88,   "80+"),
        (80,   "80+"),
        (79,   "70-79"),
        (70,   "70-79"),
        (69,   "50-69"),
        (50,   "50-69"),
        (49,   "<50"),
        (5,    "<50"),
        (0,    "<50"),
    ])
    def test_bucket_boundaries(self, score, bucket):
        assert _tier_score_bucket(score) == bucket

    def test_none_returns_unknown(self):
        assert _tier_score_bucket(None) == "unknown"

    def test_string_score_parsed(self):
        assert _tier_score_bucket("88") == "80+"


# ---------------------------------------------------------------------------
# Helpers to build synthetic data for evaluate()
# ---------------------------------------------------------------------------

def _make_pre_df(**overrides) -> pd.DataFrame:
    """Minimal pre-match recommendation row."""
    base = {
        "date": "2026-05-17",
        "league": "La Liga",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "recommended_market_type": "UNDER",
        "recommended_market_subtype": "UNDER_35",
        "recommended_market_read": "under_profile",
        "recommendation_strength": "STRONG",
        "confidence": "HIGH",
        "market_tier": "A_TIER",
        "market_tier_score": 88,
        "market_tier_reason": "HIGH strength, no warning, A-Tier subtype",
        "market_tier_flags": "",
        "type_success": "",
        "subtype_success": "",
        "control_10": 2.0,
        "chaos_10": 3.0,
        "likely_1x2": "Home",
    }
    base.update(overrides)
    return pd.DataFrame([base])


def _make_scores_df(home_goals: int, away_goals: int, **overrides) -> pd.DataFrame:
    base = {
        "date": "2026-05-17",
        "league": "La Liga",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "home_goals": home_goals,
        "away_goals": away_goals,
        "verified": "yes",
        "source_note": "football-data.org",
    }
    base.update(overrides)
    return pd.DataFrame([base])


def _run_evaluate(tmp_path: Path, pre_rows: list[dict], score_rows: list[dict]) -> pd.DataFrame:
    """Write synthetic CSVs, run evaluate(), return the output eval CSV."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    scores_path = tmp_path / "scores.csv"
    out_dir = tmp_path / "out"

    pd.DataFrame(pre_rows).to_csv(reports_dir / "la_liga_2026-05-17_daily_report.csv", index=False)
    pd.DataFrame(score_rows).to_csv(scores_path, index=False)

    evaluate(reports_dir=reports_dir, scores_path=scores_path, out_dir=out_dir)
    return pd.read_csv(out_dir / "daily_recommendation_eval.csv")


# ---------------------------------------------------------------------------
# Market-tier grouping: counts
# ---------------------------------------------------------------------------

class TestMarketTierGrouping:
    def test_a_tier_hit_counted(self, tmp_path):
        """A_TIER row with UNDER_35 success (0-2 goals) → type_success=True."""
        pre = [_make_pre_df(market_tier="A_TIER", market_tier_score=88,
                            recommended_market_type="UNDER",
                            recommended_market_subtype="UNDER_35").iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        row = df.iloc[0]
        assert _parse_bool_success(row["type_success"]) is True
        assert row["market_tier"] == "A_TIER"

    def test_a_tier_miss_counted(self, tmp_path):
        """A_TIER row with UNDER_35, but 4 goals → type_success=False."""
        pre = [_make_pre_df(market_tier="A_TIER", market_tier_score=88,
                            recommended_market_type="UNDER",
                            recommended_market_subtype="UNDER_35").iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 4, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        assert _parse_bool_success(df.iloc[0]["type_success"]) is False

    def test_b_tier_hit_counted(self, tmp_path):
        """B_TIER AVOID row that succeeds (direction wrong)."""
        pre = [_make_pre_df(
            market_tier="B_TIER", market_tier_score=70,
            recommended_market_type="AVOID",
            recommended_market_subtype="AVOID_LOW_CONTROL",
            recommended_market_read="avoid_low_control",
            confidence="LOW",
            likely_1x2="Away",  # model said away
        ).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 2, "away_goals": 0,  # home win → direction wrong for "Away"
                   "verified": "yes", "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        assert _parse_bool_success(df.iloc[0]["type_success"]) is True
        assert df.iloc[0]["market_tier"] == "B_TIER"

    def test_hard_nogo_row_evaluated(self, tmp_path):
        """HARD_NO_GO BTTS_OVER row: a result is still computed (for diagnostic audit)."""
        pre = [_make_pre_df(
            market_tier="HARD_NO_GO", market_tier_score=5,
            recommended_market_type="BTTS_OVER",
            recommended_market_subtype="BOTH_OVER25_BTTS",
        ).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 2, "away_goals": 1,  # 3 goals, both scored → OR success
                   "verified": "yes", "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        # type_success is computed for diagnostic purposes regardless of tier
        ts = _parse_bool_success(df.iloc[0]["type_success"])
        assert ts is True  # 3 goals → BTTS_OVER OR logic = True
        assert df.iloc[0]["market_tier"] == "HARD_NO_GO"


# ---------------------------------------------------------------------------
# Unmatched / unverified rows excluded
# ---------------------------------------------------------------------------

class TestUnverifiedExclusion:
    def test_unverified_row_has_null_type_success(self, tmp_path):
        """Row with no matching score → type_success must be null/None.

        A second (anchor) row is included so evaluate() writes the CSV,
        then we verify the first row (no match) has no type_success.
        """
        # Row 0: the unmatched one
        unmatched = _make_pre_df(home_team="Orphan FC", away_team="Nomatch FC").iloc[0].to_dict()
        # Row 1: anchor — has a real score match so evaluate() doesn't bail early
        anchor = _make_pre_df().iloc[0].to_dict()
        pre = [unmatched, anchor]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",  # matches anchor
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        # Find the unmatched row (home_team=Orphan FC)
        unmatched_row = df[df["home_team"] == "Orphan FC"]
        assert len(unmatched_row) == 1
        assert _parse_bool_success(unmatched_row.iloc[0]["type_success"]) is None

    def test_verified_no_row_skipped(self, tmp_path):
        """verified=no score must not produce a type_success for the target row.

        A second anchor row with verified=yes keeps evaluate() running.
        The target team's score is verified=no so should not match.
        """
        # Target pre-match row (score will be verified=no)
        target = _make_pre_df(home_team="Target FC", away_team="Rival FC").iloc[0].to_dict()
        # Anchor pre-match row (score will be verified=yes)
        anchor = _make_pre_df().iloc[0].to_dict()
        pre = [target, anchor]
        scores = [
            {"date": "2026-05-17", "league": "La Liga",
             "home_team": "Target FC", "away_team": "Rival FC",
             "home_goals": 3, "away_goals": 0,
             "verified": "no",   # ← unverified: must be ignored
             "source_note": "test"},
            {"date": "2026-05-17", "league": "La Liga",
             "home_team": "Home FC", "away_team": "Away FC",
             "home_goals": 1, "away_goals": 0,
             "verified": "yes",  # anchor
             "source_note": "test"},
        ]
        df = _run_evaluate(tmp_path, pre, scores)
        target_row = df[df["home_team"] == "Target FC"]
        assert len(target_row) == 1
        assert _parse_bool_success(target_row.iloc[0]["type_success"]) is None


# ---------------------------------------------------------------------------
# Score bucket rendering
# ---------------------------------------------------------------------------

class TestScoreBucketRendering:
    def test_summary_md_contains_tier_section(self, tmp_path):
        """Summary markdown must contain the Market Tier section heading."""
        pre = [_make_pre_df(market_tier="A_TIER", market_tier_score=88).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        _run_evaluate(tmp_path, pre, scores)
        md = (tmp_path / "out" / "daily_recommendation_eval_summary.md").read_text(encoding="utf-8")
        assert "## Success Rate by Market Tier" in md

    def test_summary_md_contains_score_bucket_section(self, tmp_path):
        """Summary markdown must contain the Tier Score Bucket section heading."""
        pre = [_make_pre_df(market_tier="A_TIER", market_tier_score=88).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        _run_evaluate(tmp_path, pre, scores)
        md = (tmp_path / "out" / "daily_recommendation_eval_summary.md").read_text(encoding="utf-8")
        assert "## Success Rate by Market Tier Score Bucket" in md

    def test_80_plus_bucket_appears_for_high_score(self, tmp_path):
        pre = [_make_pre_df(market_tier="A_TIER", market_tier_score=88).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        _run_evaluate(tmp_path, pre, scores)
        md = (tmp_path / "out" / "daily_recommendation_eval_summary.md").read_text(encoding="utf-8")
        assert "80+" in md


# ---------------------------------------------------------------------------
# Existing evaluator summary still works
# ---------------------------------------------------------------------------

class TestExistingSummaryIntegrity:
    def test_market_type_section_still_present(self, tmp_path):
        pre = [_make_pre_df().iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        _run_evaluate(tmp_path, pre, scores)
        md = (tmp_path / "out" / "daily_recommendation_eval_summary.md").read_text(encoding="utf-8")
        assert "## Success Rate by Recommended Market Type" in md

    def test_eval_csv_preserves_tier_fields(self, tmp_path):
        """All four market_tier fields must survive in the output CSV."""
        pre = [_make_pre_df(
            market_tier="A_TIER",
            market_tier_score=88,
            market_tier_reason="HIGH strength",
            market_tier_flags="",
        ).iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        for col in ("market_tier", "market_tier_score", "market_tier_reason", "market_tier_flags"):
            assert col in df.columns, f"Missing column: {col}"

    def test_eval_csv_preserves_success_fields(self, tmp_path):
        """type_success and subtype_success must be present in the output CSV."""
        pre = [_make_pre_df().iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        df = _run_evaluate(tmp_path, pre, scores)
        assert "type_success" in df.columns
        assert "subtype_success" in df.columns

    def test_overall_assessment_section_present(self, tmp_path):
        pre = [_make_pre_df().iloc[0].to_dict()]
        scores = [{"date": "2026-05-17", "league": "La Liga",
                   "home_team": "Home FC", "away_team": "Away FC",
                   "home_goals": 1, "away_goals": 0, "verified": "yes",
                   "source_note": "test"}]
        _run_evaluate(tmp_path, pre, scores)
        md = (tmp_path / "out" / "daily_recommendation_eval_summary.md").read_text(encoding="utf-8")
        assert "## Recommended Market Layer Assessment" in md
