# -*- coding: utf-8 -*-
"""Static phase-wiring audit for the football prediction project.

Diagnostic only: this script does not change model, probability, market-tier,
betting, ROI, or staking logic.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SEARCH_TERMS: tuple[str, ...] = (
    "SUPER_A_TIER",
    "ensemble predictor",
    "EnsemblePredictor",
    "ensemble_agreement",
    "ensemble_model_predictions",
    "ensemble_note",
    "wf-model",
    "build_market_tier",
    "market_tier_score",
)

CODE_DIRS: tuple[str, ...] = ("src", "scripts", "tests")
TEXT_SUFFIXES: frozenset[str] = frozenset({".py", ".md", ".txt", ".csv"})


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252", errors="replace")
    except FileNotFoundError:
        return ""


def _rel(path: Path, root: Path = ROOT) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_text_files(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for folder in CODE_DIRS:
        base = root / folder
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                paths.append(path)
    return sorted(paths)


def find_occurrences(term: str, root: Path = ROOT) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    needle = term.lower()
    for path in iter_text_files(root):
        for line_no, line in enumerate(_read_text(path).splitlines(), start=1):
            if needle in line.lower():
                hits.append({"path": _rel(path, root), "line": line_no, "text": line.strip()})
    return hits


def available_market_tiers(root: Path = ROOT) -> list[str]:
    try:
        from football_prediction_v19.diagnostics.market_tier import MARKET_TIERS

        return list(MARKET_TIERS)
    except Exception:
        text = _read_text(root / "src/football_prediction_v19/diagnostics/market_tier.py")
        match = re.search(r"MARKET_TIERS\s*=\s*\((.*?)\)", text, re.S)
        return re.findall(r"[\"']([^\"']+)[\"']", match.group(1)) if match else []


def available_wf_model_choices(root: Path = ROOT) -> list[str]:
    text = _read_text(root / "scripts/run_season_replay_audit.py")
    match = re.search(
        r"add_argument\(\s*[\"']--wf-model[\"'].*?choices\s*=\s*\[(.*?)\]",
        text,
        re.S,
    )
    if not match:
        return []
    return re.findall(r"[\"']([^\"']+)[\"']", match.group(1))


def daily_report_ensemble_fields(root: Path = ROOT) -> dict[str, Any]:
    context_text = _read_text(root / "scripts/_context_signals.py")
    context_support = (
        "CONTEXT_CSV_KEYS" in context_text
        and "ensemble_agreement" in context_text
        and "ensemble_note" in context_text
    )

    report_headers: dict[str, list[str]] = {}
    for path in sorted((root / "outputs/daily_reports").glob("*_daily_report.csv")):
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                header = next(csv.reader(handle), [])
        except (OSError, StopIteration, UnicodeDecodeError):
            header = []
        if header:
            report_headers[_rel(path, root)] = header

    with_agreement = [
        name for name, header in report_headers.items() if "ensemble_agreement" in header
    ]
    with_note = [name for name, header in report_headers.items() if "ensemble_note" in header]
    with_predictions = [
        name for name, header in report_headers.items()
        if "ensemble_model_predictions" in header
    ]

    return {
        "context_helper_support": context_support,
        "reports_checked": len(report_headers),
        "reports_with_ensemble_agreement": with_agreement,
        "reports_with_ensemble_note": with_note,
        "reports_with_ensemble_model_predictions": with_predictions,
    }


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    all_code = "\n".join(_read_text(path) for path in iter_text_files(root))
    replay_text = _read_text(root / "scripts/run_season_replay_audit.py")
    market_text = _read_text(root / "src/football_prediction_v19/diagnostics/market_tier.py")
    ensemble_tier_text = _read_text(root / "src/football_prediction_v19/diagnostics/ensemble_tier.py")
    features_text = _read_text(root / "src/football_prediction_v19/features.py")

    market_tiers = available_market_tiers(root)
    wf_model_choices = available_wf_model_choices(root)
    daily_fields = daily_report_ensemble_fields(root)

    search_hits = {term: find_occurrences(term, root) for term in SEARCH_TERMS}

    run_supports_ensemble = all(
        token in replay_text
        for token in (
            '"ensemble"',
            "_serialise_ensemble_model_predictions",
            "compute_ensemble_agreement",
        )
    )
    prediction_serialization_supported = (
        "ensemble_model_predictions" in replay_text
        and "_serialise_ensemble_model_predictions" in replay_text
        and "X.attrs[\"ensemble_model_predictions\"]" in replay_text
    )
    ensemble_context = "\n".join(
        line for line in replay_text.splitlines()
        if "ensemble_agreement" in line
        or "ensemble_note" in line
        or "ensemble_model_predictions" in line
    )
    high_medium_low_supported = all(
        token in ensemble_context for token in ('"HIGH"', '"MEDIUM"', '"LOW"')
    ) or (
        "compute_ensemble_agreement" in replay_text
        and all(token in ensemble_tier_text for token in ('"HIGH"', '"MEDIUM"', '"LOW"', '"NONE"'))
    )

    return {
        "market_tiers": market_tiers,
        "wf_model_choices": wf_model_choices,
        "search_hits": search_hits,
        "super_a_tier": {
            "appears_in_code": "SUPER_A_TIER" in all_code,
            "in_market_tiers": "SUPER_A_TIER" in market_tiers,
            "produced_by_build_market_tier": "SUPER_A_TIER" in market_text,
            "produced_by_ensemble_override": 'market_tier = "SUPER_A_TIER"' in ensemble_tier_text,
        },
        "ensemble": {
            "predictor_file_exists": (root / "src/football_prediction_v19/models/ensemble.py").exists(),
            "ensemble_mode_appears": "EnsemblePredictor" in all_code,
            "run_season_replay_supports_ensemble": run_supports_ensemble,
            "cli_wf_model_has_ensemble_choice": "ensemble" in wf_model_choices,
            "prediction_serialization_supported": prediction_serialization_supported,
            "agreement_high_medium_low_supported": high_medium_low_supported,
            "numeric_agreement_supported": "agreement_score" in replay_text and "agreement == 1.0" in ensemble_tier_text,
        },
        "daily_reports": daily_fields,
        "phases": {
            "Phase 5": {
                "status": "ACTIVE",
                "evidence": [
                    "src/football_prediction_v19/features.py: OPTIONAL_FEATURES includes H2H, Elo, time-decay, adjusted xG, game-state fields.",
                    "src/football_prediction_v19/features.py: build_extended_features() wires include_h2h/include_time_decay/include_adj_xg/include_game_state.",
                    "scripts/run_season_replay_audit.py: replay calls build_extended_features() with Phase-5 flags enabled.",
                    "tests/test_phase5_features.py covers the feature builders.",
                ],
            },
            "Phase 6": {
                "status": "ACTIVE",
                "evidence": [
                    "src/football_prediction_v19/features.py: OPTIONAL_FEATURES includes referee, rest/fatigue, table context, derby/rivalry fields.",
                    "src/football_prediction_v19/features.py: build_extended_features(... include_context=True) adds context features.",
                    "scripts/run_season_replay_audit.py: replay calls build_extended_features() with include_context=True.",
                    "tests/test_phase6_context.py covers context feature generation.",
                ],
            },
            "Phase 7": {
                "status": "ACTIVE",
                "evidence": [
                    "scripts/run_season_replay_audit.py provides diagnostic_replay and walk_forward modes.",
                    "scripts/run_season_replay_audit.py writes prediction/evaluation CSV outputs under outputs/season_replay.",
                    "Existing tests and replay outputs exercise season replay and walk-forward paths.",
                ],
            },
            "Phase 8": {
                "status": "PARTIALLY ACTIVE",
                "evidence": [
                    "Feature-matrix optional-field integration is active via OPTIONAL_FEATURES and tests/test_phase8_feature_matrix.py.",
                    "The ensemble population fix is not fully active: replay output schema is backfilled, but ensemble_model_predictions is not serialized from real model predictions.",
                ],
            },
            "Phase 9": {
                "status": "ACTIVE",
                "evidence": [
                    "scripts/_context_signals.py exposes context_csv_fields() and compute_context_signal_analysis().",
                    "Daily report scripts import context helpers and include context fields in at least some report CSVs.",
                    "tests/test_phase9_daily_integration.py covers daily context output and evaluator summary sections.",
                ],
            },
            "Phase 10": {
                "status": "PARTIALLY ACTIVE",
                "evidence": [
                    "src/football_prediction_v19/models/ensemble.py defines EnsemblePredictor with LR/GB/RF soft-voting behavior.",
                    "src/football_prediction_v19/diagnostics/ensemble_tier.py can promote A_TIER to SUPER_A_TIER on full consensus.",
                    "scripts/run_season_replay_audit.py trains an ensemble in walk_forward and attempts apply_ensemble_override().",
                    "Missing wiring remains: SUPER_A_TIER is absent from MARKET_TIERS and daily reports do not compute ensemble predictions.",
                ],
            },
        },
    }


def generate_markdown(audit: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Phase Status Audit",
        "",
        "Diagnostic audit of current main-branch phase wiring. This report is static evidence only and does not change model, probability, market-tier, betting, ROI, or staking logic.",
        "",
        "## Phase Summary",
        "",
        "| Phase | Status | Evidence |",
        "| --- | --- | --- |",
    ]

    for phase, info in audit["phases"].items():
        evidence = "<br>".join(info["evidence"])
        lines.append(f"| {phase} | {info['status']} | {evidence} |")

    super_a = audit["super_a_tier"]
    ensemble = audit["ensemble"]
    daily = audit["daily_reports"]

    lines += [
        "",
        "## Phase 10 / Ensemble Findings",
        "",
        f"- SUPER_A_TIER appears in code: {super_a['appears_in_code']}.",
        f"- SUPER_A_TIER is in MARKET_TIERS: {super_a['in_market_tiers']}.",
        f"- build_market_tier() directly produces SUPER_A_TIER: {super_a['produced_by_build_market_tier']}.",
        f"- apply_ensemble_override() can produce SUPER_A_TIER: {super_a['produced_by_ensemble_override']}.",
        f"- True multi-model EnsemblePredictor file exists: {ensemble['predictor_file_exists']}.",
        f"- run_season_replay_audit.py supports ensemble inside walk_forward: {ensemble['run_season_replay_supports_ensemble']}.",
        f"- --wf-model exposes an ensemble choice: {ensemble['cli_wf_model_has_ensemble_choice']}.",
        f"- ensemble_model_predictions is serialized from real model outputs: {ensemble['prediction_serialization_supported']}.",
        f"- ensemble_agreement supports HIGH/MEDIUM/LOW labels: {ensemble['agreement_high_medium_low_supported']}.",
        f"- ensemble_agreement supports numeric consensus values: {ensemble['numeric_agreement_supported']}.",
        "",
        "Conclusion: Phase 10 is partially active. walk_forward exposes --wf-model ensemble, replay serializes readable per-model directions, and ensemble_agreement now uses HIGH/MEDIUM/LOW/NONE. Remaining gaps: SUPER_A_TIER is not a base MARKET_TIERS value and daily reports do not compute ensemble predictions.",
        "",
        "## SUPER_A_TIER Status",
        "",
        "SUPER_A_TIER is conditionally active only through the Phase-10 ensemble override. It is not part of the base MARKET_TIERS tuple and is not emitted by build_market_tier() itself. Consumers that validate against MARKET_TIERS will not see it as an available base tier.",
        "",
        "## True Multi-Model Ensemble Status",
        "",
        "A true three-model EnsemblePredictor exists. In the current wiring, walk_forward also has a selectable --wf-model ensemble mode that trains logistic_regression, random_forest, and gradient_boosting on the same strict prior_df and serializes their per-model directions. The daily report context helper still defaults ensemble fields to blanks rather than computing them.",
        "",
        "## Ensemble Agreement Status",
        "",
        "The current code standardizes ensemble_agreement to HIGH, MEDIUM, LOW, or NONE. Old CSV values remain readable through compatibility mapping: CONSENSUS -> HIGH, SPLIT -> MEDIUM, DISAGREEMENT -> LOW, and blanks/nan -> NONE. In --wf-model ensemble mode, ensemble_model_predictions is populated as readable per-model directions.",
        "",
        "## Missing Wiring / Dead Code / CLI Exposure",
        "",
        "- SUPER_A_TIER is absent from src/football_prediction_v19/diagnostics/market_tier.py::MARKET_TIERS.",
        "- apply_ensemble_override is not exported from src/football_prediction_v19/diagnostics/__init__.py.",
        "- scripts/run_season_replay_audit.py still passes ensemble_predictions={} into apply_ensemble_override(); the override path does not consume the serialized per-model prediction text.",
        "- ensemble_model_predictions is populated in --wf-model ensemble mode and remains blank for one-model mode.",
        "- Daily report context helpers include ensemble_agreement and ensemble_note defaults, but do not compute ensemble predictions.",
        "",
        "## Daily Report Ensemble Fields",
        "",
        f"- Context helper includes ensemble fields: {daily['context_helper_support']}.",
        f"- Daily report CSV headers checked: {daily['reports_checked']}.",
        f"- Reports with ensemble_agreement: {len(daily['reports_with_ensemble_agreement'])}.",
        f"- Reports with ensemble_note: {len(daily['reports_with_ensemble_note'])}.",
        f"- Reports with ensemble_model_predictions: {len(daily['reports_with_ensemble_model_predictions'])}.",
        "",
        "## Search Hit Counts",
        "",
        "| Term | Hits |",
        "| --- | ---: |",
    ]
    for term, hits in audit["search_hits"].items():
        lines.append(f"| `{term}` | {len(hits)} |")
    lines.append("")
    return "\n".join(lines)


def format_cli_summary(audit: dict[str, Any]) -> str:
    super_a = audit["super_a_tier"]
    ensemble = audit["ensemble"]
    daily = audit["daily_reports"]
    return "\n".join(
        [
            f"Available market tiers: {', '.join(audit['market_tiers'])}",
            f"Available wf-model choices: {', '.join(audit['wf_model_choices'])}",
            f"SUPER_A_TIER appears in code: {super_a['appears_in_code']}",
            f"SUPER_A_TIER in MARKET_TIERS: {super_a['in_market_tiers']}",
            f"Ensemble mode appears in code: {ensemble['ensemble_mode_appears']}",
            f"run_season_replay_audit supports ensemble mode: {ensemble['run_season_replay_supports_ensemble']}",
            f"daily reports include ensemble fields: {daily['context_helper_support']}",
            f"ensemble_model_predictions populated from predictions: {ensemble['prediction_serialization_supported']}",
            f"ensemble_agreement HIGH/MEDIUM/LOW supported: {ensemble['agreement_high_medium_low_supported']}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-path",
        default=str(ROOT / "outputs/diagnostics/phase_status_audit.md"),
        help="Markdown report path to write.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print diagnostics without writing the markdown report.",
    )
    args = parser.parse_args(argv)

    audit = build_audit(ROOT)
    if not args.no_write:
        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = ROOT / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(generate_markdown(audit), encoding="utf-8")
        print(f"Wrote report: {_rel(report_path)}")
    print(format_cli_summary(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
