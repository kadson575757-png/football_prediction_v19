# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path


def write_v20_dashboard(output_dir: str | Path, payload: dict[str, object]) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "v20_historical_internet_prediction_dashboard.md"
    text = "\n".join(["# v2.0 Historical Internet Prediction Dashboard", "", "## 1. Run Status", str(payload.get("v20_historical_internet_prediction_status")), "## 2. Match Context", str(payload.get("match_context")), "## 3. Analysis Cutoff", str(payload.get("analysis_cutoff")), "## 4. Existing Source Reuse", str(payload.get("existing_source_inventory_status")), "## 5. Source Coverage", str(payload.get("coverage")), "## 6. Leakage Guard", str(payload.get("leakage_status")), "## 7. As-Of Feature Store", str(payload.get("features")), "## 8. Model Status", str(payload.get("model_status")), "## 9. Probability Table", str(payload.get("probabilities")), "## 10. Decision Class", str(payload.get("decision_class")), "## 11. Final Tip", str(payload.get("primary_tip")), "## 12. Main Risks", "Source quality and missing data.", "## 13. Missing Data", str(payload.get("missing_data", "")), "## 14. Artifacts", str(payload.get("artifact_paths", {})), "## 15. Safety Footer", "No automatic betting. No stake. No ROI.", ""])
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())
