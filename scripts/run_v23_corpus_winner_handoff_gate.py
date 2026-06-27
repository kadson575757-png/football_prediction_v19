# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v23_corpus_winner_handoff_gate import run_v23_corpus_winner_handoff_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/analysis_preview/v23_corpus_winner_handoff_gate")
    parser.add_argument("--emit-all", action="store_true")
    result = run_v23_corpus_winner_handoff_gate(parser.parse_args(argv).output_dir)
    for key in [
        "v23_corpus_winner_handoff_gate_status",
        "data_block_audit_status",
        "eligibility_unblock_status",
        "feature_handoff_status",
        "partial_model_status",
        "decision_policy_status",
        "backtest_blocking_status",
        "multileague_handoff_status",
        "safety_status",
        "recommendation",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
