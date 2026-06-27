# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def write_v20_real_match_autopilot_dashboard(result: dict[str, object], output_dir: str | Path) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "v20_real_match_autopilot_dashboard.md"
    path.write_text(
        "\n".join([
            "# v2.0 Real Match Autopilot Dashboard",
            "",
            f"- status: {result.get('v20_real_match_autopilot_status')}",
            f"- fixture_resolution_status: {result.get('fixture_resolution_status')}",
            f"- source_readiness: {result.get('source_readiness')}",
            f"- source_quality_band: {result.get('source_quality_band')}",
            f"- decision_class: {result.get('decision_class')}",
            f"- safety: automatic_betting={str(result.get('automatic_betting_enabled')).lower()} staking={str(result.get('staking_logic_enabled')).lower()} roi={str(result.get('roi_logic_enabled')).lower()}",
            "",
        ]),
        encoding="utf-8",
    )
    return str(path.resolve())
