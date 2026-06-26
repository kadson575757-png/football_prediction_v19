# -*- coding: utf-8 -*-
"""v1.9 match pack contract and validation preview."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_METADATA = ["match_id", "home_team", "away_team", "competition", "season", "match_date", "input_dir"]
OPTIONAL_METADATA = ["manual_evidence_completion", "notes", "tags", "source_type"]
REQUIRED_EVIDENCE_GROUPS = ["team_xg", "player_xg_xa", "match_stats", "formation_or_tactical", "odds_current"]
CRITICAL_PROMOTION_GROUPS = ["recent_form", "big_chances", "availability", "opening_closing_odds", "dnb_ou_market", "referee_weather", "tactical_details"]
ALL_EVIDENCE_GROUPS = REQUIRED_EVIDENCE_GROUPS + CRITICAL_PROMOTION_GROUPS

V19_MATCH_PACK_CONTRACT_PREVIEW_READY = "V19_MATCH_PACK_CONTRACT_PREVIEW_READY"


@dataclass(frozen=True)
class MatchPackValidationResult:
    match_id: str
    input_dir: str
    valid_pack: bool
    metadata_status: str
    files_detected_count: int
    evidence_groups_detected: str
    evidence_groups_missing: str
    critical_groups_missing: str
    field_mapping_estimate: int
    can_build_intake: bool
    can_run_workbench: bool
    can_run_batch_os: bool
    health_status: str
    warnings: str
    errors: str
    synthetic_demo_pack: bool
    not_real_match_data: bool
    not_for_prediction: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_match_pack(row: dict[str, object], *, base_dir: str | Path = ".") -> MatchPackValidationResult:
    base = Path(base_dir).resolve()
    missing_metadata = [field for field in REQUIRED_METADATA if not str(row.get(field, "")).strip()]
    input_dir = _resolve(str(row.get("input_dir", "")), base) if str(row.get("input_dir", "")).strip() else base / "__missing_input_dir__"
    files = _evidence_files(input_dir)
    detected = detect_evidence_groups(files)
    missing_required = [group for group in REQUIRED_EVIDENCE_GROUPS if group not in detected]
    missing_critical = [group for group in CRITICAL_PROMOTION_GROUPS if group not in detected]
    metadata_status = "READY" if not missing_metadata else "MISSING_REQUIRED_METADATA"
    errors: list[str] = []
    warnings: list[str] = []
    if missing_metadata:
        errors.append("missing metadata: " + ", ".join(missing_metadata))
    if not input_dir.exists():
        errors.append("input_dir does not exist")
    if not files:
        errors.append("no evidence files detected")
    if missing_required:
        warnings.append("missing required evidence groups: " + ", ".join(missing_required))
    if missing_critical:
        warnings.append("promotion-critical groups missing: " + ", ".join(missing_critical))
    can_build = not missing_metadata and input_dir.exists() and bool(files)
    can_workbench = can_build and not missing_required
    valid = can_build and not errors
    if missing_metadata or not input_dir.exists():
        health = "INVALID"
    elif not files or len(missing_required) >= 3:
        health = "BLOCKED"
    elif missing_required or missing_critical:
        health = "PARTIAL"
    else:
        health = "READY"
    synthetic = _bool(row.get("synthetic_demo_pack", False))
    return MatchPackValidationResult(
        match_id=str(row.get("match_id", "")).strip(),
        input_dir=str(input_dir),
        valid_pack=valid,
        metadata_status=metadata_status,
        files_detected_count=len(files),
        evidence_groups_detected=" | ".join(detected),
        evidence_groups_missing=" | ".join([group for group in ALL_EVIDENCE_GROUPS if group not in detected]),
        critical_groups_missing=" | ".join(missing_critical),
        field_mapping_estimate=len(detected) * 5 + len(files),
        can_build_intake=can_build,
        can_run_workbench=can_workbench,
        can_run_batch_os=can_workbench,
        health_status=health,
        warnings=" | ".join(warnings),
        errors=" | ".join(errors),
        synthetic_demo_pack=synthetic,
        not_real_match_data=synthetic or _bool(row.get("not_real_match_data", False)),
        not_for_prediction=synthetic or _bool(row.get("not_for_prediction", False)),
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        staking_logic_enabled=False,
        roi_logic_enabled=False,
    )


def detect_evidence_groups(files: list[Path]) -> list[str]:
    groups: set[str] = set()
    for path in files:
        name = path.name.lower()
        if "team-statistics" in name or "statistics" in name:
            groups.update({"team_xg", "match_stats", "formation_or_tactical", "odds_current"})
        if "team-players" in name or "players" in name:
            groups.add("player_xg_xa")
        if "recent" in name or "form" in name:
            groups.add("recent_form")
        if "big-chance" in name or "big_chance" in name:
            groups.add("big_chances")
        if "availability" in name or "lineup" in name or "injury" in name:
            groups.add("availability")
        if "opening" in name or "closing" in name or "market-movement" in name:
            groups.add("opening_closing_odds")
        if "dnb" in name or "over-under" in name or "ou-market" in name:
            groups.add("dnb_ou_market")
        if "referee" in name or "weather" in name:
            groups.add("referee_weather")
        if "tactical" in name or "fatigue" in name or "set-piece" in name:
            groups.add("tactical_details")
    return [group for group in ALL_EVIDENCE_GROUPS if group in groups]


def _evidence_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists() or not input_dir.is_dir():
        return []
    return sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in {".xlsx", ".xls", ".csv", ".json"}])


def _resolve(path: str, base: Path) -> Path:
    p = Path(path)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
