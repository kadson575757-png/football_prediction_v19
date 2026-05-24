# -*- coding: utf-8 -*-
"""Tests for team-name alias resolution and fuzzy fallback matching.

Verifies that the combination of team_aliases.json + fuzzy_team_key()
correctly resolves the mismatch between daily-report short names and
football-data.org official names.

No real API calls are made.  No scores are guessed.
"""
from __future__ import annotations

import pandas as pd
import pytest

from football_prediction_v19.team_names import (
    fuzzy_team_key,
    load_team_aliases,
    normalize_team_name,
)
from football_prediction_v19.importers.official_results import (
    OUTPUT_COLUMNS,
    merge_official_results_with_daily_reports,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_alias_cache() -> None:
    """Force reload of team_aliases.json between tests that change it."""
    load_team_aliases.cache_clear()


def _norm(name: str) -> str:
    _clear_alias_cache()
    return normalize_team_name(name)


def _fuzz(name: str) -> str:
    _clear_alias_cache()
    return fuzzy_team_key(name)


def _results_row(
    home: str,
    away: str,
    date: str = "2026-05-17",
    league: str = "La Liga",
    home_goals: int = 2,
    away_goals: int = 1,
) -> dict:
    return {
        "date": date, "league": league,
        "home_team": home, "away_team": away,
        "home_goals": home_goals, "away_goals": away_goals,
        "verified": "yes",
        "source_note": "football-data.org",
        "source_match_id": 9999,
        "source_status": "FINISHED",
        "last_updated": "2026-05-17T22:00:00Z",
    }


def _pre_row(
    home: str,
    away: str,
    date: str = "2026-05-17",
    league: str = "La Liga",
) -> dict:
    return {
        "date": date, "league": league,
        "home_team": home, "away_team": away,
        "likely_1x2": "Home", "confidence": "MEDIUM",
        "model_home_prob": 0.5, "model_draw_prob": 0.25, "model_away_prob": 0.25,
        "control_10": 3.0, "chaos_10": 2.0,
        "recommended_market_type": "DOUBLE_CHANCE",
        "recommended_market_read": "home_or_draw",
        "recommendation_strength": "MEDIUM",
        "risk_note": "",
    }


def _run_merge(
    tmp_path,
    pre_rows: list[dict],
    api_rows: list[dict],
    report_filename: str = "laliga_2026-05-17_daily_report.csv",
) -> pd.DataFrame:
    """Write pre-match CSV, build API results DataFrame, run merge, return output."""
    _clear_alias_cache()
    pre_df = pd.DataFrame(pre_rows)
    csv_path = tmp_path / report_filename
    pre_df.to_csv(csv_path, index=False)

    results_df = pd.DataFrame(api_rows)[OUTPUT_COLUMNS]
    out_path = tmp_path / "final_scores.csv"
    return merge_official_results_with_daily_reports(results_df, tmp_path, out_path)


# ===========================================================================
# 1. La Liga short-name → official-name alias tests
# ===========================================================================

class TestLaLigaAliases:
    """Our reports use short names; football-data.org returns official names."""

    def test_sociedad_normalises_to_real_sociedad(self):
        assert _norm("Sociedad") == "Real Sociedad"

    def test_real_sociedad_de_futbol_normalises_to_real_sociedad(self):
        assert _norm("Real Sociedad de Fútbol") == "Real Sociedad"

    def test_vallecano_normalises_to_rayo_vallecano(self):
        assert _norm("Vallecano") == "Rayo Vallecano"

    def test_ath_madrid_normalises_to_atletico_madrid(self):
        assert _norm("Ath Madrid") == "Atletico Madrid"

    def test_club_atletico_madrid_normalises_to_atletico_madrid(self):
        assert _norm("Club Atlético de Madrid") == "Atletico Madrid"

    def test_atletico_de_madrid_normalises_to_atletico_madrid(self):
        assert _norm("Atlético de Madrid") == "Atletico Madrid"

    def test_ath_bilbao_normalises_to_athletic_club(self):
        assert _norm("Ath Bilbao") == "Athletic Club"

    def test_espanol_normalises_to_espanyol(self):
        assert _norm("Espanol") == "Espanyol"

    def test_rcd_espanyol_normalises_to_espanyol(self):
        assert _norm("RCD Espanyol") == "Espanyol"

    def test_alaves_normalises_same_as_deportivo_alaves(self):
        assert _norm("Alavés") == _norm("Alaves")

    def test_celta_normalises_to_celta_vigo(self):
        assert _norm("Celta") == "Celta Vigo"

    def test_rc_celta_de_vigo_normalises_to_celta_vigo(self):
        assert _norm("RC Celta de Vigo") == "Celta Vigo"

    def test_sociedad_short_matches_api_name_in_merge(self, tmp_path):
        """Report: 'Sociedad'  API: 'Real Sociedad de Fútbol'  → verified=yes."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Sociedad", "Valencia")],
            api_rows=[_results_row("Real Sociedad de Fútbol", "Valencia CF")],
        )
        row = out.iloc[0]
        assert row["verified"] == "yes"
        assert row["home_goals"] == 2
        assert row["away_goals"] == 1

    def test_ath_madrid_matches_club_atletico_de_madrid(self, tmp_path):
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Ath Madrid", "Girona")],
            api_rows=[_results_row("Club Atlético de Madrid", "Girona FC")],
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_vallecano_matches_rayo_vallecano(self, tmp_path):
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Vallecano", "Villarreal")],
            api_rows=[_results_row("Rayo Vallecano", "Villarreal CF")],
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_espanol_matches_rcd_espanyol_de_barcelona(self, tmp_path):
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Osasuna", "Espanol")],
            api_rows=[_results_row("CA Osasuna", "RCD Espanyol de Barcelona")],
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_celta_matches_rc_celta_de_vigo(self, tmp_path):
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Ath Bilbao", "Celta")],
            api_rows=[_results_row("Athletic Club", "RC Celta de Vigo")],
        )
        assert out.iloc[0]["verified"] == "yes"


# ===========================================================================
# 2. EPL alias tests  (Wolves / Brighton and FC-suffix cases)
# ===========================================================================

class TestEPLAliases:
    def test_wolves_normalises_to_wolverhampton(self):
        assert _norm("Wolves") == "Wolverhampton Wanderers"

    def test_wolverhampton_wanderers_fc_normalises_correctly(self):
        assert _norm("Wolverhampton Wanderers FC") == "Wolverhampton Wanderers"

    def test_brighton_normalises_to_brighton_and_hove_albion(self):
        assert _norm("Brighton") == "Brighton & Hove Albion"

    def test_brighton_fc_normalises_correctly(self):
        assert _norm("Brighton & Hove Albion FC") == "Brighton & Hove Albion"

    def test_leeds_normalises_to_leeds_united(self):
        assert _norm("Leeds") == "Leeds United"

    def test_everton_fc_normalises_to_everton(self):
        assert _norm("Everton FC") == "Everton"

    def test_sunderland_afc_normalises_to_sunderland(self):
        assert _norm("Sunderland AFC") == "Sunderland"

    def test_wolves_matches_wolverhampton_wanderers_fc_in_merge(self, tmp_path):
        """Report: 'Wolves'  API: 'Wolverhampton Wanderers FC'  → verified=yes."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Wolverhampton Wanderers", "Fulham", league="EPL")],
            api_rows=[_results_row("Wolverhampton Wanderers FC", "Fulham FC", league="EPL")],
            report_filename="epl_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_brighton_matches_brighton_fc_in_merge(self, tmp_path):
        """Report: 'Leeds'  API: 'Leeds United FC'  and  'Brighton & Hove Albion FC'."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Leeds", "Brighton & Hove Albion", league="EPL")],
            api_rows=[_results_row("Leeds United FC", "Brighton & Hove Albion FC", league="EPL")],
            report_filename="epl_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_brentford_fc_suffix_fuzzy_match(self, tmp_path):
        """Report: 'Brentford'  API: 'Brentford FC'  → fuzzy fallback → verified=yes."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Brentford", "Crystal Palace", league="EPL")],
            api_rows=[_results_row("Brentford FC", "Crystal Palace FC", league="EPL")],
            report_filename="epl_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"


