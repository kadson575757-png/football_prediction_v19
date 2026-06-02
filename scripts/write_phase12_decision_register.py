# -*- coding: utf-8 -*-
"""Write the Phase 12 foundation decision register."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = "phase12_decision_register.csv"
OUTPUT_MD = "phase12_decision_register.md"
FINAL_RECOMMENDATION = "PHASE_12_FOUNDATION_COMPLETE_AWAITING_PRODUCTION_XG_OR_REPORTING_LAYER"


PHASE_ROWS: list[dict[str, object]] = [
    {
        "phase_id": "12.1",
        "phase_name": "Data Contract Audit",
        "purpose": "Define required match input contracts and importer readiness baseline.",
        "key_outputs": "data_contracts.py; audit_data_contracts.py",
        "key_result": "Data quality summaries and importer readiness reporting established.",
        "final_decision": "KEEP_DATA_CONTRACT_FOUNDATION",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Clean data files and importer implementation inputs.",
    },
    {
        "phase_id": "12.2",
        "phase_name": "File Type Classification + Contract-Specific Validation",
        "purpose": "Classify CSVs by role and validate with type-specific contracts.",
        "key_outputs": "file type contract helpers; audit integration",
        "key_result": "Historical, fixture, odds, xG, template, and processed files separated.",
        "final_decision": "ACCEPT_FILE_TYPE_CONTRACTS",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Use file roles to prioritize repairs.",
    },
    {
        "phase_id": "12.3",
        "phase_name": "Data Contract Repair Plan",
        "purpose": "Create non-destructive repair planning and preview outputs.",
        "key_outputs": "plan_data_contract_repairs.py",
        "key_result": "Repair actions classified without modifying source data.",
        "final_decision": "KEEP_REPAIR_PLAN_DIAGNOSTICS",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Manual review for high-risk data issues.",
    },
    {
        "phase_id": "12.4",
        "phase_name": "Fixture Empty Policy",
        "purpose": "Treat intentionally empty upcoming fixture files as non-blocking placeholders.",
        "key_outputs": "fixture empty policy validation",
        "key_result": "Empty fixture placeholders are allowed when explicitly classified.",
        "final_decision": "KEEP_FIXTURE_EMPTY_PLACEHOLDER_POLICY",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Refresh real fixture files when needed.",
    },
    {
        "phase_id": "12.5",
        "phase_name": "UNKNOWN CSV Adapter Mapping",
        "purpose": "Map known unknown CSVs to intended adapter/readiness categories.",
        "key_outputs": "csv_adapter_mapping.py",
        "key_result": "Known adapter-style files are no longer treated as hard unknowns.",
        "final_decision": "ACCEPT_UNKNOWN_CSV_ADAPTER_MAPPING",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Implement actual adapters in later phases.",
    },
    {
        "phase_id": "12.6",
        "phase_name": "xG Enrichment Contract",
        "purpose": "Separate xG contract-ready files from production-ready xG sources.",
        "key_outputs": "xg_enrichment.py; audit_xg_enrichment_contracts.py",
        "key_result": "No production-ready xG source exists; ADD_MANUAL_XG_VALUES remains.",
        "final_decision": "KEEP_XG_CONTRACT_PRODUCTION_READINESS_DISTINCTION",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Provide real xG source or manual xG values.",
    },
    {
        "phase_id": "12.7",
        "phase_name": "Partial xG Source Attribution",
        "purpose": "Attribute partial xG issues to templates, placeholders, mapping gaps, or real nulls.",
        "key_outputs": "xg_partial_attribution.py; audit_partial_xg_sources.py",
        "key_result": "Real xG null values remain a manual-data blocker.",
        "final_decision": "KEEP_PARTIAL_XG_ATTRIBUTION",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Manual xG values or mapping work.",
    },
    {
        "phase_id": "12.8",
        "phase_name": "Empty xG Column Policy",
        "purpose": "Allow accepted empty xG placeholders while preventing model usability.",
        "key_outputs": "xg_policy.py; policy register",
        "key_result": "Empty xG placeholders are accepted as placeholders, not model signal.",
        "final_decision": "KEEP_EMPTY_XG_PLACEHOLDER_POLICY",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Filled production xG values.",
    },
    {
        "phase_id": "12.9",
        "phase_name": "Manual xG CSV Importer Skeleton",
        "purpose": "Add safe local manual xG CSV import preview foundation.",
        "key_outputs": "manual_xg_csv.py; import_manual_xg_csv.py",
        "key_result": "Importer skeleton validates local CSVs but does not enrich model inputs.",
        "final_decision": "KEEP_MANUAL_XG_IMPORTER_SKELETON",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Filled accepted production manual xG file.",
    },
    {
        "phase_id": "12.10",
        "phase_name": "Manual xG Join Preview",
        "purpose": "Preview exact-key joins between manual xG files and targets.",
        "key_outputs": "xg_join_preview.py; preview_manual_xg_join.py",
        "key_result": "Join preview works with exact date/home/away keys only.",
        "final_decision": "KEEP_MANUAL_XG_JOIN_PREVIEW",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Production xG file with matching target keys.",
    },
    {
        "phase_id": "12.11",
        "phase_name": "Manual xG Entry Template Generator",
        "purpose": "Generate fillable blank manual xG templates from fixture/history sources.",
        "key_outputs": "manual_xg_template_generator.py; generate_manual_xg_template.py",
        "key_result": "Templates can be generated with blank xG fields only.",
        "final_decision": "KEEP_MANUAL_XG_TEMPLATE_GENERATOR",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Manual filling from trusted source.",
    },
    {
        "phase_id": "12.12",
        "phase_name": "Filled Manual xG Acceptance Gate",
        "purpose": "Validate filled manual xG values and join coverage before production use.",
        "key_outputs": "manual_xg_acceptance.py; validate_filled_manual_xg.py",
        "key_result": "Blank templates rejected as template-only; no production xG accepted yet.",
        "final_decision": "KEEP_FILLED_MANUAL_XG_ACCEPTANCE_GATE",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Accepted non-demo production manual xG file.",
    },
    {
        "phase_id": "12.13",
        "phase_name": "Manual xG Acceptance Demo + Documentation",
        "purpose": "Demonstrate acceptance pipeline with fake DEMO_ONLY data.",
        "key_outputs": "data/examples demo files; demo_manual_xg_acceptance.py; manual_xg_workflow.md",
        "key_result": "Demo acceptance returns MANUAL_XG_ACCEPTED but never counts as production.",
        "final_decision": "KEEP_DEMO_AS_FAKE_DEMO_ONLY",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Real non-demo production xG data.",
    },
    {
        "phase_id": "12.14",
        "phase_name": "Manual xG Production Manifest + Acceptance Register",
        "purpose": "Declare, validate, and register future production manual xG entries.",
        "key_outputs": "manual_xg_manifest.py; audit_manual_xg_manifest.py; manifest template",
        "key_result": "Demo rows do not count; production placeholder is incomplete.",
        "final_decision": "KEEP_MANIFEST_CONTROL_FOR_PRODUCTION_XG",
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Populate manifest with real xG and target paths.",
    },
    {
        "phase_id": "12.15",
        "phase_name": "Decision Register / Foundation Closure",
        "purpose": "Close Phase 12 foundation layer with decisions, deferrals, and next work.",
        "key_outputs": "phase12_decision_register.csv; phase12_decision_register.md",
        "key_result": "Foundation complete; awaiting production xG or reporting layer.",
        "final_decision": FINAL_RECOMMENDATION,
        "production_data_created": "no",
        "model_logic_changed": "no",
        "next_dependency": "Production manual xG acceptance or Phase 13 reporting.",
    },
]


def build_register_table() -> pd.DataFrame:
    return pd.DataFrame(PHASE_ROWS)


def _table_markdown(df: pd.DataFrame) -> list[str]:
    cols = ["phase_id", "phase_name", "key_result", "final_decision", "model_logic_changed"]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        values = [str(row[col]).replace("|", ";") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(df: pd.DataFrame) -> str:
    lines = [
        "# Phase 12 Decision Register",
        "",
        "## A. Executive Summary",
        "- Phase 12 final status: COMPLETE_FOR_FOUNDATION_LAYER",
        "- Final recommendation:",
        "  - KEEP_DATA_CONTRACT_AND_IMPORTER_FOUNDATION",
        "  - KEEP_EMPTY_XG_PLACEHOLDER_POLICY",
        "  - DO_NOT_USE_XG_IN_MODEL_YET",
        "  - REQUIRE_ACCEPTED_PRODUCTION_MANUAL_XG_BEFORE_ENRICHMENT",
        "  - DO_NOT_CHANGE_PROBABILITY_OR_MARKET_LOGIC",
        "",
        "## B. Phase Timeline",
    ]
    lines += _table_markdown(df)
    lines += [
        "## C. Accepted Decisions",
        "- File type contracts are accepted.",
        "- Fixture empty placeholder policy is accepted.",
        "- UNKNOWN CSV adapter mapping is accepted.",
        "- xG contract and production-readiness distinction is accepted.",
        "- Empty xG placeholders are allowed but not usable for model.",
        "- Manual xG importer skeleton is accepted.",
        "- Manual xG join preview is accepted.",
        "- Filled manual xG acceptance gate is accepted.",
        "- Demo files are accepted as fake/demo only.",
        "- Manifest controls future production manual xG files.",
        "",
        "## D. Rejected / Deferred Changes",
        "- No xG values inferred or invented.",
        "- No real production xG file added.",
        "- No xG enrichment applied to model.",
        "- No xG-based confidence upgrades.",
        "- No recommended-market upgrades from xG.",
        "- No probability logic changes.",
        "- No market tier changes.",
        "- No betting/staking/ROI changes.",
        "- No SUPER_A_TIER activation.",
        "- No web/API scraping implemented.",
        "",
        "## E. Current Known State",
        "- No accepted production manual xG files.",
        "- Demo acceptance works but is fake/demo only.",
        "- Manual xG manifest has placeholder production row requiring real paths.",
        "- Real xG/data/repair recommendations remain ADD_MANUAL_XG_VALUES or equivalent.",
        "- Next real blocker: provide accepted non-demo production manual xG file.",
        "",
        "## F. Safety Checks",
        "- No source CSV modified by decision register.",
        "- No xG values invented/deleted/modified.",
        "- No model behavior changed.",
        "- No probability/recommended market/betting/staking/ROI changes.",
        "- No SUPER_A_TIER activation.",
        "",
        "## G. Next Recommended Work",
        "1. Add a real non-demo production manual xG CSV and target path to the manifest.",
        "2. Run filled manual xG acceptance gate.",
        "3. If accepted, implement a future enrichment preview phase.",
        "4. Alternatively start Phase 13 for Excel daily analysis output / reporting layer.",
        "",
        "## H. Phase 12 Final Recommendation",
        FINAL_RECOMMENDATION,
        "",
    ]
    return "\n".join(lines)


def run(output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (ROOT / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_register_table()
    markdown = build_markdown(table)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _table, markdown = run(output_dir=Path(args.output_dir))
    print(markdown.split("## H. Phase 12 Final Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
