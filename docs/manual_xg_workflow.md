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

## M. Safety Rules

No source CSV is modified in place. xG values are never inferred or invented. Empty xG placeholders do not increase confidence or recommendations. No betting, staking, ROI, probability, market-tier, or recommended-market logic changes are part of this workflow.

## N. What Still Does Not Happen Automatically

The model does not use manual xG yet. Manual xG is not automatically downloaded, scraped, inferred, joined into model features, or used to change recommendations.
