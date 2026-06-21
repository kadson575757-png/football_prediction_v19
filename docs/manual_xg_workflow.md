# Manual xG Workflow

## A. Purpose

This document describes the safe manual xG workflow added in Phase 12. Manual xG support is currently diagnostic/foundation work only. The model does not use manual xG yet.

## B. Manual xG Workflow

The workflow is:

1. Generate a fillable template from fixture or history CSV files.
2. Fill `home_xg` and `away_xg` manually from a trusted external source outside this project.
3. Validate the filled file with the acceptance gate.
4. Preview exact-key joins against target fixture/history files.
5. Use future enrichment only after acceptance passes.

## C. Template Generation

Use `scripts/generate_manual_xg_template.py` to create blank manual-entry templates. Generated templates keep `home_xg` and `away_xg` empty by default.

## D. Filling xG Values Manually

xG values must be entered manually. xG values are never inferred or invented by this project. Missing values are not filled automatically.

## E. Acceptance Gate

Use `scripts/validate_filled_manual_xg.py` before treating a manual xG file as production-ready. Manual xG files must pass acceptance before future enrichment use.

## F. Join Preview

Use `scripts/preview_manual_xg_join.py` to verify exact date/home/away joins. The join logic does not fuzzy-match teams, infer swapped teams, or change source files.

## G. Demo Files

The files under `data/examples/` are fake demo files. Demo values are fake and not real xG. They exist only to prove that the acceptance pipeline works end-to-end.

## H. Production Manifest

Use `data/templates/manual_xg_manifest_template.csv` as the starting point for declaring future production manual xG files. A production entry must provide a real `xg_file_path`, a real `target_file_path`, `source_type=MANUAL_XG_CSV`, `data_role=PRODUCTION`, and `is_demo=false`.

Demo files do not count as production because they are marked `DEMO_ONLY` and `data_role=DEMO`. The manifest audit may evaluate demo entries for demonstration, but demo entries are never counted as accepted production manual xG.

Production manifest entries must pass the Phase 12.12 acceptance gate before any future enrichment use. Manual xG is still not used by the model until a later enrichment integration phase.

## I. Trusted xG Promotion Preview

Use `scripts/promote_trusted_xg_to_manifest.py` to run the trusted xG promotion preview flow: trusted xG source CSV -> fill preview -> acceptance gate -> manifest-entry preview.

The production manifest is not modified automatically. A promotion-ready preview still requires explicit user review before any future enrichment integration phase. Manual xG is still not used by the model.

## J. Trusted xG Source Intake

Place real trusted xG source CSVs in `data/trusted_xg_sources/`. Run `scripts/audit_trusted_xg_intake.py --write-command-list` to check schema validity, target compatibility, fill coverage, likely promotion readiness, and the next exact PowerShell commands.

Use the generated `outputs/diagnostics/trusted_xg_next_commands.ps1` as a reviewable command list for template generation, trusted-source fill preview, acceptance validation, and promotion preview. Files in `data/trusted_xg_sources/` are not consumed by the model directly; model xG use still waits for a future enrichment integration after accepted non-demo production manual xG exists.

## K. Trusted xG Source Import

Use `scripts/import_trusted_xg_source.py` when you have a trusted local export file or an explicit user-provided CSV/HTML source URL. Local export example:

```powershell
python scripts/import_trusted_xg_source.py --source "C:\path\to\trusted_xg_export.csv" --output-name trusted_xg_export.csv
```

Explicit URL example:

```powershell
python scripts/import_trusted_xg_source.py --source "https://example.com/trusted_xg_export.csv" --output-name trusted_xg_export.csv
```

There is no hidden scraping, no credentials/API-key flow, and no inferred xG values. Fetched raw files are stored separately under `data/trusted_xg_sources/raw/`; normalized trusted source CSVs are written under `data/trusted_xg_sources/`. After import, run `scripts/audit_trusted_xg_intake.py --write-command-list`.

Imported trusted xG files still do not affect model behavior until a future accepted enrichment integration is explicitly implemented.

## L. Understat Trusted xG Source

Use `scripts/import_understat_xg_source.py` when the trusted source is an Understat export. Local Understat export example:

```powershell
python scripts/import_understat_xg_source.py --source "C:\path\to\understat_xg_export.csv" --output-name understat_xg_export.csv
```

Explicit Understat URL example:

```powershell
python scripts/import_understat_xg_source.py --source "https://example.com/understat_xg_export.csv" --output-name understat_xg_export.csv
```

The Understat adapter accepts match-pair exports such as `date,home_team,away_team,home_xG,away_xG`, `date,home,away,hxg,axg`, and safely pairable long exports with `date,team,opponent,xG,xGA,venue`. It performs no hidden scraping, uses only explicit user-provided URLs, and never infers xG values.

