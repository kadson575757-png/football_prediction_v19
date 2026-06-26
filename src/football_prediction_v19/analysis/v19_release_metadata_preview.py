# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path


def write_release_metadata(output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    payload = {"release_name": "v1.9 Final Release Candidate Preview", "release_status": "READY_TO_TAG_PREVIEW", "latest_pr_expected": "dynamic unknown allowed", "safety_mode": "preview-only", "supported_modes": ["raw evidence", "match pack manifest", "batch config", "single match"], "main_entrypoint": "scripts/run_v19_final_pipeline_preview.py", "stabilization_entrypoint": "scripts/run_v19_release_stabilization_preview.py"}
    js = out / "release_metadata_v1_9.json"; md = out / "release_metadata_v1_9.md"
    js.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md.write_text("# v1.9 Release Metadata\n\n" + "\n".join(f"- {k}: {v}" for k, v in payload.items()) + "\n", encoding="utf-8")
    return {"release_metadata_json_path": str(js.resolve()), "release_metadata_md_path": str(md.resolve())}
