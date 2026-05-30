# -*- coding: utf-8 -*-
"""Write the Phase 11 final decision register.

Reporting only. This script does not change market-tier rules, probability
logic, recommended-market logic, betting, staking, ROI, or SUPER_A_TIER
activation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_MD = "phase11_decision_register.md"
OUTPUT_CSV = "phase11_decision_register.csv"

FINAL_RECOMMENDATIONS = (
    "KEEP_PHASE_11_3_DEFENSIVE_RULES",
    "DO_NOT_RELAX_LIGUE1",
    "DO_NOT_ACTIVATE_SUPER_A_TIER",
    "DO_NOT_ADD_PROMOTION_RULES_YET",
)

PHASE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "phase_id": "11.1",
        "phase_name": "Phase 11.1 Clean Evidence Cohort",
        "purpose": "Separate modern tier evidence from old UNKNOWN/non-ensemble rows.",
        "output_script": "scripts/analyze_tier_rule_candidates.py",
        "key_result": "Default decision scope uses modern-tier rows.",
        "final_decision": "Use clean cohort for Phase 11 decisions.",
        "rule_changes_made": "no",
    },
    {
        "phase_id": "11.2",
        "phase_name": "Phase 11.2 Candidate Stability Validation",
        "purpose": "Validate candidate rule signals across leagues and stability dimensions.",
        "output_script": "scripts/analyze_tier_rule_candidates.py --stability-report",
        "key_result": "Stable defensive no-go signals identified.",
        "final_decision": "Investigate defensive downgrade patch only.",
        "rule_changes_made": "no",
    },
    {
        "phase_id": "11.3",
        "phase_name": "Phase 11.3 Defensive Tier Rule Patch",
        "purpose": "Apply narrow defensive DOWNGRADE-to-HARD_NO_GO rules.",
        "output_script": "src/football_prediction_v19/diagnostics/market_tier.py",
        "key_result": "Low control, medium favorite, and late season DOWNGRADE rows moved to HARD_NO_GO.",
        "final_decision": "Accepted and keep as-is.",
        "rule_changes_made": "yes",
    },
    {
        "phase_id": "11.4",
        "phase_name": "Phase 11.4 Post-11.3 Impact Audit",
        "purpose": "Measure global impact and defensive integrity after Phase 11.3.",
        "output_script": "scripts/audit_phase11_3_impact.py",
        "key_result": "Impacted rows 281/4518 (6.2%), impacted success 61.6%, no A/B impact.",
        "final_decision": "Keep Phase 11.3 defensive rules.",
        "rule_changes_made": "no",
    },
    {
        "phase_id": "11.5",
        "phase_name": "Phase 11.5 Ligue 1 Relaxation Investigation",
        "purpose": "Investigate whether Ligue 1 HARD_NO_GO outlier comes from Phase 11.3.",
        "output_script": "scripts/audit_ligue1_defensive_relaxation.py",
        "key_result": "Ligue 1 Phase 11.3 impacted rows were not the direct cause.",
        "final_decision": "Continue source attribution before any relaxation.",
        "rule_changes_made": "no",
    },
    {
        "phase_id": "11.6",
        "phase_name": "Phase 11.6 HARD_NO_GO Source Attribution",
        "purpose": "Attribute HARD_NO_GO rows to reason/source categories.",
        "output_script": "scripts/audit_hard_no_go_source_attribution.py",
        "key_result": "Ligue 1 source candidates found for BOTH_OVER25_BTTS, SUPPRESSED_WITH_WARNING, LEAGUE_PROFILE_SUPPRESSION.",
        "final_decision": "Simulate source relaxation before changing rules.",
        "rule_changes_made": "no",
    },
    {
        "phase_id": "11.7",
        "phase_name": "Phase 11.7 Ligue 1 Relaxation Simulation",
        "purpose": "Simulate relaxing selected Ligue 1 HARD_NO_GO source rows in memory.",
        "output_script": "scripts/simulate_ligue1_source_relaxation.py",
        "key_result": "Recommendation DO_NOT_RELAX; defensive separation fails safety criteria.",
        "final_decision": "Do not relax Ligue 1 sources.",
        "rule_changes_made": "no",
    },
)


def build_register_table() -> pd.DataFrame:
    return pd.DataFrame(PHASE_ROWS)


def _markdown_table(df: pd.DataFrame) -> list[str]:
    cols = [
        "phase_id",
        "phase_name",
        "purpose",
        "output_script",
        "key_result",
        "final_decision",
        "rule_changes_made",
    ]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Phase 11 Decision Register",
        "",
        "Reporting only. No tier rules were changed by this register.",
        "",
        "## A. Executive Summary",
        "- Phase 11 final status: COMPLETE_FOR_CURRENT_EVIDENCE_CYCLE",
        "- Final recommendation:",
    ]
    lines += [f"  - {item}" for item in FINAL_RECOMMENDATIONS]
    lines += [
        "",
        "## B. Phase Timeline",
    ]
    lines += _markdown_table(df)
    lines += [
        "## C. Final Accepted Changes",
        "- Phase 11.3 defensive rules remain accepted.",
        "- DOWNGRADE + low control -> HARD_NO_GO.",
        "- DOWNGRADE + medium_fav -> HARD_NO_GO.",
        "- DOWNGRADE + late season -> HARD_NO_GO.",
        "- HARD_NO_GO confirmations for low control and medium_fav remain accepted.",
        "",
        "## D. Rejected / Deferred Changes",
        "- No SUPER_A_TIER activation.",
        "- No global promotion rules.",
        "- No Ligue 1 source relaxation.",
        "- No relaxation for BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO.",
        "- No relaxation for SUPPRESSED_WITH_WARNING.",
        "- No relaxation for LEAGUE_PROFILE_SUPPRESSION.",
        "",
        "## E. Evidence Summary",
        "- Phase 11.4 impacted rows: 281 / 4518 = 6.2%.",
        "- Phase 11.4 impacted success rate: 61.6%.",
        "- Phase 11.4 non-impacted success rate: 73.3%.",
        "- Phase 11.4 integrity: no A_TIER/B_TIER impacted, no SUPER_A_TIER.",
        "- Phase 11.6 Ligue 1 source candidates:",
        "  - BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO.",
        "  - SUPPRESSED_WITH_WARNING.",
        "  - LEAGUE_PROFILE_SUPPRESSION.",
        "- Phase 11.7 final recommendation: DO_NOT_RELAX.",
        "",
        "## F. Safety Checks",
        "- No probability logic changed.",
        "- No recommended market logic changed.",
        "- No betting/staking/ROI logic changed.",
        "- SUPER_A_TIER remains inactive.",
        "- Promotion rules were not activated.",
        "",
        "## G. Next Recommended Work",
        "- Phase 12 should focus on broader league profile calibration or importer/data quality, not more Phase 11 rule changes.",
        "- Any future promotion logic requires a separate simulation and impact audit.",
        "",
    ]
    return "\n".join(lines)


def run(output_dir: Path) -> tuple[pd.DataFrame, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_register_table()
    markdown = build_markdown(df)
    df.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return df, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    df, _markdown = run(Path(args.output_dir))
    print(f"Wrote {len(df)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print("KEEP_PHASE_11_3_DEFENSIVE_RULES | DO_NOT_RELAX_LIGUE1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