After importing an Understat source, run:

```powershell
python scripts/audit_understat_xg_source.py
python scripts/audit_trusted_xg_intake.py --write-command-list
python scripts/show_trusted_xg_intake_commands.py
```

Understat imports still do not affect model behavior until a future accepted enrichment integration is explicitly implemented.

## M. Understat League/Season Fetch Pilot

Use `scripts/fetch_understat_xg_source.py` only when you explicitly want to fetch one Understat league/season page or one explicit Understat URL.

League/season example:

```powershell
python scripts/fetch_understat_xg_source.py --league Bundesliga --season 2024 --output-name understat_xg_bundesliga_2024.csv
```

Explicit URL example:

```powershell
python scripts/fetch_understat_xg_source.py --url "https://understat.com/league/Bundesliga/2024" --output-name understat_xg_custom.csv
```

After a fetch, run:

```powershell
python scripts/audit_understat_fetch.py
python scripts/audit_understat_xg_source.py
python scripts/audit_trusted_xg_intake.py --write-command-list
python scripts/show_trusted_xg_intake_commands.py
```

Fetched/imported xG files still do not affect model behavior until a future accepted enrichment integration is explicitly implemented.

## N. Understat Fetch Wrote Raw HTML But Found No Match Data

If `fetch_understat_xg_source.py` writes a raw HTML file but reports `UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED`, inspect the saved file without fetching anything:

```powershell
python scripts/inspect_understat_raw_fetch.py --raw-path data/trusted_xg_sources/raw/understat_league_Bundesliga_2024.html
```

Do not commit raw runtime HTML files from `data/trusted_xg_sources/raw/`. The runtime parser fallback is diagnostic only and does not infer xG values. If Understat changes its payload format and the fallback cannot find a parseable xG payload, local export import remains supported:

```powershell
python scripts/import_understat_xg_source.py --source "C:\path\to\understat_xg_export.csv" --output-name understat_xg_export.csv
```

## O. Understat Data Access Fallback

Direct Understat league-page HTML fetches may only return a base page with no embedded `datesData`, `teamsData`, or match payload. Phase 13.7 adds a controlled fallback resolver that can use an existing normalized source, a local Understat export, a saved raw payload/HTML file, an explicitly enabled optional provider, or an explicitly enabled fetch mode. It does not infer or invent xG values.

Preferred local export fallback:

```powershell
python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --source path/to/understat_export.csv --output-name understat_xg_bundesliga_2024.csv
```

Optional provider fallback, only if the optional package is installed and explicitly enabled:

```powershell
python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --allow-optional-provider --output-name understat_xg_bundesliga_2024.csv
```

Explicit fetch fallback, only when network access is explicitly requested:

```powershell
python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --allow-network --mode explicit_fetch --output-name understat_xg_bundesliga_2024.csv
```

After a successful resolve, run:

```powershell
python scripts/audit_understat_data_access.py
python scripts/audit_understat_xg_source.py
python scripts/audit_trusted_xg_intake.py --write-command-list
python scripts/show_trusted_xg_intake_commands.py
```

Do not commit raw runtime HTML or payload files from `data/trusted_xg_sources/raw/`. Imported xG files still do not affect model behavior until a future accepted enrichment integration is explicitly implemented.

## P. Optional Understat Provider Bootstrap

The optional Understat provider uses `soccerdata` only when you explicitly install and enable it. Check availability:

```powershell
python scripts/check_understat_optional_provider.py
```

Print the install command without installing:

```powershell
python scripts/bootstrap_understat_optional_provider.py
```

Explicit install:

```powershell
python scripts/bootstrap_understat_optional_provider.py --install
```

After installation, retry resolution:

```powershell
python scripts/resolve_understat_xg_source.py --league Bundesliga --season 2024 --allow-optional-provider --output-name understat_xg_bundesliga_2024.csv
```

`soccerdata` is optional. No xG values are inferred, and model behavior remains unchanged until a future accepted enrichment integration is explicitly implemented.

## Q. Understat Join Diagnostics and Alias Map

An Understat source can contain the same number of rows as a football-data target file and still match poorly when team names or match dates are represented differently. For example, 306 Understat rows can match only 90 target rows if exact `date + home_team + away_team` keys diverge.

Run the join diagnostics before accepting or promoting any low-coverage fill preview:

```powershell
python scripts/audit_understat_join_diagnostics.py --source data/trusted_xg_sources/understat_xg_bundesliga_2024.csv --target data/processed/football_data_D1_2024_clean.csv
```

Review the generated unmatched rows, same-date team alias candidates, and plus/minus one-day date candidates under `outputs/diagnostics/`. If aliases are needed, start from:

