# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path


def write_release_checklist(output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    items = ["Pull latest main", "Run final pipeline raw mode", "Run final pipeline manifest mode", "Run final pipeline batch config mode", "Run final pipeline single match mode", "Run final smoke tests", "Run release stabilization", "Review final dashboard", "Review final user guide", "Confirm safety flags remain false", "Confirm no generated outputs are committed", "Tag preview release if desired"]
    md = out / "release_checklist.md"; js = out / "release_checklist.json"
    commands = "\n".join(["```powershell", "$PY scripts\\run_v19_final_pipeline_preview.py --raw-input-dir tests\\fixtures\\raw_evidence_intake --output-dir outputs\\analysis_preview\\v19_final_pipeline_raw --emit-all", "$PY scripts\\run_v19_final_smoke_tests_preview.py --output-dir outputs\\analysis_preview\\v19_final_smoke_tests --emit-all", "$PY scripts\\run_v19_release_stabilization_preview.py --output-dir outputs\\analysis_preview\\v19_release_stabilization --emit-all", "```"])
    md.write_text("# v1.9 Release Checklist\n\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items)) + "\n\n## Commands\n\n" + commands + "\n\nConfirm no generated outputs are committed.\n", encoding="utf-8")
    js.write_text(json.dumps({"release_checklist_status": "READY", "items": items}, indent=2), encoding="utf-8")
    return {"release_checklist_path": str(md.resolve()), "release_checklist_json_path": str(js.resolve())}
