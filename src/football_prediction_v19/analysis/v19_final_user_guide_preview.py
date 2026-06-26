# -*- coding: utf-8 -*-
"""Final v1.9 user guide writer."""
from __future__ import annotations

from pathlib import Path


def write_final_user_guide(output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""# v1.9 User Guide

## 1. What v1.9 Does
It turns football match evidence into preview-only analysis dashboards and batch decision support.

## 2. What v1.9 Does Not Do
- no automatic betting
- no stake
- no ROI
- no live result fetching
- no external network calls
- no guaranteed prediction

## 3. Choose Your Start Mode
A) I have one match Excel folder:
`$PY scripts\\run_v19_final_pipeline_preview.py --single-match-input-dir <folder> --home-team <home> --away-team <away> --competition <competition> --season <season> --match-date <date> --output-dir outputs\\analysis_preview\\v19_final_pipeline --emit-all`

B) I have raw evidence folders:
`$PY scripts\\run_v19_final_pipeline_preview.py --raw-input-dir tests\\fixtures\\raw_evidence_intake --output-dir outputs\\analysis_preview\\v19_final_pipeline --emit-all`

C) I have prepared match packs:
`$PY scripts\\run_v19_final_pipeline_preview.py --match-pack-manifest tests\\fixtures\\match_packs\\match_pack_manifest.csv --output-dir outputs\\analysis_preview\\v19_final_pipeline --emit-all`

D) I already have batch config:
`$PY scripts\\run_v19_final_pipeline_preview.py --batch-config tests\\fixtures\\batch_workbench\\lazio_atalanta_batch_config.csv --output-dir outputs\\analysis_preview\\v19_final_pipeline --emit-all`

## 4. What Files To Open After Run
- final_pipeline_dashboard.md
- final_action_plan.md
- final_release_readiness_report.md
- batch_os/executive_dashboard.md
- completion_campaign/master_completion_template.csv

## 5. How To Fill Missing Data
Open `master_completion_template.csv`, fill `user_value` only, save, rerun completion, then review `portfolio_delta_dashboard.md`.

## 6. Evidence Checklist
- Team xG
- Player xG/xA
- Match Stats
- Formation/Tactical
- Current Odds
- Recent Form
- Big Chances
- Availability
- Opening/Closing Odds
- DNB/OU Market

## 7. Common Problems
- missing metadata
- unknown files
- duplicate files
- blocked pack
- partial pack
- no promotion because safety remains disabled

## 8. Safety Reminder
Preview only. No production betting. No stake. No ROI. No automatic betting.
""", encoding="utf-8")
    return str(path.resolve())