```powershell
data/templates/understat_team_alias_map_template.csv
```

Audit the alias map:

```powershell
python scripts/audit_understat_team_alias_map.py --alias-map data/templates/understat_team_alias_map_template.csv
```

Apply reviewed aliases only to a preview copy:

```powershell
python scripts/apply_understat_team_alias_preview.py --source data/trusted_xg_sources/understat_xg_bundesliga_2024.csv --alias-map data/templates/understat_team_alias_map_template.csv
```

Then rerun fill, validation, and promotion preview. There is no fuzzy auto-fill, no automatic alias application, and no xG values are inferred or invented.

## R. Understat Alias and Date Alignment Preview Workflow

When a reviewed Understat alias map exists, apply it only to a preview copy:

```powershell
python scripts/apply_understat_team_alias_preview.py --source data/trusted_xg_sources/understat_xg_bundesliga_2024.csv --alias-map data/trusted_xg_sources/understat_team_alias_map_bundesliga_2024.csv
```

If a reviewed fixture-date mismatch remains, start from:

```powershell
data/templates/understat_date_alignment_template.csv
```

Audit the date alignment map:

```powershell
python scripts/audit_understat_date_alignment_map.py --date-map data/trusted_xg_sources/understat_date_alignment_bundesliga_2024.csv
```

Apply accepted date alignments only to a preview copy:

```powershell
python scripts/apply_understat_date_alignment_preview.py --source outputs/xg_alias_preview/understat_xg_bundesliga_2024_understat_alias_preview.csv --date-map data/trusted_xg_sources/understat_date_alignment_bundesliga_2024.csv
```

For Bundesliga 2024, the reviewed date-alignment case is `FC St Pauli` vs `Holstein Kiel`: Understat source date `2024-11-30`, football-data target date `2024-11-29`. This is a reviewed date-key alignment only; no xG value is inferred or changed.

The local helper runs the full preview chain:

```powershell
python scripts/build_understat_bundesliga_2024_xg_acceptance_preview.py
```

The helper writes only under `outputs/`, leaves source and target CSVs unchanged, and writes a manifest-entry preview only. The production manifest remains review-only and is not modified automatically.

## S. Trusted xG Manifest Preview Hardening

Phase 13.11 hardens manifest-entry previews before any real production manifest edit. Data acceptance and manifest registration are separate checks: `TRUSTED_XG_PROMOTION_READY` means the data preview passed acceptance, while `manifest_registration_status` says whether the manifest row is safe to review.

Use a production-candidate manifest path instead of an `outputs/` file:

```powershell
data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv
```

Build the hardened Bundesliga 2024 manifest preview:

```powershell
python scripts/build_understat_bundesliga_2024_manifest_preview.py
```

The preview should use repo-relative paths such as:

```text
xg_file_path=data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv
target_file_path=data/processed/football_data_D1_2024_clean.csv
league=Bundesliga
season=2024
```

`outputs/` paths are runtime preview artifacts and must not become production manifest paths. Absolute local Windows paths are also unsafe for a shared production manifest because they are machine-specific. If no reviewed `manifest_xg_path`, league, or season is supplied, the manifest entry remains incomplete or preview-only.

This phase still does not materialize the accepted production xG CSV automatically and does not edit the production manifest. xG remains inactive in model features until a later explicit integration phase.

## T. Accepted Trusted xG Artifact Workflow

Phase 13.12 adds a guarded accepted-artifact step. The raw trusted source, preview outputs, accepted artifact, and production manifest are separate things:

- Raw trusted source: `data/trusted_xg_sources/understat_xg_bundesliga_2024.csv`
- Preview outputs: runtime files under `outputs/`
- Accepted artifact: reviewed CSV under `data/trusted_xg_sources/accepted/`
- Production manifest: still review-only and never edited automatically

Preview the accepted artifact materialization:

```powershell
python scripts/build_understat_bundesliga_2024_accepted_artifact_preview.py
```

Materialize only after full validation:

```powershell
python scripts/build_understat_bundesliga_2024_accepted_artifact_preview.py --write
```

The accepted artifact path is:

```text
data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv
```

The materializer rejects `outputs/` paths, unsafe absolute paths, missing xG values, invalid xG values, and low join coverage. It does not modify the raw source, target, model inputs, or production manifest. xG remains inactive in model features until a later explicit integration phase.

Audit accepted artifacts:

```powershell
python scripts/audit_accepted_trusted_xg_artifacts.py
```

## U. Accepted xG Manifest Registration

Phase 13.13 registers a reviewed accepted artifact in the manual xG manifest. Registration is metadata only: it records which accepted xG CSV belongs to which target match CSV, league, season, row count, and required join coverage.

