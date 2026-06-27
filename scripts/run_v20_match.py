# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_v20_real_match_autopilot import run_v20_real_match_autopilot  # noqa: E402


def run_v20_match(**kwargs: object) -> dict[str, object]:
    if not kwargs.get("output_dir"):
        safe = "_".join(str(kwargs.get(k, "")).lower().replace(" ", "_").replace("/", "-") for k in ["home_team", "away_team", "match_date"])
        kwargs["output_dir"] = f"outputs/analysis_preview/v20_match_{safe}"
    result = run_v20_real_match_autopilot(**kwargs)
    out = Path(str(kwargs["output_dir"]))
    block_reasons = result.get("block_reasons", [])
    missing = result.get("missing_data", {})
    source_status = result.get("source_status", {})
    source_lines = "\n".join(f"- {k}: {v.get('status')} ({v.get('reason')})" for k, v in source_status.items())
    top = "# DATA_BLOCKED" if result.get("decision_class") == "DATA_BLOCKED" else ("# NO_BET" if result.get("decision_class") == "NO_BET" else ("# ANALYST_LEAN" if result.get("decision_class") == "ANALYST_LEAN" else "# MODEL_TIP"))
    aliases = {
        "final_tip_card.md": top + "\n\n# v2.0 Final Tip Card\n\n" + f"decision_class={result.get('decision_class')}\nprimary_tip={result.get('primary_tip')}\nBlock Reason: {', '.join(block_reasons)}\nNo automatic betting. No stake. No ROI.\n",
        "missing_data_report.md": top + "\n\n# v2.0 Missing Data Report\n\n" + "\n".join(f"- {k}: {str(v).lower()}" for k, v in missing.items()) + "\n",
        "source_quality_report.md": top + "\n\n# v2.0 Source Quality Report\n\n" + f"source_quality_score={result.get('source_quality_score')}\nsource_quality_band={result.get('source_quality_band')}\n\nSource Status:\n{source_lines}\n",
    }
    for name, text in aliases.items():
        (out / name).write_text(text, encoding="utf-8")
    report_src = Path(result["v20_final_real_match_report_path"])
    (out / "final_match_report.md").write_text(report_src.read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame([result.get("probabilities", {})]).to_csv(out / "model_probabilities.csv", index=False)
    result["v20_match_status"] = result["v20_real_match_autopilot_status"]
    result["risk_level"] = "HIGH" if result.get("decision_class") in {"NO_BET", "DATA_BLOCKED"} else "MEDIUM"
    (out / "machine_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([{"artifact_name": p.name, "path": str(p.resolve())} for p in out.iterdir() if p.is_file()]).to_csv(out / "artifact_index.csv", index=False)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--home-team", required=True); p.add_argument("--away-team", required=True); p.add_argument("--competition", required=True); p.add_argument("--season", required=True); p.add_argument("--match-date", required=True); p.add_argument("--kickoff-time", default="")
    p.add_argument("--mock-data-dir", default=""); p.add_argument("--output-dir", default=""); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT))
    args = p.parse_args(argv)
    result = run_v20_match(**vars(args))
    for key in ["v20_match_status", "decision_class", "primary_tip", "confidence", "risk_level", "source_quality_band", "leakage_status", "network_calls_enabled", "cache_used", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        print(f"{key}={str(result.get(key)).lower() if isinstance(result.get(key), bool) else result.get(key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
