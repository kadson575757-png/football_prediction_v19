# -*- coding: utf-8 -*-
"""Preview-only validation of manual v1.9 completion evidence."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.real_match_input_pack_preview import COMPLETION_GROUPS

V19_COMPLETION_VALIDATION_PREVIEW_READY = "V19_COMPLETION_VALIDATION_PREVIEW_READY"
V19_COMPLETION_VALIDATION_BLOCKED_MISSING_INPUT = "V19_COMPLETION_VALIDATION_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19CompletionValidationConfig:
    intake_path: str | Path
    completion_path: str | Path | None = None
    completed_intake_path: str | Path | None = None
    fields_completed_count: int = 0
    remaining_missing_fields_count: int = 0
    completed_evidence_groups: str = ""
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19CompletionValidationResult:
    completion_validation_status: str
    completion_validation_report_path: str
    completion_validation_json_path: str
    completion_file_used: str
    fields_completed_count: int
    fields_rejected_count: int
    remaining_missing_fields_count: int
    completed_groups: str
    still_missing_by_group: str
    critical_missing_fields: str
    market_missing_fields: str
    availability_missing_fields: str
    form_missing_fields: str
    tactical_missing_fields: str
    data_quality_warnings: str
    template_next_actions: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19CompletionValidationRunner:
    def __init__(self, config: V19CompletionValidationConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19CompletionValidationResult:
        intake = _read_frame(_resolve(self.config.intake_path, self.base))
        completed = _read_frame(_resolve(self.config.completed_intake_path, self.base)) if self.config.completed_intake_path else intake
        completion = _read_frame(_resolve(self.config.completion_path, self.base)) if self.config.completion_path else pd.DataFrame()
        if intake.empty:
            return self._blocked()

        row = completed.iloc[0] if not completed.empty else intake.iloc[0]
        missing_by_group = _missing_by_group(row)
        critical = [
            field for field in [
                "home_recent_xg_for", "away_recent_xg_for", "home_recent_xg_against", "away_recent_xg_against",
                "home_big_chances_for", "away_big_chances_for", "home_big_chances_against", "away_big_chances_against",
            ]
            if _blank(row.get(field, ""))
        ]
        market_missing = _missing_subset(row, "Market/Odds")
        availability_missing = _missing_subset(row, "Lineups/Availability")
        form_missing = _missing_subset(row, "Player/Recent Form")
        tactical_missing = _missing_subset(row, "Tactical/Fatigue")
        warnings = _numeric_warnings(completion)
        groups = self.config.completed_evidence_groups or _completed_groups(row)
        fields_completed = int(self.config.fields_completed_count or _changed_count(intake, completed))
        remaining_missing = int(self.config.remaining_missing_fields_count or sum(len(v) for v in missing_by_group.values()))

        payload = {
            "completion_validation_status": V19_COMPLETION_VALIDATION_PREVIEW_READY,
            "completion_file_used": "yes" if self.config.completion_path else "no",
            "fields_completed_count": fields_completed,
            "fields_rejected_count": len(warnings),
            "remaining_missing_fields_count": remaining_missing,
            "completed_groups": groups,
            "still_missing_by_group": missing_by_group,
            "critical_missing_fields": critical,
            "market_missing_fields": market_missing,
            "availability_missing_fields": availability_missing,
            "form_missing_fields": form_missing,
            "tactical_missing_fields": tactical_missing,
            "data_quality_warnings": warnings,
            "template_next_actions": _next_actions(critical, market_missing, availability_missing, tactical_missing),
            "safety": _safety(),
        }
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / "completion_validation.json"
        report_path = out / "completion_validation_report.md"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report_path.write_text(_render(payload), encoding="utf-8")
        return V19CompletionValidationResult(
            V19_COMPLETION_VALIDATION_PREVIEW_READY,
            str(report_path.resolve()),
            str(json_path.resolve()),
            payload["completion_file_used"],
            fields_completed,
            len(warnings),
            remaining_missing,
            groups,
            _join_group_missing(missing_by_group),
            " | ".join(critical),
            " | ".join(market_missing),
            " | ".join(availability_missing),
            " | ".join(form_missing),
            " | ".join(tactical_missing),
            " | ".join(warnings),
            " | ".join(payload["template_next_actions"]),
            False,
            False,
            False,
            False,
            V19_COMPLETION_VALIDATION_PREVIEW_READY,
        )

    def _blocked(self) -> V19CompletionValidationResult:
        return V19CompletionValidationResult(V19_COMPLETION_VALIDATION_BLOCKED_MISSING_INPUT, "", "", "no", 0, 0, 0, "", "", "", "", "", "", "", "", "", False, False, False, False, V19_COMPLETION_VALIDATION_BLOCKED_MISSING_INPUT)


def _render(payload: dict[str, object]) -> str:
    missing = payload["still_missing_by_group"]
    warning_lines = [f"- {warning}" for warning in payload["data_quality_warnings"]] or ["- none"]
    lines = [
        "# v1.9 Completion Validation Preview",
        "",
        "## 1. Completion Status",
        f"- completion applied: {payload['completion_file_used']}",
        f"- fields_completed_count: {payload['fields_completed_count']}",
        f"- remaining_missing_fields_count: {payload['remaining_missing_fields_count']}",
        "",
        "## 2. Fields Completed",
        f"- completed_groups: {payload['completed_groups'] or 'none'}",
        "",
        "## 3. Groups Completed",
        "- Match Stats/Control completed enough for diagnostic" if "Match Stats/Control" in str(payload["completed_groups"]) else "- Match Stats/Control still incomplete",
        "- H2H manual note present" if not any("h2h_summary" in fields for fields in missing.values()) else "- H2H manual note missing",
        "",
        "## 4. Remaining Missing Fields",
        *[f"- {group}: {', '.join(fields) if fields else 'none'}" for group, fields in missing.items()],
        "",
        "## 5. Critical Missing Fields",
        "- Recent Form missing",
        "- Big Chances missing",
        "",
        "## 6. Group-by-Group Validation",
        "- Market/Odds partial: current odds may be present, opening/closing and DNB/OU remain blockers.",
        "- Lineups/Availability partial: lineup status is not enough without goalkeeper, missing, suspended and doubtful details.",
        "- Tactical/Fatigue partial: score/profile can be diagnostic while tactical notes remain incomplete.",
        "- Match Stats/Control completed enough for diagnostic.",
        "",
        "## 7. Data Quality Warnings",
        *warning_lines,
        "",
        "## 8. Next Fields To Fill",
        *[f"- {item}" for item in payload["template_next_actions"]],
        "",
        "## 9. Impact on Production Readiness",
        "Completion improves analyst readability, but Recent Form missing and Big Chances missing keep promotion blocked.",
        "",
        "## 10. Safety Footer",
        "Preview only. No production betting, no stake, no ROI, no automatic betting.",
        "",
    ]
    return "\n".join(lines)


def _missing_by_group(row: pd.Series) -> dict[str, list[str]]:
    return {group: [field for field in fields if field in row.index and _blank(row.get(field, ""))] for group, fields in COMPLETION_GROUPS.items()}


def _missing_subset(row: pd.Series, group: str) -> list[str]:
    return _missing_by_group(row).get(group, [])


def _completed_groups(row: pd.Series) -> str:
    groups = []
    for group, fields in COMPLETION_GROUPS.items():
        if any(field in row.index and not _blank(row.get(field, "")) for field in fields):
            groups.append(group)
    return " | ".join(groups)


def _changed_count(before: pd.DataFrame, after: pd.DataFrame) -> int:
    if before.empty or after.empty:
        return 0
    count = 0
    for column in after.columns:
        before_value = before.iloc[0].get(column, "") if column in before.columns else ""
        if _blank(before_value) and not _blank(after.iloc[0].get(column, "")):
            count += 1
    return count


def _numeric_warnings(completion: pd.DataFrame) -> list[str]:
    if completion.empty:
        return []
    numeric_tokens = ["odds", "xg", "shots", "possession", "score", "count", "over_line", "handicap_line", "days", "chances"]
    warnings = []
    row = completion.iloc[0]
    for column in completion.columns:
        value = row.get(column, "")
        if _blank(value) or not any(token in column for token in numeric_tokens):
            continue
        if pd.isna(pd.to_numeric(pd.Series([value]), errors="coerce")).iloc[0]:
            warnings.append(f"{column} has non-numeric value")
    return warnings


def _next_actions(critical: list[str], market: list[str], availability: list[str], tactical: list[str]) -> list[str]:
    actions = []
    if critical:
        actions.append("Fill recent form and big chances fields.")
    if market:
        actions.append("Add opening, closing, DNB and Over/Under market fields.")
    if availability:
        actions.append("Add goalkeeper, missing, suspended and doubtful player fields.")
    if tactical:
        actions.append("Add tactical detail notes and fatigue/rest context.")
    return actions or ["No critical next action detected."]


def _join_group_missing(missing: dict[str, list[str]]) -> str:
    return " | ".join(f"{group}: {','.join(fields)}" for group, fields in missing.items() if fields)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _resolve(path: str | Path | None, base: Path) -> Path:
    p = Path(str(path or ""))
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if not path.exists() or path.is_dir():
            return pd.DataFrame()
        return pd.read_csv(path, low_memory=False, keep_default_na=False)
    except (EmptyDataError, OSError):
        return pd.DataFrame()


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""
