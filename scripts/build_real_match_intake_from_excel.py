# -*- coding: utf-8 -*-
"""Build a preview-only manual real-match intake CSV from local Excel evidence."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.real_match_intake_schema_preview import INTAKE_COLUMNS  # noqa: E402

BUILDER_READY = "REAL_MATCH_INTAKE_EXCEL_BUILDER_READY"
BUILDER_NO_EVIDENCE_FILES = "REAL_MATCH_INTAKE_EXCEL_BUILDER_NO_EVIDENCE_FILES"
BUILDER_INCOMPLETE_REQUIRED_FIELDS = "REAL_MATCH_INTAKE_EXCEL_BUILDER_INCOMPLETE_REQUIRED_FIELDS"
BUILDER_UNSAFE_PATH = "REAL_MATCH_INTAKE_EXCEL_BUILDER_BLOCKED_UNSAFE_PATH"
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
SUMMARY_DIR = Path("outputs/analysis_preview/manual_intake_builder")
REQUIRED_VALUE_COLUMNS = ["match_date", "competition", "season", "home_team", "away_team"]


@dataclass(frozen=True)
class ExcelEvidence:
    path: Path
    role: str
    sheets: dict[str, pd.DataFrame]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="data/manual/evidence")
    parser.add_argument("--output", default="data/manual/real_match_intake.csv")
    parser.add_argument("--home-team")
    parser.add_argument("--away-team")
    parser.add_argument("--competition")
    parser.add_argument("--season")
    parser.add_argument("--match-date")
    parser.add_argument("--country", default="")
    parser.add_argument("--venue-name", default="")
    parser.add_argument("--timezone", default="")
    parser.add_argument("--neutral-venue", default="false")
    parser.add_argument("--allow-empty-output", action="store_true")
    parser.add_argument("--allow-incomplete-output", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_real_match_intake_from_excel(
    *,
    input_dir: str | Path = "data/manual/evidence",
    output: str | Path = "data/manual/real_match_intake.csv",
    home_team: str | None = None,
    away_team: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    match_date: str | None = None,
    country: str = "",
    venue_name: str = "",
    timezone: str = "",
    neutral_venue: str = "false",
    allow_empty_output: bool = False,
    allow_incomplete_output: bool = False,
    force: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    evidence_dir = _resolve(input_dir, base)
    output_path = _resolve(output, base)
    summary_dir = base / SUMMARY_DIR
    if evidence_dir is None or output_path is None or _unsafe(evidence_dir) or _unsafe(output_path):
        return _blocked(BUILDER_UNSAFE_PATH, summary_dir)

    evidence = _load_evidence(evidence_dir)
    row = {column: "" for column in INTAKE_COLUMNS}
    row.update({
        "match_date": match_date or "",
        "competition": competition or "",
        "season": season or "",
        "home_team": home_team or "",
        "away_team": away_team or "",
        "country": country,
        "venue_name": venue_name,
        "timezone": timezone,
        "neutral_venue": neutral_venue,
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    })
    diagnostics = {
        "input_files": [str(item.path) for item in evidence],
        "sheets": [],
        "columns_by_file": {},
        "samples_by_file": {},
        "mapped_fields": set(),
        "ambiguous_fields": set(),
        "evidence_notes": [],
    }

    role_positions = _role_positions(evidence)
    for item in evidence:
        diagnostics["columns_by_file"][str(item.path)] = {}
        diagnostics["samples_by_file"][str(item.path)] = {}
        for sheet_name, frame in item.sheets.items():
            diagnostics["sheets"].append(f"{item.path.name}:{sheet_name}")
            diagnostics["columns_by_file"][str(item.path)][sheet_name] = list(frame.columns)
            diagnostics["samples_by_file"][str(item.path)][sheet_name] = _sample_rows(frame)
        if item.role == "team_statistics":
            _map_team_statistics(row, item, diagnostics, role_positions.get(item.path, ""))
        elif item.role == "team_players":
            _map_team_players(row, item, diagnostics, role_positions.get(item.path, ""))

    _apply_context_defaults(row, home_team, away_team, competition, season, match_date, country, venue_name, timezone, neutral_venue)
    if not row["cross_provider_match_key"] and all(row.get(c) for c in ["competition", "season", "home_team", "away_team", "match_date"]):
        row["cross_provider_match_key"] = _manual_key(row)
        diagnostics["mapped_fields"].add("cross_provider_match_key")
    _finalize_quality(row, evidence, diagnostics)

    missing_required = [column for column in REQUIRED_VALUE_COLUMNS if _blank(row.get(column, ""))]
    missing_optional = [column for column in INTAKE_COLUMNS if column not in REQUIRED_VALUE_COLUMNS and _blank(row.get(column, ""))]
    row["missing_required_fields_count"] = len(missing_required)
    row["missing_optional_fields_count"] = len(missing_optional)
    row["manual_review_required"] = bool(missing_required or missing_optional)

    status = BUILDER_READY
    output_written = False
    existing_output_protected = False
    write_block_reason = ""
    if not evidence:
        status = BUILDER_NO_EVIDENCE_FILES
        if allow_empty_output:
            output_written = _write_intake(output_path, row)
        else:
            existing_output_protected = output_path.exists()
            write_block_reason = "No Excel evidence files found; existing output protected and no empty intake was written."
    elif missing_required and not (allow_incomplete_output or force):
        status = BUILDER_INCOMPLETE_REQUIRED_FIELDS
        existing_output_protected = output_path.exists()
        write_block_reason = "Required match context fields are missing; existing output protected and incomplete intake was not written."
    else:
        output_written = _write_intake(output_path, row)
    summary = _write_summary(
        summary_dir,
        status,
        output_path,
        evidence,
        diagnostics,
        sorted(missing_required),
        sorted(missing_optional),
        row,
        input_dir=evidence_dir,
        output_written=output_written,
        existing_output_protected=existing_output_protected,
        write_block_reason=write_block_reason,
    )
    return {
        "real_match_intake_excel_builder_status": status,
        "input_files_detected": len(evidence),
        "fields_mapped_count": len(diagnostics["mapped_fields"]),
        "missing_required_fields_count": len(missing_required),
        "missing_optional_fields_count": len(missing_optional),
        "manual_review_required": bool(row["manual_review_required"]),
        "output_written": output_written,
        "existing_output_protected": existing_output_protected,
        "write_block_reason": write_block_reason,
        "output_path": str(output_path.resolve()),
        "summary_csv_path": str(summary["csv"].resolve()),
        "summary_md_path": str(summary["md"].resolve()),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "recommendation": status,
    }


def _load_evidence(input_dir: Path) -> list[ExcelEvidence]:
    if not input_dir.exists() or not input_dir.is_dir():
        return []
    files = sorted(set(input_dir.glob("team-statistics*.xlsx")) | set(input_dir.glob("team-players*.xlsx")))
    evidence = []
    for path in files:
        role = "team_statistics" if path.name.lower().startswith("team-statistics") else "team_players"
        try:
            sheets = pd.read_excel(path, sheet_name=None)
        except Exception:
            sheets = {}
        normalized = {_sheet: _normalize_frame(frame) for _sheet, frame in sheets.items()}
        evidence.append(ExcelEvidence(path=path.resolve(), role=role, sheets=normalized))
    return evidence


def _role_positions(evidence: list[ExcelEvidence]) -> dict[Path, str]:
    positions = {}
    for role in ["team_statistics", "team_players"]:
        items = [item for item in evidence if item.role == role]
        midpoint = len(items) // 2
        for index, item in enumerate(items):
            if len(items) >= 2 and len(items) % 2 == 0:
                positions[item.path] = "away" if index < midpoint else "home"
            else:
                positions[item.path] = ""
    return positions


def _map_team_statistics(row: dict[str, object], item: ExcelEvidence, diagnostics: dict[str, object], inferred_prefix: str = "") -> None:
    for frame in item.sheets.values():
        if frame.empty:
            continue
        home = _team_row(frame, str(row.get("home_team", "")))
        away = _team_row(frame, str(row.get("away_team", "")))
        inferred_from_order = home is None and away is None and bool(inferred_prefix)
        if home is None and away is None and inferred_prefix:
            diagnostics["ambiguous_fields"].add(f"{item.path.name}:team_identity_inferred_from_export_order")
            home = frame.iloc[0] if inferred_prefix == "home" else None
            away = frame.iloc[0] if inferred_prefix == "away" else None
        for prefix, team_row in [("home", home), ("away", away)]:
            if team_row is None:
                continue
            if not inferred_from_order:
                _assign(row, f"{prefix}_team_xg_for", _first_value(team_row, ["xg_for", "xg", "expected_goals_for", "team_xg_for"]), diagnostics)
                _assign(row, f"{prefix}_team_xg_against", _first_value(team_row, ["xg_against", "xga", "expected_goals_against", "team_xg_against"]), diagnostics)
                _assign(row, f"{prefix}_venue_xg_for", _first_value(team_row, ["venue_xg_for", "home_xg_for", "away_xg_for"]), diagnostics)
                _assign(row, f"{prefix}_venue_xg_against", _first_value(team_row, ["venue_xg_against", "home_xg_against", "away_xg_against"]), diagnostics)
                _assign(row, f"{prefix}_recent_xg_for", _first_value(team_row, ["recent_xg_for", "last5_xg_for", "last_5_xg_for"]), diagnostics)
                _assign(row, f"{prefix}_recent_xg_against", _first_value(team_row, ["recent_xg_against", "recent_xga", "last5_xga"]), diagnostics)
                _assign(row, f"{prefix}_formation", _first_value(team_row, ["formation", "default_formation"]), diagnostics)
                _assign(row, f"{prefix}_tactical_profile", _first_value(team_row, ["tactical_profile", "team_style", "style"]), diagnostics)
                _assign(row, f"{prefix}_set_piece_xg_for", _first_value(team_row, ["set_piece_xg_for", "sp_xg_for"]), diagnostics)
                _assign(row, f"{prefix}_set_piece_xg_against", _first_value(team_row, ["set_piece_xg_against", "sp_xg_against"]), diagnostics)
                _assign(row, f"{prefix}_set_piece_xg_ratio", _first_value(team_row, ["set_piece_xg_ratio", "sp_xg_ratio"]), diagnostics)
                _assign(row, f"{prefix}_rest_days", _first_value(team_row, ["rest_days", f"{prefix}_rest_days"]), diagnostics)
                _assign(row, f"{prefix}_travel_fatigue_note", _first_value(team_row, ["travel_fatigue_note", "fatigue_note"]), diagnostics)
                _assign(row, f"{prefix}_missing_players", _first_value(team_row, ["missing_players", "injuries", "absences"]), diagnostics)
                _assign(row, f"{prefix}_key_absences", _first_value(team_row, ["key_absences", "key_absence_count"]), diagnostics)
                _assign(row, f"{prefix}_goalkeeper_status", _first_value(team_row, ["goalkeeper_status", "gk_status"]), diagnostics)
            _map_structured_team_stats(row, prefix, frame, diagnostics)
        for target, aliases in {
            "venue_name": ["venue", "venue_name", "stadium"],
            "country": ["country"],
            "timezone": ["timezone"],
            "tactical_matchup_score": ["tactical_matchup_score", "matchup_score"],
            "formation_matchup_note": ["formation_matchup_note", "formation_note"],
            "pressing_matchup_note": ["pressing_matchup_note", "pressing_note"],
            "transition_matchup_note": ["transition_matchup_note", "transition_note"],
            "defensive_line_risk_note": ["defensive_line_risk_note", "defensive_risk_note"],
            "do_so_fatigue_modifier": ["do_so_fatigue_modifier", "fatigue_modifier"],
            "xg_zone_correction_flag": ["xg_zone_correction_flag"],
            "xg_zone_correction_note": ["xg_zone_correction_note"],
        }.items():
            value = _first_nonblank(frame, aliases)
            _assign(row, target, value, diagnostics)
        _add_statistics_note(row, frame, item.path.name, diagnostics)


def _map_team_players(row: dict[str, object], item: ExcelEvidence, diagnostics: dict[str, object], inferred_prefix: str = "") -> None:
    for frame in item.sheets.values():
        if frame.empty:
            continue
        team_col = _find_column(frame, ["team", "squad", "club"])
        prefixes = []
        if team_col is None and inferred_prefix:
            diagnostics["ambiguous_fields"].add(f"{item.path.name}:team_identity_inferred_from_export_order")
            prefixes = [(inferred_prefix, frame)]
        elif team_col is not None:
            for prefix, team in [("home", str(row.get("home_team", ""))), ("away", str(row.get("away_team", "")))]:
                if not team:
                    continue
                subset = frame[frame[team_col].astype(str).str.lower() == team.lower()]
                if not subset.empty:
                    prefixes.append((prefix, subset))
        for prefix, subset in prefixes:
            team = str(row.get(f"{prefix}_team", ""))
            if not team:
                continue
            _assign(row, f"{prefix}_player_xg_total", _sum_column(subset, ["xg", "player_xg", "npxg"]), diagnostics)
            _assign(row, f"{prefix}_player_xa_total", _sum_column(subset, ["xa", "xag", "player_xa"]), diagnostics)
            _assign(row, f"{prefix}_big_chances", _sum_column(subset, ["big_chances", "big_chances_created"]), diagnostics)
            scorer = _top_player(subset, ["goals", "g", "xg"], ["player", "player_name", "name"])
            creator = _top_player(subset, ["assists", "a", "xa", "xag"], ["player", "player_name", "name"])
            _assign(row, f"{prefix}_main_scorer", scorer, diagnostics)
            _assign(row, f"{prefix}_main_creator", creator, diagnostics)
            _add_player_note(row, prefix, subset, item.path.name, diagnostics)


def _map_structured_team_stats(row: dict[str, object], prefix: str, frame: pd.DataFrame, diagnostics: dict[str, object]) -> None:
    statistic_col = _find_column(frame, ["statistic", "category", "type"])
    if statistic_col is None:
        return
    set_piece = _statistic_row(frame, statistic_col, ["set piece"])
    if set_piece is not None:
        _assign(row, f"{prefix}_set_piece_xg_for", _first_value(set_piece, ["xg"]), diagnostics)
        _assign(row, f"{prefix}_set_piece_xg_against", _first_value(set_piece, ["xga"]), diagnostics)
        ratio = _ratio(_first_value(set_piece, ["xg"]), _first_value(set_piece, ["xga"]))
        _assign(row, f"{prefix}_set_piece_xg_ratio", ratio, diagnostics)
    formation = _best_formation(frame, statistic_col)
    _assign(row, f"{prefix}_formation", formation, diagnostics)
    totals = _team_totals_from_breakdown(frame)
    if totals:
        _assign(row, f"{prefix}_team_xg_for", totals.get("xg", ""), diagnostics)
        _assign(row, f"{prefix}_team_xg_against", totals.get("xga", ""), diagnostics)


def _statistic_row(frame: pd.DataFrame, statistic_col: str, needles: list[str]) -> pd.Series | None:
    lowered = frame[statistic_col].astype(str).str.lower()
    for needle in needles:
        matches = frame[lowered == needle.lower()]
        if not matches.empty:
            return matches.iloc[0]
    return None


def _best_formation(frame: pd.DataFrame, statistic_col: str) -> str:
    if "min" not in frame.columns:
        return ""
    candidates = frame[frame[statistic_col].astype(str).str.match(r"^\d-\d-\d", na=False)].copy()
    if candidates.empty:
        return ""
    candidates["_min"] = pd.to_numeric(candidates["min"], errors="coerce").fillna(0)
    return str(candidates.sort_values("_min", ascending=False).iloc[0][statistic_col])


def _team_totals_from_breakdown(frame: pd.DataFrame) -> dict[str, float]:
    statistic_col = _find_column(frame, ["statistic"])
    xg_col = _find_column(frame, ["xg"])
    xga_col = _find_column(frame, ["xga"])
    if statistic_col is None or xg_col is None or xga_col is None:
        return {}
    stats = frame[statistic_col].astype(str).str.lower()
    if stats.str.contains("open play|from corner|set piece|direct freekick|penalty", regex=True).any():
        use = frame[stats.str.contains("open play|from corner|set piece|direct freekick|penalty", regex=True)]
        return {
            "xg": round(float(pd.to_numeric(use[xg_col], errors="coerce").fillna(0).sum()), 2),
            "xga": round(float(pd.to_numeric(use[xga_col], errors="coerce").fillna(0).sum()), 2),
        }
    return {}


def _add_statistics_note(row: dict[str, object], frame: pd.DataFrame, file_name: str, diagnostics: dict[str, object]) -> None:
    statistic_col = _find_column(frame, ["statistic"])
    if statistic_col is None:
        return
    stats = ", ".join(str(value) for value in frame[statistic_col].head(6).tolist())
    note = f"{file_name}: statistic groups observed: {stats}"
    diagnostics["evidence_notes"].append(note)


def _add_player_note(row: dict[str, object], prefix: str, frame: pd.DataFrame, file_name: str, diagnostics: dict[str, object]) -> None:
    player_col = _find_column(frame, ["player", "player_name", "name"])
    if player_col is None:
        return
    names = ", ".join(str(value) for value in frame[player_col].head(5).tolist())
    team = row.get(f"{prefix}_team", prefix)
    diagnostics["evidence_notes"].append(f"{file_name}: top {team} players observed: {names}")


def _ratio(numerator: object, denominator: object) -> object:
    top = pd.to_numeric(pd.Series([numerator]), errors="coerce").iloc[0]
    bottom = pd.to_numeric(pd.Series([denominator]), errors="coerce").iloc[0]
    if pd.isna(top) or pd.isna(bottom) or float(bottom) == 0:
        return ""
    return round(float(top) / float(bottom), 2)


def _apply_context_defaults(row: dict[str, object], home: str | None, away: str | None, competition: str | None, season: str | None, date: str | None, country: str, venue: str, timezone: str, neutral: str) -> None:
    for column, value in {
        "home_team": home,
        "away_team": away,
        "competition": competition,
        "season": season,
        "match_date": date,
        "country": country,
        "venue_name": venue,
        "timezone": timezone,
        "neutral_venue": neutral,
    }.items():
        if value and _blank(row.get(column, "")):
            row[column] = value


def _finalize_quality(row: dict[str, object], evidence: list[ExcelEvidence], diagnostics: dict[str, object]) -> None:
    stats = [item.path.name for item in evidence if item.role == "team_statistics"]
    players = [item.path.name for item in evidence if item.role == "team_players"]
    row["xg_source_note"] = "Mapped from local Excel evidence: " + ", ".join(stats) if stats else ""
    row["player_form_source_note"] = "Mapped from local Excel evidence: " + ", ".join(players) if players else ""
    row["tactical_source_note"] = "Mapped from local Excel evidence: " + ", ".join(stats) if stats else ""
    row["availability_source_note"] = "Mapped from local Excel evidence: " + ", ".join(stats) if stats else ""
    for column in ["xg_data_quality_status", "availability_data_quality_status", "player_form_data_quality_status", "tactical_data_quality_status"]:
        row[column] = "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    row["market_data_quality_status"] = "DIAGNOSTIC_READY_WITH_MISSING_OPTIONAL_FIELDS"
    evidence_notes = " | ".join(str(note) for note in diagnostics.get("evidence_notes", []))
    ambiguous = " | ".join(str(field) for field in sorted(diagnostics.get("ambiguous_fields", [])))
    note_parts = ["Generated from local Excel evidence; missing values remain blank and require manual review."]
    if evidence_notes:
        note_parts.append(f"Evidence notes: {evidence_notes}")
    if ambiguous:
        note_parts.append(f"Ambiguous fields: {ambiguous}")
    row["evidence_quality_note"] = " ".join(note_parts)
    row["analyst_note"] = "Generated by build_real_match_intake_from_excel.py; preview-only intake."


def _write_intake(output_path: Path, row: dict[str, object]) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row], columns=INTAKE_COLUMNS).to_csv(output_path, index=False)
    return True


def _write_summary(
    summary_dir: Path,
    status: str,
    output_path: Path,
    evidence: list[ExcelEvidence],
    diagnostics: dict[str, object],
    missing_required: list[str],
    missing_optional: list[str],
    row: dict[str, object],
    *,
    input_dir: Path,
    output_written: bool,
    existing_output_protected: bool,
    write_block_reason: str,
) -> dict[str, Path]:
    summary_dir.mkdir(parents=True, exist_ok=True)
    csv_path = summary_dir / "intake_builder_summary.csv"
    md_path = summary_dir / "intake_builder_summary.md"
    summary_row = {
        "real_match_intake_excel_builder_status": status,
        "input_files_detected": len(evidence),
        "sheets_detected": len(diagnostics["sheets"]),
        "fields_mapped_count": len(diagnostics["mapped_fields"]),
        "ambiguous_fields_count": len(diagnostics["ambiguous_fields"]),
        "evidence_notes_count": len(diagnostics["evidence_notes"]),
        "missing_required_fields_count": len(missing_required),
        "missing_optional_fields_count": len(missing_optional),
        "manual_review_required": bool(row.get("manual_review_required", True)),
        "output_written": output_written,
        "existing_output_protected": existing_output_protected,
        "write_block_reason": write_block_reason,
        "output_path": str(output_path.resolve()),
        "network_calls_enabled": False,
        "prediction_logic_enabled": False,
        "betting_logic_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "recommendation": status,
    }
    pd.DataFrame([summary_row]).to_csv(csv_path, index=False)
    columns_lines = []
    for file_path, sheets in diagnostics["columns_by_file"].items():
        columns_lines.append(f"- {Path(file_path).name}")
        for sheet, columns in sheets.items():
            columns_lines.append(f"  - {sheet}: {', '.join(map(str, columns))}")
    sample_lines = []
    for file_path, sheets in diagnostics["samples_by_file"].items():
        sample_lines.append(f"- {Path(file_path).name}")
        for sheet, rows in sheets.items():
            sample_lines.append(f"  - {sheet}:")
            if not rows:
                sample_lines.append("    - no rows sampled")
            for row_sample in rows:
                sample_lines.append(f"    - {row_sample}")
    md_path.write_text("\n".join([
        "# Real Match Intake Builder From Excel",
        "",
        f"- input_dir: {input_dir}",
        f"- output_written: {str(output_written).lower()}",
        f"- existing_output_protected: {str(existing_output_protected).lower()}",
        f"- write_block_reason: {write_block_reason or 'none'}",
        "",
        "## A. Input Files",
        f"- count: {len(evidence)}",
        *[f"- {Path(item.path).name} ({item.role})" for item in evidence],
        "",
        "## B. Sheets Found",
        *[f"- {sheet}" for sheet in diagnostics["sheets"]],
        "",
        "## C. Columns Found Per File",
        *columns_lines,
        "",
        "## D. Rows Sampled",
        *sample_lines,
        "",
        "## E. Fields Mapped",
        *[f"- {field}" for field in sorted(diagnostics["mapped_fields"])],
        "",
        "## F. Fields Missing",
        f"- required: {', '.join(missing_required) if missing_required else 'none'}",
        f"- optional_count: {len(missing_optional)}",
        "",
        "## G. Ambiguous Fields",
        *[f"- {field}" for field in sorted(diagnostics["ambiguous_fields"])],
        "",
        "## H. Evidence Notes Created",
        *[f"- {note}" for note in diagnostics["evidence_notes"]],
        "",
        "## I. Manual Review Decision",
        f"- {'yes' if row.get('manual_review_required') else 'no'}",
        "",
        "## Generated Output Path",
        f"- {output_path if output_written else 'not written'}",
        "",
        "## J. Recommended Next Command",
        "$PY scripts/run_match_analysis_preview.py --real-match-intake data/manual/real_match_intake.csv" if output_written else "Place team-statistics*.xlsx and team-players*.xlsx into data/manual/evidence and rerun the builder.",
        "",
        "Preview-only: no prediction, betting, staking, ROI, market-tier, or recommendation logic changed.",
        "",
    ]), encoding="utf-8")
    return {"csv": csv_path, "md": md_path}


def _blocked(status: str, summary_dir: Path) -> dict[str, object]:
    summary_dir.mkdir(parents=True, exist_ok=True)
    return {"real_match_intake_excel_builder_status": status, "recommendation": status}


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [_normalize_name(column) for column in normalized.columns]
    return normalized


def _sample_rows(frame: pd.DataFrame, limit: int = 5) -> list[str]:
    if frame.empty:
        return []
    samples = []
    for record in frame.head(limit).to_dict(orient="records"):
        parts = []
        for key, value in record.items():
            if not _blank(value):
                parts.append(f"{key}={value}")
        samples.append("; ".join(parts) if parts else "blank row")
    return samples


def _normalize_name(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return text.strip("_")


def _team_row(frame: pd.DataFrame, team: str) -> pd.Series | None:
    team_col = _find_column(frame, ["team", "squad", "club"])
    if team_col is None or not team:
        return None
    matches = frame[frame[team_col].astype(str).str.lower() == team.lower()]
    if matches.empty:
        return None
    return matches.iloc[0]


def _find_column(frame: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized_aliases = {_normalize_name(alias) for alias in aliases}
    for column in frame.columns:
        if _normalize_name(column) in normalized_aliases:
            return column
    return None


def _first_value(row: pd.Series, aliases: list[str]) -> object:
    for alias in aliases:
        column = _find_column(pd.DataFrame(columns=row.index), [alias])
        if column and not _blank(row.get(column, "")):
            return row.get(column, "")
    return ""


def _first_nonblank(frame: pd.DataFrame, aliases: list[str]) -> object:
    column = _find_column(frame, aliases)
    if column is None:
        return ""
    for value in frame[column].tolist():
        if not _blank(value):
            return value
    return ""


def _sum_column(frame: pd.DataFrame, aliases: list[str]) -> object:
    column = _find_column(frame, aliases)
    if column is None:
        return ""
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return ""
    return round(float(values.sum()), 2)


def _top_player(frame: pd.DataFrame, score_aliases: list[str], name_aliases: list[str]) -> str:
    score_col = _find_column(frame, score_aliases)
    name_col = _find_column(frame, name_aliases)
    if score_col is None or name_col is None:
        return ""
    ranked = frame.copy()
    ranked["_score"] = pd.to_numeric(ranked[score_col], errors="coerce").fillna(0)
    if ranked.empty:
        return ""
    top = ranked.sort_values("_score", ascending=False).iloc[0]
    name = str(top.get(name_col, "")).strip()
    score = top.get("_score", "")
    return f"{name} ({score:g})" if name else ""


def _assign(row: dict[str, object], column: str, value: object, diagnostics: dict[str, object]) -> None:
    if column not in row or _blank(value) or not _blank(row.get(column, "")):
        return
    row[column] = value
    diagnostics["mapped_fields"].add(column)


def _manual_key(row: dict[str, object]) -> str:
    return "manual-{competition}-{season}-{home}-{away}-{date}".format(
        competition=_slug(row.get("competition", "")),
        season=_slug(row.get("season", "")),
        home=_slug(row.get("home_team", "")),
        away=_slug(row.get("away_team", "")),
        date=str(row.get("match_date", ""))[:10],
    )


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return text.strip("-") or "unknown"


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_real_match_intake_from_excel(
        input_dir=args.input_dir,
        output=args.output,
        home_team=args.home_team,
        away_team=args.away_team,
        competition=args.competition,
        season=args.season,
        match_date=args.match_date,
        country=args.country,
        venue_name=args.venue_name,
        timezone=args.timezone,
        neutral_venue=args.neutral_venue,
        allow_empty_output=args.allow_empty_output,
        allow_incomplete_output=args.allow_incomplete_output,
        force=args.force,
        base_dir=args.base_dir,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
