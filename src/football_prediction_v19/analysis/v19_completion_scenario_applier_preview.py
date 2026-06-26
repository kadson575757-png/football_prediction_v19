# -*- coding: utf-8 -*-
"""Apply synthetic transition-lab scenario values to a completion template."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_COMPLETION_SCENARIO_APPLIED = "V19_COMPLETION_SCENARIO_APPLIED"
V19_COMPLETION_SCENARIO_BLOCKED_MISSING_TEMPLATE = "V19_COMPLETION_SCENARIO_BLOCKED_MISSING_TEMPLATE"


@dataclass(frozen=True)
class V19CompletionScenarioApplierConfig:
    base_completion_template: str | Path
    scenario: dict[str, object]
    output_path: str | Path
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19CompletionScenarioApplierResult:
    completion_scenario_status: str
    scenario_completion_path: str
    scenario_id: str
    filled_values_count: int
    test_scenario_mode: bool
    synthetic_completion_values: bool
    not_real_match_data: bool
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19CompletionScenarioApplier:
    def __init__(self, config: V19CompletionScenarioApplierConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19CompletionScenarioApplierResult:
        template_path = _resolve(self.config.base_completion_template, self.base)
        if not template_path.exists():
            return self._blocked()
        frame = pd.read_csv(template_path, keep_default_na=False)
        scenario = self.config.scenario
        values = scenario.get("synthetic_values", {}) if isinstance(scenario.get("synthetic_values", {}), dict) else {}
        if "user_value" not in frame.columns:
            frame["user_value"] = ""
        for column in ["scenario_id", "test_scenario_mode", "synthetic_completion_values", "not_real_match_data", "not_for_prediction"]:
            if column not in frame.columns:
                frame[column] = ""
        filled = 0
        for index, row in frame.iterrows():
            field = str(row.get("field_name", "")).strip()
            value = values.get(field, "")
            if str(value).strip():
                frame.at[index, "user_value"] = value
                filled += 1
            frame.at[index, "scenario_id"] = scenario.get("scenario_id", "")
            frame.at[index, "test_scenario_mode"] = "true"
            frame.at[index, "synthetic_completion_values"] = "true"
            frame.at[index, "not_real_match_data"] = "true"
            frame.at[index, "not_for_prediction"] = "true"
        output_path = _resolve(self.config.output_path, self.base)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_path, index=False)
        return V19CompletionScenarioApplierResult(
            V19_COMPLETION_SCENARIO_APPLIED,
            str(output_path.resolve()),
            str(scenario.get("scenario_id", "")),
            filled,
            True,
            True,
            True,
            False,
            False,
            False,
            False,
            V19_COMPLETION_SCENARIO_APPLIED,
        )

    def _blocked(self) -> V19CompletionScenarioApplierResult:
        return V19CompletionScenarioApplierResult(V19_COMPLETION_SCENARIO_BLOCKED_MISSING_TEMPLATE, "", str(self.config.scenario.get("scenario_id", "")), 0, True, True, True, False, False, False, False, V19_COMPLETION_SCENARIO_BLOCKED_MISSING_TEMPLATE)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
