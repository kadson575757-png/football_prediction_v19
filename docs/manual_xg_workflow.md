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

## T. Safety Rules

No source CSV is modified in place. xG values are never inferred or invented. Empty xG placeholders do not increase confidence or recommendations. No betting, staking, ROI, probability, market-tier, or recommended-market logic changes are part of this workflow.

## U. What Still Does Not Happen Automatically

The model does not use manual xG yet. Manual xG is not automatically downloaded, scraped, inferred, joined into model features, or used to change recommendations.