The three production-facing layers remain separate:

- Raw trusted source: provider export kept under `data/trusted_xg_sources/`
- Accepted artifact: reviewed, fully accepted CSV under `data/trusted_xg_sources/accepted/`
- Manifest registration: repo-relative manifest row that points to the accepted artifact and target file

Dry-run the registration:

```powershell
python scripts/register_accepted_xg_manifest_entry.py
```

Write the reviewed Bundesliga 2024 entry only after the dry-run is clean:

```powershell
python scripts/register_accepted_xg_manifest_entry.py --write
```

Audit the registration:

```powershell
python scripts/audit_accepted_xg_manifest_registration.py
```

The reviewed entry is:

```text
manifest_id=trusted_xg_understat_bundesliga_2024_manual_xg
xg_file_path=data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv
target_file_path=data/processed/football_data_D1_2024_clean.csv
league=Bundesliga
season=2024
expected_rows=306
min_join_coverage_pct=100.0
```

The registration script rejects `outputs/` paths, absolute local Windows production paths, missing league/season metadata, missing artifacts, row-count mismatches, and join coverage below the manifest requirement. It does not modify the raw Understat source, target match CSV, accepted artifact values, or model inputs.

Registered xG is accepted data only. A future explicit integration phase is still required before xG can influence model features, predictions, probabilities, market tiers, or recommendations.

## V. Manifest-Backed xG Enrichment Preview

Phase 13.14 builds a manifest-backed enrichment preview. It reads accepted production manifest entries, joins the accepted xG artifact to the registered target file by exact date/home/away keys, and writes a preview CSV only under `outputs/xg_enrichment_preview/`.

Build the generic manifest-backed preview:

```powershell
python scripts/build_manifest_xg_enrichment_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit the reviewed Bundesliga 2024 preview:

```powershell
python scripts/build_understat_bundesliga_2024_manifest_xg_enrichment_preview.py
```

Audit preview files:

```powershell
python scripts/audit_manifest_xg_enrichment_preview.py
```

The layers remain separate:

- Accepted artifact: `data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv`
- Production target: `data/processed/football_data_D1_2024_clean.csv`
- Enriched preview: runtime CSV under `outputs/xg_enrichment_preview/`

The enriched preview is not a model input yet. It is a review artifact proving the manifest-backed join can preserve target identity columns and add accepted `home_xg`/`away_xg` without editing the target file. A future explicit integration phase is required before xG can influence predictions, probabilities, market tiers, or recommendations.

## W. Manifest-backed xG Readiness Audit

Phase 13.15 adds a readiness audit for the full reviewed chain:

```text
raw trusted source -> accepted artifact -> manifest registration -> enrichment preview
```

Run the generic readiness audit:

```powershell
python scripts/audit_manifest_xg_readiness.py
```

Run the Bundesliga 2024 readiness report:

```powershell
python scripts/build_understat_bundesliga_2024_xg_readiness_report.py
```

Readiness means the accepted artifact is registered, repo-relative, present under `data/trusted_xg_sources/accepted/`, joins to the registered target with the required coverage, and can be used for reporting/diagnostic previews. The model integration status remains:

```text
XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN
```

This creates a separate distinction:

- Production target lacks xG values: the target CSV is intentionally not modified in place.
- Accepted artifact registered in manifest: reviewed xG data exists outside the target CSV.
- Manifest-backed enrichment preview ready: reporting/diagnostic preview can be built under `outputs/`.
- xG model integration not active by design: xG still cannot influence predictions or markets.

Because of this separation, `scripts/audit_xg_enrichment_contracts.py` and `scripts/audit_data_contracts.py` may still return `ADD_MANUAL_XG_VALUES`. Those scripts audit production target files themselves, not the manifest-backed reporting preview chain.

xG can now be used for reporting and diagnostic previews only. A later explicit integration phase is required before xG can influence model features, predictions, probabilities, market tiers, or recommendations.

## X. xG Reporting Preview Layer

Phase 13.16 builds a reporting-only match-level xG preview from the ready manifest-backed enrichment chain. It adds reporting columns such as `xg_total`, `xg_diff_home`, `xg_result_label`, `actual_result_label`, and `xg_result_matches_actual` to a runtime CSV under `outputs/xg_reporting_preview/`.

Build the generic reporting preview:

```powershell
python scripts/build_xg_reporting_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit the Bundesliga 2024 reporting preview:

```powershell
python scripts/build_understat_bundesliga_2024_xg_reporting_preview.py
```

Audit reporting previews:

```powershell
python scripts/audit_xg_reporting_preview.py
```

