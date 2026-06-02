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

## I. Safety Rules

No source CSV is modified in place. xG values are never inferred or invented. Empty xG placeholders do not increase confidence or recommendations. No betting, staking, ROI, probability, market-tier, or recommended-market logic changes are part of this workflow.

## J. What Still Does Not Happen Automatically

The model does not use manual xG yet. Manual xG is not automatically downloaded, scraped, inferred, joined into model features, or used to change recommendations.
