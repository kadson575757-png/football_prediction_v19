# -*- coding: utf-8 -*-
"""Before/after decision delta preview for v1.9 workbench reruns."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

V19_DECISION_DELTA_PREVIEW_READY = "V19_DECISION_DELTA_PREVIEW_READY"
V19_DECISION_DELTA_BLOCKED_MISSING_INPUT = "V19_DECISION_DELTA_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19DecisionDeltaConfig:
    base_workbench_json: str | Path
    rerun_workbench_json: str | Path
    filled_values_count: int = 0
    output_dir: str | Path = "outputs/analysis_preview/v19_completion_rerun"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DecisionDeltaResult:
    decision_delta_status: str
    decision_delta_report_path: str
    decision_delta_json_path: str
    blocker_delta_path: str
    market_family_delta_path: str
    score_tree_delta_path: str
    readiness_delta_path: str
    base_final_decision_class: str
    rerun_final_decision_class: str
    decision_class_changed: bool
    base_evidence_readiness_score: int
    rerun_evidence_readiness_score: int
    evidence_readiness_delta: int
    base_conflict_score: str
    rerun_conflict_score: str
    conflict_score_changed: bool
    base_promotion_allowed: bool
    rerun_promotion_allowed: bool
    promotion_changed: bool
    blockers_removed: str
    blockers_added: str
    blockers_remaining: str
    market_families_upgraded: str
    market_families_downgraded: str
    score_tree_changes: str
    upgrade_reason: str
    downgrade_reason: str
    final_delta_summary: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19DecisionDeltaRunner:
    def __init__(self, config: V19DecisionDeltaConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19DecisionDeltaResult:
        base = _read_json(_resolve(self.config.base_workbench_json, self.base))
        rerun = _read_json(_resolve(self.config.rerun_workbench_json, self.base))
        if not base or not rerun:
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        delta = _delta(base, rerun, self.config.filled_values_count)
        paths = {
            "decision_delta_report": out / "decision_delta_report.md",
            "decision_delta_json": out / "decision_delta.json",
            "blocker_delta": out / "blocker_delta.md",
            "market_family_delta": out / "market_family_delta.md",
            "score_tree_delta": out / "score_tree_delta.md",
            "readiness_delta": out / "readiness_delta.md",
        }
        payload = {"base": _summary(base), "rerun": _summary(rerun), "delta": delta, "safety": _safety()}
        paths["decision_delta_json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths["decision_delta_report"].write_text(_decision_report(delta), encoding="utf-8")
        paths["blocker_delta"].write_text(_blocker_report(delta), encoding="utf-8")
        paths["market_family_delta"].write_text(_market_report(delta), encoding="utf-8")
        paths["score_tree_delta"].write_text(_score_report(delta), encoding="utf-8")
        paths["readiness_delta"].write_text(_readiness_report(delta), encoding="utf-8")
        return V19DecisionDeltaResult(
            V19_DECISION_DELTA_PREVIEW_READY,
            str(paths["decision_delta_report"].resolve()),
            str(paths["decision_delta_json"].resolve()),
            str(paths["blocker_delta"].resolve()),
            str(paths["market_family_delta"].resolve()),
            str(paths["score_tree_delta"].resolve()),
            str(paths["readiness_delta"].resolve()),
            delta["base_final_decision_class"],
            delta["rerun_final_decision_class"],
            delta["decision_class_changed"],
            delta["base_evidence_readiness_score"],
            delta["rerun_evidence_readiness_score"],
            delta["evidence_readiness_delta"],
            delta["base_conflict_score"],
            delta["rerun_conflict_score"],
            delta["conflict_score_changed"],
            delta["base_promotion_allowed"],
            delta["rerun_promotion_allowed"],
            delta["promotion_changed"],
            " | ".join(delta["blockers_removed"]),
            " | ".join(delta["blockers_added"]),
            " | ".join(delta["blockers_remaining"]),
            " | ".join(delta["market_families_upgraded"]),
            " | ".join(delta["market_families_downgraded"]),
            " | ".join(delta["score_tree_changes"]),
            delta["upgrade_reason"],
            delta["downgrade_reason"],
            delta["final_delta_summary"],
            False,
            False,
            False,
            False,
            V19_DECISION_DELTA_PREVIEW_READY,
        )

    def _blocked(self) -> V19DecisionDeltaResult:
        return V19DecisionDeltaResult(V19_DECISION_DELTA_BLOCKED_MISSING_INPUT, "", "", "", "", "", "", "", "", False, 0, 0, 0, "", "", False, False, False, False, "", "", "", "", "", "", "", "", "", False, False, False, False, V19_DECISION_DELTA_BLOCKED_MISSING_INPUT)


def _delta(base: dict[str, object], rerun: dict[str, object], filled_values_count: int) -> dict[str, object]:
    base_pr = base.get("production_readiness", {})
    rerun_pr = rerun.get("production_readiness", {})
    base_blockers = set(base_pr.get("critical_blockers", []) or [])
    rerun_blockers = set(rerun_pr.get("critical_blockers", []) or [])
    base_families = _families(base)
    rerun_families = _families(rerun)
    upgraded = [family for family in base_families if _rank(rerun_families.get(family, "")) > _rank(base_families.get(family, ""))]
    downgraded = [family for family in base_families if _rank(rerun_families.get(family, "")) < _rank(base_families.get(family, ""))]
    base_score = int(base_pr.get("readiness_score", 0) or 0)
    rerun_score = int(rerun_pr.get("readiness_score", 0) or 0)
    decision_changed = str(base_pr.get("final_decision_class", "")) != str(rerun_pr.get("final_decision_class", ""))
    promotion_changed = _bool(base_pr.get("promotion_allowed", False)) != _bool(rerun_pr.get("promotion_allowed", False))
    if filled_values_count == 0:
        summary = "No decision change because no filled completion values were provided."
    elif decision_changed or promotion_changed:
        summary = "Decision state changed after filled completion values were applied."
    elif base_blockers != rerun_blockers:
        summary = "Some blockers improved, but promotion remains blocked."
    else:
        summary = "No material decision change after rerun."
    return {
        "base_final_decision_class": str(base_pr.get("final_decision_class", "")),
        "rerun_final_decision_class": str(rerun_pr.get("final_decision_class", "")),
        "decision_class_changed": decision_changed,
        "base_evidence_readiness_score": base_score,
        "rerun_evidence_readiness_score": rerun_score,
        "evidence_readiness_delta": rerun_score - base_score,
        "base_conflict_score": str(base_pr.get("conflict_score", "")),
        "rerun_conflict_score": str(rerun_pr.get("conflict_score", "")),
        "conflict_score_changed": str(base_pr.get("conflict_score", "")) != str(rerun_pr.get("conflict_score", "")),
        "base_promotion_allowed": _bool(base_pr.get("promotion_allowed", False)),
        "rerun_promotion_allowed": _bool(rerun_pr.get("promotion_allowed", False)),
        "promotion_changed": promotion_changed,
        "blockers_removed": sorted(base_blockers - rerun_blockers),
        "blockers_added": sorted(rerun_blockers - base_blockers),
        "blockers_remaining": sorted(base_blockers & rerun_blockers),
        "market_families_upgraded": upgraded,
        "market_families_downgraded": downgraded,
        "score_tree_changes": [] if base.get("promotion_simulation") == rerun.get("promotion_simulation") else ["score tree payload changed"],
        "upgrade_reason": "Promotion candidate may be unlocked if conflict score and market alignment allow it." if promotion_changed or upgraded else "No upgrade detected.",
        "downgrade_reason": "Downgrade if filled data contradicts Atalanta edge." if downgraded else "No downgrade detected.",
        "final_delta_summary": summary,
    }


def _decision_report(delta: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Decision Delta Report",
        "",
        "## 1. Summary",
        f"- base final_decision_class: {delta['base_final_decision_class']}",
        f"- rerun final_decision_class: {delta['rerun_final_decision_class']}",
        f"- changed: {str(delta['decision_class_changed']).lower()}",
        "",
        "## 2. Readiness Delta",
        f"- base score: {delta['base_evidence_readiness_score']}",
        f"- rerun score: {delta['rerun_evidence_readiness_score']}",
        f"- delta: {delta['evidence_readiness_delta']}",
        "",
        "## 3. Promotion Delta",
        f"- base promotion_allowed: {str(delta['base_promotion_allowed']).lower()}",
        f"- rerun promotion_allowed: {str(delta['rerun_promotion_allowed']).lower()}",
        f"- changed: {str(delta['promotion_changed']).lower()}",
        "",
        "## 4. Blocker Delta",
        _blocker_table(delta),
        "",
        "## 5. Market Family Delta",
        f"- upgraded: {', '.join(delta['market_families_upgraded']) or 'none'}",
        f"- downgraded: {', '.join(delta['market_families_downgraded']) or 'none'}",
        "",
        "## 6. Score Tree Delta",
        f"- branch changes: {', '.join(delta['score_tree_changes']) or 'none'}",
        "- exact score still blocked: yes",
        "",
        "## 7. Final Explanation",
        str(delta["final_delta_summary"]),
        "",
        "## 8. Safety Footer",
        "No stake. No ROI. No automatic betting.",
        "",
    ])


def _blocker_report(delta: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Blocker Delta",
        "",
        f"- removed blockers: {', '.join(delta['blockers_removed']) or 'none'}",
        f"- remaining blockers: {', '.join(delta['blockers_remaining']) or 'none'}",
        f"- newly added blockers: {', '.join(delta['blockers_added']) or 'none'}",
        "- critical blockers still active: " + (", ".join(delta["blockers_remaining"]) or "none"),
        f"- impact on promotion: promotion_allowed remains {str(delta['rerun_promotion_allowed']).lower()}",
        "",
    ])


def _market_report(delta: dict[str, object]) -> str:
    families = ["1X2", "Double Chance", "DNB", "Over/Under", "BTTS", "Score Family", "No-Bet"]
    rows = [{"market family": fam, "base status": "unchanged", "rerun status": "unchanged", "changed": "no", "explanation": "No filled values changed this family."} for fam in families]
    return "# v1.9 Market Family Delta\n\n" + _table(pd.DataFrame(rows)) + "\n"


def _score_report(delta: dict[str, object]) -> str:
    return "# v1.9 Score Tree Delta\n\n- branch changes: " + (", ".join(delta["score_tree_changes"]) or "none") + "\n- exact score still blocked: yes\n"


def _readiness_report(delta: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Readiness Delta",
        "",
        f"- evidence readiness before: {delta['base_evidence_readiness_score']}",
        f"- evidence readiness after: {delta['rerun_evidence_readiness_score']}",
        f"- production readiness before: {delta['base_final_decision_class']}",
        f"- production readiness after: {delta['rerun_final_decision_class']}",
        f"- conflict score before: {delta['base_conflict_score']}",
        f"- conflict score after: {delta['rerun_conflict_score']}",
        f"- promotion status before: {str(delta['base_promotion_allowed']).lower()}",
        f"- promotion status after: {str(delta['rerun_promotion_allowed']).lower()}",
        "",
    ])


def _blocker_table(delta: dict[str, object]) -> str:
    blockers = sorted(set(delta["blockers_removed"]) | set(delta["blockers_added"]) | set(delta["blockers_remaining"]))
    rows = []
    for blocker in blockers:
        rows.append({
            "blocker": blocker,
            "base status": "active" if blocker in delta["blockers_removed"] or blocker in delta["blockers_remaining"] else "inactive",
            "rerun status": "active" if blocker in delta["blockers_added"] or blocker in delta["blockers_remaining"] else "inactive",
            "changed": "yes" if blocker in delta["blockers_removed"] or blocker in delta["blockers_added"] else "no",
            "explanation": "No filled completion values changed this blocker." if blocker in delta["blockers_remaining"] else "Blocker status changed.",
        })
    return _table(pd.DataFrame(rows))


def _families(payload: dict[str, object]) -> dict[str, str]:
    records = payload.get("analysis_suite", {}).get("market_family_read", [])
    if not records:
        records = payload.get("analysis_suite", {}).get("market_family_matrix", [])
    result = {}
    machine = payload.get("analysis_suite", {})
    if isinstance(machine, dict):
        nested = machine.get("market_family_read")
        if isinstance(nested, list):
            records = nested
    for row in records if isinstance(records, list) else []:
        result[str(row.get("market_family", ""))] = str(row.get("status", ""))
    return result


def _rank(status: str) -> int:
    return {"NO_BET": 0, "BLOCKED": 1, "PARTIAL": 2, "READY": 3, "BET_CANDIDATE_PREVIEW": 4}.get(status, 0)


def _summary(payload: dict[str, object]) -> dict[str, object]:
    return {"match": payload.get("match", {}), "production_readiness": payload.get("production_readiness", {})}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
