# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def write_backtest_report(metrics: dict[str, object], output_dir: str | Path) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "v20_no_leakage_backtest_report.md"
    path.write_text(
        "# v2.0 No-Leakage Backtest Report\n\n"
        f"- matches_total: {metrics.get('matches_total')}\n"
        f"- matches_evaluated: {metrics.get('matches_evaluated')}\n"
        f"- accuracy_1x2: {metrics.get('accuracy_1x2')}\n"
        f"- brier_score: {metrics.get('brier_score')}\n\n"
        "No ROI. No stake. No profit. No betting ledger.\n",
        encoding="utf-8",
    )
    return str(path.resolve())