This layer can support diagnostics and reporting only. It does not make xG a model feature, does not change predictions or probabilities, and does not affect market ranking, staking, ROI, or `SUPER_A_TIER`.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` while manifest readiness and reporting preview are ready. That is expected because the legacy audits inspect whether production target CSV files themselves contain xG values, while Phase 13.16 writes a separate runtime reporting preview and intentionally leaves production targets untouched.

A future explicit integration phase is required before xG can influence predictions, probabilities, market ranking, staking, or ROI logic.

## Y. Team-level xG Reporting Aggregates

Phase 13.17 builds team-level reporting aggregates from the match-level xG reporting preview. It produces one row per team with goals for/against, xG for/against, goal and xG differences, points, and home/away splits.

Build generic team aggregates:

```powershell
python scripts/build_team_xg_reporting_aggregates.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit Bundesliga 2024 team aggregates:

```powershell
python scripts/build_understat_bundesliga_2024_team_xg_reporting_aggregates.py
```

Audit team aggregate previews:

```powershell
python scripts/audit_team_xg_reporting_aggregates.py
```

These outputs are reporting/diagnostic previews only. They can support human analysis of team xG profiles, but they cannot influence model predictions, probabilities, market ranking, staking, or ROI logic until a later explicit integration phase.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` while manifest readiness, reporting previews, and team aggregate previews are ready. That remains expected because production target CSVs are intentionally not modified in place.

## Z. Rolling xG Form Reporting

Phase 13.18 builds rolling pre-match xG form previews from the match-level xG reporting preview. It creates two team-match rows per match and computes rolling xG, goals, goal difference, points, and over/under-performance values from matches before the current match only.

Build generic rolling form:

```powershell
python scripts/build_rolling_xg_form_reporting.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit Bundesliga 2024 rolling form:

```powershell
python scripts/build_understat_bundesliga_2024_rolling_xg_form_reporting.py
```

Audit rolling form previews:

```powershell
python scripts/audit_rolling_xg_form_reporting.py
```

Rolling form deliberately avoids current-match leakage: each row's rolling values use only that team's prior matches within the configured window. These outputs can support human reporting and diagnostics, but they cannot influence model predictions, probabilities, market ranking, staking, or ROI logic until a later explicit integration phase.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` while manifest readiness, reporting, aggregate, and rolling previews are ready. That remains expected because production target CSVs are intentionally not modified in place.

## AA. xG Matchup Reporting Preview

Phase 13.19 builds match-level matchup reporting previews by joining the accepted match-level xG reporting preview with pre-match rolling xG form for the home and away teams. It writes runtime CSVs under `outputs/xg_reporting_preview/` and leaves source, target, accepted artifact, and manifest files unchanged.

Build the generic matchup preview:

```powershell
python scripts/build_xg_matchup_reporting_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit Bundesliga 2024 matchup reporting:

```powershell
python scripts/build_understat_bundesliga_2024_xg_matchup_reporting_preview.py
```

Audit matchup previews:

```powershell
python scripts/audit_xg_matchup_reporting_preview.py
```

The matchup preview deliberately uses pre-match rolling context only. Current-match `home_xg` and `away_xg` remain reporting columns, while rolling matchup values come from each team's prior matches within the configured window.

These outputs are diagnostic/reporting previews only. They cannot influence model features, predictions, probabilities, market ranking, staking, ROI, or `SUPER_A_TIER` until a later explicit integration phase.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` while manifest readiness, reporting, aggregate, rolling, and matchup previews are ready. That remains expected because production target CSVs are intentionally not modified in place.

## AB. xG Reporting Pack Preview

Phase 13.20 builds a reporting pack preview that bundles the ready reporting-only xG layers into a single index and markdown summary:

- match-level xG reporting preview
- team xG reporting aggregates
- rolling xG form reporting
- xG matchup reporting preview

Build the generic reporting pack:

```powershell
python scripts/build_xg_reporting_pack_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit the Bundesliga 2024 reporting pack:

```powershell
python scripts/build_understat_bundesliga_2024_xg_reporting_pack_preview.py
```

Audit reporting pack previews:

```powershell
python scripts/audit_xg_reporting_pack_preview.py
```

The pack writes only runtime artifacts under `outputs/xg_reporting_preview/`, including `xg_reporting_pack_index.csv` and `xg_reporting_pack_summary.md`. It does not modify the production target CSV, accepted xG artifact, raw Understat source, or production manifest.