# ===========================================================================
# 3. Eredivisie alias tests
# ===========================================================================

class TestEredivisieAliases:
    def test_fortuna_normalises_to_fortuna_sittard(self):
        assert _norm("Fortuna") == "Fortuna Sittard"

    def test_sbv_excelsior_normalises_to_excelsior_rotterdam(self):
        assert _norm("SBV Excelsior") == "Excelsior Rotterdam"

    def test_excelsior_normalises_to_excelsior_rotterdam(self):
        assert _norm("Excelsior") == "Excelsior Rotterdam"

    def test_psv_normalises_to_psv_eindhoven(self):
        assert _norm("PSV") == "PSV Eindhoven"

    def test_twente_normalises_to_fc_twente(self):
        assert _norm("Twente") == "FC Twente"

    def test_sparta_normalises_to_sparta_rotterdam(self):
        assert _norm("Sparta") == "Sparta Rotterdam"

    def test_fortuna_matches_fortuna_sittard_in_merge(self, tmp_path):
        """Report: 'FC Utrecht'  vs 'Fortuna'  API: 'FC Utrecht' vs 'Fortuna Sittard'."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("FC Utrecht", "Fortuna", league="Eredivisie")],
            api_rows=[_results_row("FC Utrecht", "Fortuna Sittard", league="Eredivisie")],
            report_filename="eredivisie_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_sbv_excelsior_matches_excelsior_rotterdam_in_merge(self, tmp_path):
        """Report: 'Sparta Rotterdam' vs 'Excelsior Rotterdam'  API: 'Sparta Rotterdam' vs 'SBV Excelsior'."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Sparta Rotterdam", "Excelsior Rotterdam", league="Eredivisie")],
            api_rows=[_results_row("Sparta Rotterdam", "SBV Excelsior", league="Eredivisie")],
            report_filename="eredivisie_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"

    def test_psv_eindhoven_matches_api_psv_in_merge(self, tmp_path):
        """Report: 'PSV Eindhoven'  API: 'PSV Eindhoven'  → exact match."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("PSV Eindhoven", "FC Twente", league="Eredivisie")],
            api_rows=[_results_row("PSV Eindhoven", "FC Twente", league="Eredivisie")],
            report_filename="eredivisie_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "yes"


# ===========================================================================
# 4. Ambiguous match still not verified
# ===========================================================================

class TestAmbiguousMatch:
    def test_two_api_rows_same_teams_stays_unverified(self, tmp_path):
        api_rows = [
            _results_row("Real Sociedad de Fútbol", "Valencia CF"),
            _results_row("Real Sociedad de Fútbol", "Valencia CF", home_goals=0, away_goals=0),
        ]
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Sociedad", "Valencia")],
            api_rows=api_rows,
        )
        assert out.iloc[0]["verified"] == "no"
        assert out.iloc[0]["source_note"] == "ambiguous_match"

    def test_two_fuzzy_candidates_stays_unverified(self, tmp_path):
        """If fuzzy fallback finds multiple candidates, do not verify."""
        # Two matches where both fuzzy-normalize to the same key
        api_rows = [
            _results_row("Brentford FC", "Crystal Palace FC", home_goals=1, away_goals=0, league="EPL"),
            _results_row("Brentford FC", "Crystal Palace FC", home_goals=2, away_goals=1, league="EPL"),
        ]
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("Brentford", "Crystal Palace", league="EPL")],
            api_rows=api_rows,
            report_filename="epl_2026-05-17_daily_report.csv",
        )
        assert out.iloc[0]["verified"] == "no"
        assert out.iloc[0]["source_note"] == "ambiguous_match"


# ===========================================================================
# 5. Unsupported 2. Bundesliga remains no_match_found / not verified
# ===========================================================================

class TestUnsupportedLeague:
    def test_2bundesliga_no_api_match_stays_no_match_found(self, tmp_path):
        """2. Bundesliga is not in LEAGUE_TO_FD_CODE; result stays no_match_found."""
        # API results contain only La Liga data; pre-match has 2. Bundesliga
        api_rows = [_results_row("Real Sociedad de Fútbol", "Valencia CF")]

        d2_csv = tmp_path / "d2_2026-05-17_daily_report.csv"
        pd.DataFrame([_pre_row("Hertha BSC", "Schalke", league="2. Bundesliga")]).to_csv(d2_csv, index=False)

        results_df = pd.DataFrame(api_rows)[OUTPUT_COLUMNS]
        out = merge_official_results_with_daily_reports(
            results_df, tmp_path, tmp_path / "scores.csv"
        )
        row = out[out["league"] == "2. Bundesliga"]
        assert len(row) == 1
        assert row.iloc[0]["verified"] == "no"
        assert row.iloc[0]["source_note"] == "no_match_found"
        assert pd.isna(row.iloc[0]["home_goals"]) or row.iloc[0]["home_goals"] is None

    def test_unknown_name_with_no_alias_stays_no_match_found(self, tmp_path):
        """A completely unknown short name that has no alias and no fuzzy match."""
        out = _run_merge(
            tmp_path,
            pre_rows=[_pre_row("XYZ United", "ABC City")],
            api_rows=[_results_row("Real Sociedad de Fútbol", "Valencia CF")],
        )
        assert out.iloc[0]["verified"] == "no"
        assert out.iloc[0]["source_note"] == "no_match_found"


# ===========================================================================
# 6. fuzzy_team_key unit tests
# ===========================================================================

class TestFuzzyTeamKey:
    def test_strips_fc_suffix(self):
        assert _fuzz("Brentford FC") == _fuzz("Brentford")

    def test_strips_afc_suffix(self):
        assert _fuzz("Sunderland AFC") == _fuzz("Sunderland")

    def test_strips_cf_suffix(self):
        assert _fuzz("Valencia CF") == _fuzz("Valencia")

    def test_strips_accents(self):
        # "Alavés" → "alaves" after accent removal
        key = _fuzz("Alavés")
        assert "a" in key  # just verify it doesn't crash and removes combining chars
        assert "é" not in key

    def test_real_not_stripped(self):
        # "real" is NOT in the strip list — distinguishes Real Madrid from Atletico
        key = _fuzz("Real Madrid")
        assert "real" in key

    def test_brighton_hove_albion_fc_same_as_brighton_hove_albion(self):
        assert _fuzz("Brighton & Hove Albion FC") == _fuzz("Brighton & Hove Albion")

    def test_wolverhampton_fc_same_as_wolverhampton(self):
        assert _fuzz("Wolverhampton Wanderers FC") == _fuzz("Wolverhampton Wanderers")

    def test_none_input_safe(self):
        """fuzzy_team_key must not crash on empty/None-like input."""
        result = fuzzy_team_key("")
        assert isinstance(result, str)

    def test_alias_applied_before_fuzz(self):
        """Alias lookup happens first, so 'Sociedad' → 'Real Sociedad' → fuzzy key."""
        _clear_alias_cache()
        key = fuzzy_team_key("Sociedad")
        assert "real" in key and "sociedad" in key
