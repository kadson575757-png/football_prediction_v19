# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.v19_decision_transition_lab_preview import V19DecisionTransitionLabConfig, V19DecisionTransitionLabRunner  # noqa: E402


def run_v19_decision_transition_lab_preview(**kwargs: object) -> dict[str, object]:
    return V19DecisionTransitionLabRunner(V19DecisionTransitionLabConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-workbench-json", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--home-team", required=True)
    parser.add_argument("--away-team", required=True)
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--match-date", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_decision_transition_lab"))
    parser.add_argument("--emit-all", action="store_true", default=False)
    parser.add_argument("--base-dir", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v19_decision_transition_lab_preview(
        base_workbench_json=args.base_workbench_json,
        input_dir=args.input_dir,
        home_team=args.home_team,
        away_team=args.away_team,
        competition=args.competition,
        season=args.season,
        match_date=args.match_date,
        output_dir=args.output_dir,
        emit_all=args.emit_all,
        base_dir=args.base_dir,
    )
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