The reporting pack is for diagnostics and human review only. xG is still not a model feature and cannot influence predictions, probabilities, market ranking, staking, ROI, or `SUPER_A_TIER` until a later explicit integration phase.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` while manifest readiness and the reporting pack are ready. That remains expected because legacy audits inspect whether production target CSV files themselves contain xG values, while the reporting pack intentionally uses separate runtime preview artifacts.

## AC. xG Reporting Layer Closure Audit

Phase 13.21 closes the reporting-only xG layer for human diagnostics. The closure audit confirms that the accepted artifact, production manifest registration, enrichment preview, manifest readiness audit, match-level reporting preview, team aggregates, rolling form, matchup preview, and reporting pack are all available as runtime preview/reporting artifacts.

Run the generic closure audit:

```powershell
python scripts/audit_xg_reporting_layer_closure.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg
```

Run the Bundesliga 2024 closure helper:

```powershell
python scripts/build_understat_bundesliga_2024_xg_reporting_layer_closure.py
```

The expected closure status is:

```text
XG_REPORTING_LAYER_COMPLETE
```

This means xG reporting is ready for human diagnostics and review only. It does not activate xG as a model feature, does not change predictions or probabilities, does not change market ranking or recommended market logic, and does not affect betting, staking, ROI, stake sizing, or `SUPER_A_TIER`.

Legacy audits may still say `ADD_MANUAL_XG_VALUES` because production target CSVs are intentionally not modified in place. The closure audit records that as acceptable and non-blocking for the reporting layer.

Any future xG model integration requires a separate explicit phase with stronger validation, leakage checks, replay impact analysis, and safety review before xG can influence model behavior.

## AD. Analysis Export Bundle Preview

Phase 14.1 builds a human-analysis export bundle from the ready xG reporting layer. It copies normalized runtime preview CSVs into:

```text
outputs/analysis_export_preview/<manifest_id>/
```

The bundle includes match-level xG reporting, team xG aggregates, rolling xG form, matchup reporting, the reporting pack index, and the closure summary when available. It also writes `analysis_export_bundle_index.csv` and `analysis_export_bundle_summary.md`.

Build the generic export bundle:

```powershell
python scripts/build_analysis_export_bundle_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit the Bundesliga 2024 export bundle:

```powershell
python scripts/build_understat_bundesliga_2024_analysis_export_bundle_preview.py
```

Audit export bundles:

```powershell
python scripts/audit_analysis_export_bundle_preview.py
```

This layer is designed for manual review, spreadsheet analysis, and future Excel/dashboard workflows. It does not modify production target CSVs, accepted xG artifacts, raw trusted sources, or the production manifest.

xG remains inactive in model predictions, probabilities, market ranking, recommended market logic, staking, ROI, stake sizing, and `SUPER_A_TIER`. Any future xG model integration requires a separate explicit phase with stronger validation and impact analysis.

## AE. Analysis Excel Workbook Preview

Phase 14.2 converts the Phase 14.1 analysis export bundle into a human-friendly Excel workbook preview:

```text
outputs/analysis_export_preview/<manifest_id>/analysis_export_workbook_preview.xlsx
```

Build the generic workbook preview:

```powershell
python scripts/build_analysis_excel_workbook_preview.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg --write-preview
```

Build and audit the Bundesliga 2024 workbook preview:

```powershell
python scripts/build_understat_bundesliga_2024_analysis_excel_workbook_preview.py
```

Audit workbook previews:

```powershell
python scripts/audit_analysis_excel_workbook_preview.py
```

The workbook contains README, bundle index, match-level, team aggregate, rolling form, matchup, reporting pack, and closure-summary sheets when available. It is intended for manual review, dashboard prototyping, and future analysis workflows.

The workbook is a runtime preview artifact and should not be committed. It does not modify production target CSVs, accepted xG artifacts, raw trusted sources, or the production manifest.

xG remains inactive in model predictions, probabilities, market ranking, recommended market logic, staking, ROI, stake sizing, and `SUPER_A_TIER`. Any future xG model integration requires a separate explicit phase with stronger validation and impact analysis.

## AF. Analysis Export Layer Closure

Phase 14.3 closes the analysis export usability layer for human analysis. The closure audit confirms that the analysis export bundle, Excel workbook preview, xG reporting layer closure, reporting pack, and manifest readiness are available and consistent.

Run the generic export-layer closure audit:

```powershell
python scripts/audit_analysis_export_layer_closure.py --manifest-id trusted_xg_understat_bundesliga_2024_manual_xg
```

Run the Bundesliga 2024 export-layer closure helper:

```powershell
python scripts/build_understat_bundesliga_2024_analysis_export_layer_closure.py
```

The expected closure status is:

```text
ANALYSIS_EXPORT_LAYER_COMPLETE
```

This means the export layer is complete for human analysis usage: CSV export bundle, Excel workbook preview, and xG reporting closure are ready as runtime artifacts.

This does not include model feature activation, prediction changes, probability changes, market ranking changes, recommended-market changes, betting, staking, ROI, stake sizing, or `SUPER_A_TIER` changes.

