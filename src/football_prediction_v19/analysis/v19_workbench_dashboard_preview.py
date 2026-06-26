# -*- coding: utf-8 -*-
"""User-facing dashboard for the v1.9 match workbench preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

V19_WORKBENCH_DASHBOARD_PREVIEW_READY = "V19_WORKBENCH_DASHBOARD_PREVIEW_READY"


@dataclass(frozen=True)
class V19WorkbenchDashboardConfig:
    match: dict[str, object]
    production_readiness: dict[str, object]
    artifact_paths: dict[str, str]
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19WorkbenchDashboardResult:
    workbench_dashboard_status: str
    workbench_dashboard_path: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19WorkbenchDashboardRenderer:
    def __init__(self, config: V19WorkbenchDashboardConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19WorkbenchDashboardResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "workbench_dashboard.md"
        path.write_text(_render(self.config.match, self.config.production_readiness, self.config.artifact_paths), encoding="utf-8")
        return V19WorkbenchDashboardResult(V19_WORKBENCH_DASHBOARD_PREVIEW_READY, str(path.resolve()), False, False, False, False, V19_WORKBENCH_DASHBOARD_PREVIEW_READY)


def _render(match: dict[str, object], readiness: dict[str, object], artifacts: dict[str, str]) -> str:
    home = match.get("home_team", "")
    away = match.get("away_team", "")
    competition = match.get("competition", "")
    season = match.get("season", "")
    date = match.get("match_date", "")
    lines = [
        "# v1.9 Match Workbench Dashboard",
        "",
        "## 1. Match",
        f"{home} vs {away}, {competition}, {season}, {date}",
        "",
        "## 2. Current Final Status",
        f"- final_decision_class: {readiness.get('final_decision_class', '')}",
        f"- evidence_readiness_score: {readiness.get('readiness_score', '')}",
        f"- promotion_allowed: {str(readiness.get('promotion_allowed', False)).lower()}",
        f"- strong_promotion_allowed: {str(readiness.get('strong_promotion_allowed', False)).lower()}",
        f"- conflict_score: {readiness.get('conflict_score', '')}",
        "- No production bet",
        "",
        "## 3. What We Know",
        "- Atalanta structural edge",
        "- Lazio counterweights",
        "- score tree readable",
        "- market preview readable",
        "- set-piece route",
        "",
        "## 4. What Blocks Promotion",
        "- recent form missing",
        "- big chances missing",
        "- full availability missing",
        "- opening/closing odds missing",
        "- DNB/OU missing",
        "- conflict score HIGH",
        "- productive betting disabled",
        "",
        "## 5. What To Fill Next",
        "- Recent Form",
        "- Big Chances",
        "- Availability",
        "- Market",
        "",
        "## 6. What Could Upgrade",
        "- if recent form aligns with Atalanta edge",
        "- if big chances support Atalanta",
        "- if availability does not hurt Atalanta",
        "- if market movement does not drift against Atalanta",
        "",
        "## 7. What Could Downgrade",
        "- if Lazio form/big chances stronger",
        "- if Atalanta key attackers missing",
        "- if market moves against Atalanta",
        "- if lineup uncertainty remains",
        "",
        "## 8. Artifact Links",
    ]
    lines.extend([f"- {name}: {path}" for name, path in artifacts.items()])
    lines.extend([
        "",
        "## 9. Safety Footer",
        "Preview only. No stake. No ROI. No automatic betting. network_calls_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false.",
        "",
    ])
    return "\n".join(lines)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
