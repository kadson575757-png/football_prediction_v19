# -*- coding: utf-8 -*-
"""Build a fillable v1.9 completion pack from a match workbench JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_COMPLETION_PACK_PREVIEW_READY = "V19_COMPLETION_PACK_PREVIEW_READY"
V19_COMPLETION_PACK_BLOCKED_MISSING_INPUT = "V19_COMPLETION_PACK_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19CompletionPackConfig:
    workbench_json: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_completion_pack"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19CompletionPackResult:
    completion_pack_status: str
    completion_pack_enabled: bool
    completion_pack_output_dir: str
    completion_pack_dashboard_path: str
    completion_fill_template_path: str
    completion_fill_template_md_path: str
    critical_fields_only_path: str
    market_fields_only_path: str
    availability_fields_only_path: str
    form_big_chance_fields_only_path: str
    tactical_fields_only_path: str
    completion_fill_guide_path: str
    completion_pack_json_path: str
    completion_pack_bundle_index_path: str
    completion_fields_count: int
    critical_fields_count: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19CompletionPackBuilder:
    def __init__(self, config: V19CompletionPackConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19CompletionPackResult:
        payload = _read_json(_resolve(self.config.workbench_json, self.base))
        if not payload:
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        fields = _field_rows(payload)
        frame = pd.DataFrame(fields)
        paths = {
            "completion_pack_dashboard": out / "completion_pack_dashboard.md",
            "completion_fill_template": out / "completion_fill_template.csv",
            "completion_fill_template_md": out / "completion_fill_template.md",
            "critical_fields_only": out / "critical_fields_only.csv",
            "market_fields_only": out / "market_fields_only.csv",
            "availability_fields_only": out / "availability_fields_only.csv",
            "form_big_chance_fields_only": out / "form_big_chance_fields_only.csv",
            "tactical_fields_only": out / "tactical_fields_only.csv",
            "completion_fill_guide": out / "completion_fill_guide.md",
            "completion_pack_json": out / "completion_pack.json",
            "completion_pack_bundle_index": out / "completion_pack_bundle_index.csv",
        }
        frame.to_csv(paths["completion_fill_template"], index=False)
        frame[frame["priority"].eq("CRITICAL")].to_csv(paths["critical_fields_only"], index=False)
        frame[frame["field_group"].eq("Market")].to_csv(paths["market_fields_only"], index=False)
        frame[frame["field_group"].eq("Availability")].to_csv(paths["availability_fields_only"], index=False)
        frame[frame["field_group"].isin(["Recent Form", "Big Chances"])].to_csv(paths["form_big_chance_fields_only"], index=False)
        frame[frame["field_group"].isin(["Tactical Details", "Fatigue", "Defensive Actions"])].to_csv(paths["tactical_fields_only"], index=False)
        paths["completion_pack_dashboard"].write_text(_dashboard(payload, frame), encoding="utf-8")
        paths["completion_fill_template_md"].write_text(_template_md(frame), encoding="utf-8")
        paths["completion_fill_guide"].write_text(_guide(), encoding="utf-8")
        pack = {
            "completion_pack_status": V19_COMPLETION_PACK_PREVIEW_READY,
            "match": payload.get("match", {}),
            "fields": frame.to_dict(orient="records"),
            "production_readiness": payload.get("production_readiness", {}),
            "artifact_paths": {name: str(path.resolve()) for name, path in paths.items()},
            "safety": _safety(completion_pack_enabled=True),
        }
        paths["completion_pack_json"].write_text(json.dumps(pack, indent=2), encoding="utf-8")
        index = _write_index(paths["completion_pack_bundle_index"], paths)
        return V19CompletionPackResult(
            V19_COMPLETION_PACK_PREVIEW_READY,
            True,
            str(out.resolve()),
            str(paths["completion_pack_dashboard"].resolve()),
            str(paths["completion_fill_template"].resolve()),
            str(paths["completion_fill_template_md"].resolve()),
            str(paths["critical_fields_only"].resolve()),
            str(paths["market_fields_only"].resolve()),
            str(paths["availability_fields_only"].resolve()),
            str(paths["form_big_chance_fields_only"].resolve()),
            str(paths["tactical_fields_only"].resolve()),
            str(paths["completion_fill_guide"].resolve()),
            str(paths["completion_pack_json"].resolve()),
            str(paths["completion_pack_bundle_index"].resolve()),
            len(frame),
            int(frame["priority"].eq("CRITICAL").sum()),
            False,
            False,
            False,
            False,
            V19_COMPLETION_PACK_PREVIEW_READY,
        )

    def _blocked(self) -> V19CompletionPackResult:
        return V19CompletionPackResult(V19_COMPLETION_PACK_BLOCKED_MISSING_INPUT, False, "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, False, False, False, False, V19_COMPLETION_PACK_BLOCKED_MISSING_INPUT)


def _field_rows(payload: dict[str, object]) -> list[dict[str, str]]:
    rows = []
    def add(group: str, names: list[str], priority: str, required: str, markets: str, example: str) -> None:
        for name in names:
            rows.append({
                "field_group": group,
                "field_name": name,
                "current_status": "MISSING",
                "required_for": required,
                "affected_market_families": markets,
                "priority": priority,
                "example_format": example,
                "user_value": "",
                "notes": "Fill only verified evidence; do not invent values.",
            })
    add("Recent Form", ["home_recent_xg_for", "away_recent_xg_for", "home_recent_xg_against", "away_recent_xg_against"], "CRITICAL", "Recent Form gate", "1X2 | Goals | Score Family", "decimal")
    add("Big Chances", ["home_big_chances_for", "away_big_chances_for", "home_big_chances_against", "away_big_chances_against"], "CRITICAL", "Big Chances gate", "Goals | BTTS | Score Family", "integer")
    add("Availability", ["home_goalkeeper_status", "away_goalkeeper_status", "home_missing_players", "away_missing_players", "home_suspended_players", "away_suspended_players", "home_doubtful_players", "away_doubtful_players"], "CRITICAL", "Full Availability Details gate", "1X2 | DNB | BTTS", "text")
    add("Market", ["home_open_odds", "draw_open_odds", "away_open_odds", "home_closing_odds", "draw_closing_odds", "away_closing_odds", "dnb_home_odds", "dnb_away_odds", "over_line", "over_current_odds", "under_current_odds"], "CRITICAL", "Opening/Closing and DNB/OU gates", "1X2 | Double Chance | DNB | Over/Under", "decimal")
    add("Defensive Actions", ["home_tackles", "away_tackles", "home_interceptions", "away_interceptions", "home_blocks", "away_blocks"], "HIGH", "confidence upgrade", "1X2 | Goals", "integer")
    add("Tactical Details", ["formation_matchup_note", "pressing_matchup_note", "transition_matchup_note", "defensive_line_risk_note"], "HIGH", "tactical confidence", "Score Family | BTTS", "text")
    add("Fatigue", ["home_rest_days", "away_rest_days", "home_travel_fatigue_note", "away_travel_fatigue_note"], "MEDIUM", "fatigue review", "1X2 | DNB", "number/text")
    add("Referee", ["referee_name", "referee_profile_note"], "NICE", "context", "All", "text")
    add("Weather", ["weather_note", "pitch_note"], "NICE", "context", "Goals | Score Family", "text")
    add("H2H", ["h2h_summary", "h2h_style_note"], "NICE", "manual context", "All", "text")
    return rows


def _dashboard(payload: dict[str, object], frame: pd.DataFrame) -> str:
    match = payload.get("match", {})
    readiness = payload.get("production_readiness", {})
    critical = frame[frame["priority"].eq("CRITICAL")]
    return "\n".join([
        "# v1.9 Completion Pack Dashboard",
        "",
        "## 1. Match",
        f"- {match.get('home_team', '')} vs {match.get('away_team', '')}",
        f"- Competition: {match.get('competition', '')}",
        f"- Date: {match.get('match_date', '')}",
        f"- Current final_decision_class: {readiness.get('final_decision_class', '')}",
        "",
        "## 2. Why This Pack Exists",
        "- current status ANALYST_LEAN_ONLY",
        "- promotion blocked",
        "- critical blockers active",
        "",
        "## 3. Critical Fields To Fill First",
        _table(critical[["field_name", "field_group", "required_for", "affected_market_families"]].rename(columns={"field_group": "group", "required_for": "why required", "affected_market_families": "affected market families"})),
        "",
        "## 4. Minimum Useful Fill Set",
        "- Recent xG for/against",
        "- Big Chances for/against",
        "- Goalkeeper status",
        "- Missing/suspended/doubtful players",
        "- Opening/closing odds",
        "- DNB/OU odds",
        "",
        "## 5. Market-Specific Fill Sets",
        "- 1X2 needed fields: recent form, availability, opening/closing odds",
        "- Double Chance needed fields: recent form, market movement",
        "- DNB needed fields: DNB odds and availability",
        "- Over/Under needed fields: big chances, OU line, recent goals/xG",
        "- BTTS needed fields: big chances and availability",
        "- Score Family needed fields: recent form, tactical details, availability",
        "",
        "## 6. How To Use",
        "- Fill user_value column",
        "- Save CSV",
        "- Run rerun command",
        "- Open decision_delta_report.md",
        "",
        "## 7. Safety Footer",
        "Preview only. No stake. No ROI. No automatic betting.",
        "",
    ])


def _template_md(frame: pd.DataFrame) -> str:
    return "# v1.9 Completion Fill Template\n\n" + _table(frame.head(50)) + "\n"


def _guide() -> str:
    return "\n".join(["# v1.9 Completion Fill Guide", "", "Fill only `user_value`. Leave unknown values blank. No fake values. No automatic betting.", ""])


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _write_index(path: Path, paths: dict[str, Path]) -> list[dict[str, object]]:
    rows = [{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return rows


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safety(*, completion_pack_enabled: bool) -> dict[str, bool]:
    return {
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "completion_pack_enabled": completion_pack_enabled,
    }