Any future xG model integration requires a separate explicit phase with stronger validation, leakage checks, replay impact analysis, and safety review before xG can influence model behavior.

## AG. Importer Source Registry Preview

Phase 15.1 starts real importer/API/scraper preparation safely by defining a preview registry of planned external sources such as FBref, Understat, FotMob, SofaScore, WhoScored, and soccerdata.

Build the importer source registry preview:

```powershell
python scripts/build_importer_source_registry_preview_helper.py
```

Audit the importer source registry preview:

```powershell
python scripts/audit_importer_source_registry_preview.py
```

This phase does not make live network calls, does not scrape websites, and does not fetch provider data. It only records future adapter capabilities, schema-contract status, and implementation status. Future phases should implement one source adapter at a time with explicit tests and safety checks.

Importer work is separate from xG model integration. Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AH. Canonical Importer Schema Contracts Preview

Phase 15.2 defines canonical schema contracts for future scraper/API/provider adapters. It registers preview contracts for match rows, team match stats, player match stats, fixtures, lineups, odds snapshots, and xG source rows.

Build the schema contracts preview:

```powershell
python scripts/build_importer_schema_contracts_preview_helper.py
```

Audit the schema contracts preview:

```powershell
python scripts/audit_importer_schema_contracts_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, import provider data, or infer values. It only defines the target fields, validation rules, source support, and adapter-pending status for future implementations.

Future phases should implement one adapter at a time against these contracts. Importer outputs must stay separate from model integration until a later explicit phase with stronger validation, leakage checks, replay impact analysis, and safety review.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AI. Importer Adapter Interface Preview

Phase 15.3 introduces the adapter interface and base contract for future importer providers. It defines adapter config, run context, preview result objects, and a base adapter that can validate configuration and schema-contract support without fetching or normalizing provider data.

Build the adapter interface preview:

```powershell
python scripts/build_importer_adapter_interface_preview_helper.py
```

Audit the adapter interface preview:

```powershell
python scripts/audit_importer_adapter_interface_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, import provider data, or infer values. Preview adapters report zero normalized rows by design and only prove that source registry rows can be represented as adapter configurations against the canonical contracts.

Future phases should implement one provider adapter at a time. Importer outputs must stay separate from model integration until a later explicit phase with stronger validation, leakage checks, replay impact analysis, and safety review.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AJ. File-Based Importer Dry Run Preview

Phase 15.4 validates local CSV files against canonical importer contracts such as `canonical_match`, `canonical_fixture`, and `canonical_xg_source`.

Build the file-based importer dry-run preview:

```powershell
python scripts/build_file_based_importer_dry_run_preview_helper.py
```

Audit the file-based importer dry-run preview:

```powershell
python scripts/audit_file_based_importer_dry_run_preview.py
```

This phase reads local files only. It does not scrape websites, call provider APIs, fetch external data, infer missing values, or modify target CSVs in place. When preview output is requested, normalized CSVs are written only under `outputs/importer_preview/normalized/`.

This is the bridge toward analysis-ready input bundles. Future phases can implement one provider adapter at a time or build local imported-data bundles from validated files. Importer outputs remain separate from model integration until a later explicit phase.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AK. Analysis Input Bundle Preview

Phase 16.1 converts local importer preview output into an analysis-ready input bundle. The default input is the normalized `canonical_match` preview from `outputs/importer_preview/normalized/canonical_match_preview.csv`.

Build the analysis input bundle preview:

```powershell
python scripts/build_analysis_input_bundle_preview_helper.py
```

Audit the analysis input bundle preview:

```powershell
python scripts/audit_analysis_input_bundle_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or run betting/staking logic. Missing values are not inferred or invented, and importer outputs remain separate from model integration until a later explicit phase.

This is the final bridge before single-match analysis report generation. Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AL. Single Match Analysis Report Preview

Phase 16.2 creates the first preview-only single-match analysis report from the local analysis input bundle.

Build the single-match report preview:

```powershell
python scripts/build_single_match_analysis_report_preview_helper.py
```

Audit the single-match report preview:

```powershell
python scripts/audit_single_match_analysis_report_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations. It is the first analysis-facing preview layer and uses only the local analysis input bundle.

Future phases can enrich the report with xG reporting packs, team aggregates, rolling form, and matchup context. Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AM. Single Match Analysis Context Enrichment Preview

Phase 16.3 enriches the preview-only single-match report with available local context layers. Optional xG, team aggregate, rolling form, and matchup context may be missing; missing optional context is reported as a warning and is not inferred or invented.

Build the context enrichment preview:

```powershell
python scripts/build_single_match_context_enrichment_preview_helper.py
```

Audit the context enrichment preview:

