# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_phase_status  # noqa: E402


def test_market_tiers_reflect_base_market_tier_module() -> None:
    tiers = audit_phase_status.available_market_tiers(ROOT)

    assert tiers == [
        "A_TIER",
        "B_TIER",
        "C_TIER",
        "DOWNGRADE",
        "HARD_NO_GO",
        "OBSERVE_ONLY",
    ]
    assert "SUPER_A_TIER" not in tiers


def test_wf_model_choices_include_ensemble_without_dropping_existing_choices() -> None:
    choices = audit_phase_status.available_wf_model_choices(ROOT)

    assert choices == [
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
        "ensemble",
    ]


def test_phase10_is_detected_as_partially_wired() -> None:
    audit = audit_phase_status.build_audit(ROOT)

    assert audit["super_a_tier"]["appears_in_code"] is True
    assert audit["super_a_tier"]["in_market_tiers"] is False
    assert audit["super_a_tier"]["produced_by_ensemble_override"] is True
    assert audit["ensemble"]["predictor_file_exists"] is True
    assert audit["ensemble"]["run_season_replay_supports_ensemble"] is True
    assert audit["ensemble"]["cli_wf_model_has_ensemble_choice"] is True
    assert audit["ensemble"]["prediction_serialization_supported"] is True
    assert audit["ensemble"]["agreement_high_medium_low_supported"] is True


def test_report_contains_required_phase_sections() -> None:
    audit = audit_phase_status.build_audit(ROOT)
    markdown = audit_phase_status.generate_markdown(audit)

    for phase in ("Phase 5", "Phase 6", "Phase 7", "Phase 8", "Phase 9", "Phase 10"):
        assert phase in markdown
    assert "Missing Wiring" in markdown
    assert "SUPER_A_TIER Status" in markdown
    assert "True Multi-Model Ensemble Status" in markdown
    assert "Ensemble Agreement Status" in markdown


def test_cli_summary_prints_required_diagnostics() -> None:
    audit = audit_phase_status.build_audit(ROOT)
    summary = audit_phase_status.format_cli_summary(audit)

    assert "Available market tiers:" in summary
    assert "Available wf-model choices:" in summary
    assert "SUPER_A_TIER appears in code:" in summary
    assert "Ensemble mode appears in code:" in summary
    assert "run_season_replay_audit supports ensemble mode:" in summary
    assert "daily reports include ensemble fields:" in summary
