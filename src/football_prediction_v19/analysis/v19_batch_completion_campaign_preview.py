# -*- coding: utf-8 -*-
"""Batch completion campaign preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_completion_pack_preview import _field_rows

V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY = "V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY"
V19_BATCH_COMPLETION_CAMPAIGN_BLOCKED_MISSING_INPUT = "V19_BATCH_COMPLETION_CAMPAIGN_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19BatchCompletionCampaignConfig:
    batch_results_json: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_batch_completion_campaign"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchCompletionCampaignResult:
    batch_completion_campaign_status: str
    batch_completion_campaign_enabled: bool
    campaign_output_dir: str
    campaign_dashboard_path: str
    master_completion_template_path: str
    master_completion_template_md_path: str
    priority_fill_plan_path: str
    match_fill_matrix_path: str
    match_fill_matrix_md_path: str
    critical_fields_by_match_path: str
    market_fields_by_match_path: str
    availability_fields_by_match_path: str
    form_big_chance_fields_by_match_path: str
    campaign_summary_json_path: str
    campaign_bundle_index_path: str
    fillable_fields_total: int
    critical_fields_total: int
    matches_with_critical_blockers: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19BatchCompletionCampaignBuilder:
    def __init__(self, config: V19BatchCompletionCampaignConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchCompletionCampaignResult:
        batch = _read_json(_resolve(self.config.batch_results_json, self.base))
        if not batch:
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        rows = _master_rows(batch)
        frame = pd.DataFrame(rows)
        paths = {
            "campaign_dashboard": out / "campaign_dashboard.md",
            "master_completion_template": out / "master_completion_template.csv",
            "master_completion_template_md": out / "master_completion_template.md",
            "priority_fill_plan": out / "priority_fill_plan.md",
            "match_fill_matrix": out / "match_fill_matrix.csv",
            "match_fill_matrix_md": out / "match_fill_matrix.md",
            "critical_fields_by_match": out / "critical_fields_by_match.csv",
            "market_fields_by_match": out / "market_fields_by_match.csv",
            "availability_fields_by_match": out / "availability_fields_by_match.csv",
            "form_big_chance_fields_by_match": out / "form_big_chance_fields_by_match.csv",
            "campaign_summary_json": out / "campaign_summary.json",
            "campaign_bundle_index": out / "campaign_bundle_index.csv",
        }
        frame.to_csv(paths["master_completion_template"], index=False)
        frame.to_csv(paths["match_fill_matrix"], index=False)
        frame[frame["priority"].eq("CRITICAL")].to_csv(paths["critical_fields_by_match"], index=False)
        frame[frame["field_group"].eq("Market")].to_csv(paths["market_fields_by_match"], index=False)
        frame[frame["field_group"].eq("Availability")].to_csv(paths["availability_fields_by_match"], index=False)
        frame[frame["field_group"].isin(["Recent Form", "Big Chances"])].to_csv(paths["form_big_chance_fields_by_match"], index=False)
        paths["campaign_dashboard"].write_text(_dashboard(batch, frame), encoding="utf-8")
        paths["master_completion_template_md"].write_text("# v1.9 Master Completion Template\n\n" + _table(frame.head(80)) + "\n", encoding="utf-8")
        paths["priority_fill_plan"].write_text(_priority_plan(frame), encoding="utf-8")
        paths["match_fill_matrix_md"].write_text("# v1.9 Match Fill Matrix\n\n" + _table(frame) + "\n", encoding="utf-8")
        summary = {
            "batch_completion_campaign_status": V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY,
            "matches_total": batch.get("matches_total", 0),
            "fillable_fields_total": len(frame),
            "critical_fields_total": int(frame["priority"].eq("CRITICAL").sum()),
            "matches_with_critical_blockers": len({row["match_id"] for row in rows if row["priority"] == "CRITICAL"}),
            "safety": _safety(),
        }
        paths["campaign_summary_json"].write_text(json.dumps(summary, indent=2), encoding="utf-8")
        _write_bundle(paths["campaign_bundle_index"], paths)
        return V19BatchCompletionCampaignResult(
            V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY,
            True,
            str(out.resolve()),
            str(paths["campaign_dashboard"].resolve()),
            str(paths["master_completion_template"].resolve()),
            str(paths["master_completion_template_md"].resolve()),
            str(paths["priority_fill_plan"].resolve()),
            str(paths["match_fill_matrix"].resolve()),
            str(paths["match_fill_matrix_md"].resolve()),
            str(paths["critical_fields_by_match"].resolve()),
            str(paths["market_fields_by_match"].resolve()),
            str(paths["availability_fields_by_match"].resolve()),
            str(paths["form_big_chance_fields_by_match"].resolve()),
            str(paths["campaign_summary_json"].resolve()),
            str(paths["campaign_bundle_index"].resolve()),
            len(frame),
            int(frame["priority"].eq("CRITICAL").sum()),
            summary["matches_with_critical_blockers"],
            False,
            False,
            False,
            False,
            V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY,
        )

    def _blocked(self) -> V19BatchCompletionCampaignResult:
        return V19BatchCompletionCampaignResult(V19_BATCH_COMPLETION_CAMPAIGN_BLOCKED_MISSING_INPUT, False, "", "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, False, False, False, False, V19_BATCH_COMPLETION_CAMPAIGN_BLOCKED_MISSING_INPUT)


def _master_rows(batch: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    template_fields = _field_rows({})
    for match in batch.get("matches", []):
        if not isinstance(match, dict) or match.get("status") != "SUCCESS":
            continue
        for field in template_fields:
            rows.append({
                "match_id": match.get("match_id", ""),
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "competition": match.get("competition", ""),
                "match_date": match.get("match_date", ""),
                "field_group": field["field_group"],
                "field_name": field["field_name"],
                "current_status": field["current_status"],
                "priority": field["priority"],
                "required_for": field["required_for"],
                "affected_market_families": field["affected_market_families"],
                "current_value": "",
                "user_value": "",
                "example_format": field["example_format"],
                "notes": field["notes"],
            })
    return rows


def _dashboard(batch: dict[str, object], frame: pd.DataFrame) -> str:
    return "\n".join([
        "# v1.9 Batch Completion Campaign Dashboard",
        "",
        f"- matches_total: {batch.get('matches_total', 0)}",
        f"- fillable_fields_total: {len(frame)}",
        f"- critical_fields_total: {int(frame['priority'].eq('CRITICAL').sum()) if not frame.empty else 0}",
        "",
        "## How To Use",
        "Fill only the `user_value` column, save the CSV, then run the batch completion rerun command.",
        "",
        "## Safety",
        "Preview only. No production betting. No stake. No ROI. No automatic betting.",
        "",
    ])


def _priority_plan(frame: pd.DataFrame) -> str:
    groups = frame[frame["priority"].eq("CRITICAL")]["field_group"].drop_duplicates().tolist() if not frame.empty else []
    return "# v1.9 Priority Fill Plan\n\n" + "\n".join(f"- {group}" for group in groups) + "\n"


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