```powershell
python scripts/audit_single_match_context_enrichment_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations. Future phases can connect enriched report context to richer human-facing analysis templates.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AN. Human-Facing Single Match Analysis Report Preview

Phase 16.4 converts enriched local preview context into the first human-readable match analysis report preview. Optional xG, team aggregate, rolling form, and matchup context may be missing; missing optional context is reported and is not inferred.

Build the human-facing report preview:

```powershell
python scripts/build_human_match_analysis_report_preview_helper.py
```

Audit the human-facing report preview:

```powershell
python scripts/audit_human_match_analysis_report_preview.py
```

This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations. It is the first human-facing analysis preview layer.

Future phases can enrich the report with real provider adapters, richer xG context, and eventually controlled prediction integration. Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AO. End-to-End Human Match Analysis Pipeline Preview

Phase 16.5 adds a one-command local preview runner. It runs the file importer dry run, analysis input bundle, single-match report, context enrichment, and human-facing report in order.

Run the end-to-end preview:

```powershell
python scripts/build_human_match_pipeline_preview_helper.py
```

Audit the end-to-end preview:

```powershell
python scripts/audit_human_match_pipeline_preview.py
```

This is now the usable local preview pipeline for human review. It does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations.

Future phases can add richer real provider adapters and controlled model integration separately. Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AP. Human Match Analysis Preview Layer Closure Audit

Phase 16.6 confirms that the local human match analysis preview pipeline is complete and ready for human review workflows.

Run the full closure helper:

```powershell
python scripts/build_human_analysis_preview_layer_closure_helper.py
```

Audit the closure status directly:

```powershell
python scripts/audit_human_analysis_preview_layer_closure.py
```

The one-command preview path is: file-based importer -> analysis input bundle -> single match report -> context enrichment -> human-facing report -> closure audit.

This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations. Future phases can add real provider adapters, richer data coverage, and controlled model integration separately.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AQ. Safety Rules

No source CSV is modified in place. xG values are never inferred or invented. Empty xG placeholders do not increase confidence or recommendations. No betting, staking, ROI, probability, market-tier, or recommended-market logic changes are part of this workflow.

## AR. What Still Does Not Happen Automatically

The model does not use manual xG yet. Manual xG is not automatically downloaded, scraped, inferred, joined into model features, or used to change recommendations.

## AS. Manual Human Match Input Pack Preview

Phase 17.1 adds a local CSV template and example for human-provided match inputs. It is a preview-only input pack for the existing human match analysis preview pipeline.

Build the manual input pack preview:

```powershell
python scripts/build_manual_human_match_input_pack_preview_helper.py
```

Validate a local manual input CSV:

```powershell
python scripts/validate_manual_human_match_input.py --input outputs/analysis_preview/manual_input/manual_human_match_input_example.csv
```

Run the human match pipeline from a manual input CSV:

```powershell
python scripts/build_human_match_pipeline_from_manual_input_preview.py --input outputs/analysis_preview/manual_input/manual_human_match_input_example.csv
```

Audit the manual input pack preview:

```powershell
python scripts/audit_manual_human_match_input_pack_preview.py
```

Required match identity fields must be filled by the user. Optional context fields may remain empty and are never inferred or invented. This phase does not make live network calls, scrape websites, fetch API data, run model predictions, or generate betting/staking recommendations.

Model predictions, probabilities, market ranking, recommended-market logic, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` remain unchanged.

## AT. Controlled Understat xG Provider Pull Preview

Phase 18.1 introduces the first automatic provider pull layer. Understat is supported in controlled preview mode because xG and xGA are central analysis inputs, but network access is disabled by default.

Build the offline Understat provider pull preview from the local fixture:

```powershell
python scripts/build_understat_provider_pull_preview_helper.py
```

Audit the provider pull preview:

```powershell
python scripts/audit_understat_provider_pull_preview.py
```

Bridge normalized Understat preview output into the manual human match input pipeline:

```powershell
python scripts/build_manual_input_from_understat_provider_pull_preview.py
```

Real provider pulling requires an explicit `--allow-network` flag. Tests and helper paths use only local fixtures and make no live provider calls. Raw snapshots are stored under `outputs/provider_pull_preview/understat/raw`, normalized preview output under `outputs/provider_pull_preview/understat/normalized`, and manifests under `outputs/provider_pull_preview/understat`.

The provider output can be converted into the manual human match input CSV format for the existing human analysis preview pipeline. Missing values are preserved and surfaced; they are not inferred or invented.

This phase does not activate xG as production model features, run model predictions, or generate betting/staking recommendations. Production model, probability, market-tier, recommended-market, betting, staking, ROI, stake sizing, and `SUPER_A_TIER` logic remain unchanged.
