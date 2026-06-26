# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path


def write_release_notes(output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "release_notes_v1_9.md"
    path.write_text("""# v1.9 Release Candidate Preview Notes

## 1. Summary
v1.9 is a preview release candidate for local football evidence analysis and batch operating workflows.

## 2. What Changed
Final pipeline, raw evidence intake, match-pack scanning, batch OS, release readiness, smoke tests, and stabilization gates.

## 3. Main Entry Points
- `scripts/run_v19_final_pipeline_preview.py`
- `scripts/run_v19_release_stabilization_preview.py`

## 4. Supported Input Modes
- raw evidence
- match pack manifest
- batch config
- single match

## 5. Major Dashboards
Final dashboard, Batch OS executive dashboard, release stabilization dashboard.

## 6. Safety Boundaries
No production betting. No stake. No ROI. No automatic betting. No external network calls.

## 7. Known Limitations
Preview only. No automatic external data fetching. Input evidence quality determines output quality. Demo fixtures are synthetic if marked.

## 8. How To Run
Use `$PY scripts\\run_v19_final_pipeline_preview.py ...`.

## 9. Recommended Next Work After v1.9
Use stabilization, review docs, optionally tag preview release.
""", encoding="utf-8")
    return {"release_notes_path": str(path.resolve())}
