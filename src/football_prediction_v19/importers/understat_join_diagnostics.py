# -*- coding: utf-8 -*-
"""Understat-to-football-data join diagnostics.

Phase 13.9 diagnostic/foundation only. This module explains exact-key join
coverage and writes reviewable alias/date candidates. It never infers, invents,
or fills xG values.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

UNDERSTAT_JOIN_READY = "UNDERSTAT_JOIN_READY"
UNDERSTAT_JOIN_BLOCKED_LOW_COVERAGE = "UNDERSTAT_JOIN_BLOCKED_LOW_COVERAGE"
UNDERSTAT_JOIN_BLOCKED_NO_TARGET = "UNDERSTAT_JOIN_BLOCKED_NO_TARGET"
UNDERSTAT_JOIN_BLOCKED_INVALID_SOURCE = "UNDERSTAT_JOIN_BLOCKED_INVALID_SOURCE"
UNDERSTAT_JOIN_BLOCKED_INVALID_TARGET = "UNDERSTAT_JOIN_BLOCKED_INVALID_TARGET"
UNDERSTAT_JOIN_NEEDS_TEAM_ALIAS_MAP = "UNDERSTAT_JOIN_NEEDS_TEAM_ALIAS_MAP"
UNDERSTAT_JOIN_NEEDS_DATE_ALIGNMENT_REVIEW = "UNDERSTAT_JOIN_NEEDS_DATE_ALIGNMENT_REVIEW"
UNDERSTAT_JOIN_INCONCLUSIVE = "UNDERSTAT_JOIN_INCONCLUSIVE"

READY_FOR_XG_ACCEPTANCE = "READY_FOR_XG_ACCEPTANCE"
ADD_UNDERSTAT_TEAM_ALIAS_MAP = "ADD_UNDERSTAT_TEAM_ALIAS_MAP"
REVIEW_UNDERSTAT_DATE_ALIGNMENT = "REVIEW_UNDERSTAT_DATE_ALIGNMENT"
IMPROVE_UNDERSTAT_JOIN_NORMALIZATION = "IMPROVE_UNDERSTAT_JOIN_NORMALIZATION"
INCONCLUSIVE_UNDERSTAT_JOIN_DIAGNOSTICS = "INCONCLUSIVE_UNDERSTAT_JOIN_DIAGNOSTICS"


@dataclass
class UnderstatJoinDiagnosticResult:
    source_path: str
    target_path: str
    source_rows: int
    target_rows: int
    exact_matches: int
    missing_matches: int
    exact_coverage_pct: float
    same_date_candidate_matches: int
    plus_minus_one_day_candidate_matches: int
    team_alias_candidate_count: int
    date_mismatch_candidate_count: int
    diagnostic_label: str
    blocking_reasons: list[str]
    warning_notes: list[str]
    recommendation: str = INCONCLUSIVE_UNDERSTAT_JOIN_DIAGNOSTICS
    unmatched_source: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    unmatched_target: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    alias_candidates: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    date_candidates: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)
    team_name_summary: pd.DataFrame = field(default_factory=pd.DataFrame, repr=False)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for key in ("unmatched_source", "unmatched_target", "alias_candidates", "date_candidates", "team_name_summary"):
            out.pop(key, None)
        return out


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve(path: str | Path) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = _repo_root() / out
    return out


def _norm_col(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm_col(col): str(col) for col in df.columns}
    for name in names:
        key = _norm_col(name)
        if key in by_norm:
            return by_norm[key]
    return None


def _parse_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)
    if parsed.isna().any():
        parsed = parsed.fillna(pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True))
    return parsed.dt.strftime("%Y-%m-%d")


def _norm_team(value: Any) -> str:
    return " ".join(str(value or "").strip().replace(".", "").split())


def _join_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["date"].astype(str).str.strip()
        + "|"
        + df["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + df["away_team"].astype(str).str.strip().str.lower()
    )


def load_understat_join_inputs(source_path: str | Path, target_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = _resolve(source_path)
    target = _resolve(target_path)
    if not source.exists():
        raise FileNotFoundError(f"SOURCE_NOT_FOUND={source}")
    if not target.exists():
        raise FileNotFoundError(f"TARGET_NOT_FOUND={target}")
    return pd.read_csv(source, low_memory=False), pd.read_csv(target, low_memory=False)


def normalize_join_key_columns(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    date = _find_col(df, "date", "Date")
    home = _find_col(df, "home_team", "HomeTeam", "home")
    away = _find_col(df, "away_team", "AwayTeam", "away")
    if not all([date, home, away]):
        raise ValueError(f"{source_type}_MISSING_JOIN_COLUMNS")
    out = df.copy()
    out["date"] = _parse_date(out[str(date)])
    out["home_team"] = out[str(home)].map(_norm_team)
    out["away_team"] = out[str(away)].map(_norm_team)
    out["join_key"] = _join_key(out)
    out["source_row_id"] = range(len(out))
    return out


def build_exact_join_keys(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_join_key_columns(source_df, "source")
    target = normalize_join_key_columns(target_df, "target")
    return source[["source_row_id", "join_key"]].merge(
        target[["source_row_id", "join_key"]].rename(columns={"source_row_id": "target_row_id"}),
        on="join_key",
        how="inner",
    )


def find_unmatched_source_rows(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_join_key_columns(source_df, "source")
    target = normalize_join_key_columns(target_df, "target")
    target_keys = set(target["join_key"])
    return source[~source["join_key"].isin(target_keys)].copy()


def find_unmatched_target_rows(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_join_key_columns(source_df, "source")
    target = normalize_join_key_columns(target_df, "target")
    source_keys = set(source["join_key"])
    return target[~target["join_key"].isin(source_keys)].copy()


def find_same_date_team_alias_candidates(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source_unmatched = find_unmatched_source_rows(source_df, target_df)
    target_unmatched = find_unmatched_target_rows(source_df, target_df)
    if source_unmatched.empty or target_unmatched.empty:
        return pd.DataFrame()
    joined = source_unmatched.merge(
        target_unmatched,
        on="date",
        how="inner",
        suffixes=("_source", "_target"),
    )
    if joined.empty:
        return joined
    columns = [
        "date",
        "home_team_source",
        "away_team_source",
        "home_team_target",
        "away_team_target",
        "source_row_id_source",
        "source_row_id_target",
    ]
    out = joined[[col for col in columns if col in joined.columns]].copy()
    out = out.rename(columns={"source_row_id_source": "source_row_id", "source_row_id_target": "target_row_id"})
    out["candidate_type"] = "SAME_DATE_TEAM_ALIAS_REVIEW"
    return out.drop_duplicates()


def find_plus_minus_one_day_candidates(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source_unmatched = find_unmatched_source_rows(source_df, target_df)
    target_unmatched = find_unmatched_target_rows(source_df, target_df)
    if source_unmatched.empty or target_unmatched.empty:
        return pd.DataFrame()
    source = source_unmatched.copy()
    target = target_unmatched.copy()
    source["date_dt"] = pd.to_datetime(source["date"], errors="coerce")
    target["date_dt"] = pd.to_datetime(target["date"], errors="coerce")
    joined = source.merge(target, on=["home_team", "away_team"], how="inner", suffixes=("_source", "_target"))
    if joined.empty:
        return pd.DataFrame()
    joined["date_delta_days"] = (joined["date_dt_source"] - joined["date_dt_target"]).dt.days
    joined = joined[joined["date_delta_days"].abs().eq(1)].copy()
    if joined.empty:
        return pd.DataFrame()
    out = joined[[
        "date_source",
        "date_target",
        "home_team",
        "away_team",
        "date_delta_days",
        "source_row_id_source",
        "source_row_id_target",
    ]].rename(columns={"source_row_id_source": "source_row_id", "source_row_id_target": "target_row_id"})
    out["candidate_type"] = "PLUS_MINUS_ONE_DAY_DATE_REVIEW"
    return out.drop_duplicates()


def summarize_team_name_differences(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
    source = normalize_join_key_columns(source_df, "source")
    target = normalize_join_key_columns(target_df, "target")
    source_teams = sorted(set(source["home_team"]).union(set(source["away_team"])))
    target_teams = sorted(set(target["home_team"]).union(set(target["away_team"])))
    rows = []
    for team in source_teams:
        rows.append({"side": "source_only" if team not in target_teams else "both", "team": team})
    for team in target_teams:
        if team not in source_teams:
            rows.append({"side": "target_only", "team": team})
    return pd.DataFrame(rows)


def _recommendation(source_rows: int, target_rows: int, exact_matches: int, alias_count: int, date_count: int) -> str:
    coverage = exact_matches / target_rows if target_rows else 0.0
    missing = max(target_rows - exact_matches, source_rows - exact_matches, 0)
    if coverage >= 0.98:
        return READY_FOR_XG_ACCEPTANCE
    if missing and alias_count / missing >= 0.6:
        return ADD_UNDERSTAT_TEAM_ALIAS_MAP
    if missing and date_count / missing >= 0.6:
        return REVIEW_UNDERSTAT_DATE_ALIGNMENT
    if source_rows == target_rows and coverage < 0.9:
        return IMPROVE_UNDERSTAT_JOIN_NORMALIZATION
    return INCONCLUSIVE_UNDERSTAT_JOIN_DIAGNOSTICS


def _label_for_recommendation(rec: str, coverage: float) -> str:
    if rec == READY_FOR_XG_ACCEPTANCE:
        return UNDERSTAT_JOIN_READY
    if coverage < 90.0:
        return UNDERSTAT_JOIN_BLOCKED_LOW_COVERAGE
    if rec == ADD_UNDERSTAT_TEAM_ALIAS_MAP:
        return UNDERSTAT_JOIN_NEEDS_TEAM_ALIAS_MAP
    if rec == REVIEW_UNDERSTAT_DATE_ALIGNMENT:
        return UNDERSTAT_JOIN_NEEDS_DATE_ALIGNMENT_REVIEW
    return UNDERSTAT_JOIN_INCONCLUSIVE


def build_understat_join_diagnostics(source_path: str | Path, target_path: str | Path) -> UnderstatJoinDiagnosticResult:
    source_resolved = _resolve(source_path)
    target_resolved = _resolve(target_path)
    try:
        source_df, target_df = load_understat_join_inputs(source_resolved, target_resolved)
    except FileNotFoundError as exc:
        target_missing = "TARGET_NOT_FOUND" in str(exc)
        return UnderstatJoinDiagnosticResult(
            source_path=str(source_resolved),
            target_path=str(target_resolved),
            source_rows=0,
            target_rows=0,
            exact_matches=0,
            missing_matches=0,
            exact_coverage_pct=0.0,
            same_date_candidate_matches=0,
            plus_minus_one_day_candidate_matches=0,
            team_alias_candidate_count=0,
            date_mismatch_candidate_count=0,
            diagnostic_label=UNDERSTAT_JOIN_BLOCKED_NO_TARGET if target_missing else UNDERSTAT_JOIN_BLOCKED_INVALID_SOURCE,
            blocking_reasons=[str(exc)],
            warning_notes=[],
        )
    try:
        exact = build_exact_join_keys(source_df, target_df)
        unmatched_source = find_unmatched_source_rows(source_df, target_df)
        unmatched_target = find_unmatched_target_rows(source_df, target_df)
        alias_candidates = find_same_date_team_alias_candidates(source_df, target_df)
        date_candidates = find_plus_minus_one_day_candidates(source_df, target_df)
        team_summary = summarize_team_name_differences(source_df, target_df)
    except ValueError as exc:
        text = str(exc)
        label = UNDERSTAT_JOIN_BLOCKED_INVALID_TARGET if text.startswith("target_") else UNDERSTAT_JOIN_BLOCKED_INVALID_SOURCE
        return UnderstatJoinDiagnosticResult(
            source_path=str(source_resolved),
            target_path=str(target_resolved),
            source_rows=int(len(source_df)),
            target_rows=int(len(target_df)),
            exact_matches=0,
            missing_matches=int(len(target_df)),
            exact_coverage_pct=0.0,
            same_date_candidate_matches=0,
            plus_minus_one_day_candidate_matches=0,
            team_alias_candidate_count=0,
            date_mismatch_candidate_count=0,
            diagnostic_label=label,
            blocking_reasons=[text],
            warning_notes=[],
        )
    exact_matches = int(exact["source_row_id"].nunique()) if not exact.empty else 0
    target_rows = int(len(target_df))
    source_rows = int(len(source_df))
    missing = max(target_rows - exact_matches, source_rows - exact_matches, 0)
    coverage = round((exact_matches / target_rows * 100.0), 2) if target_rows else 0.0
    alias_count = int(alias_candidates["source_row_id"].nunique()) if not alias_candidates.empty and "source_row_id" in alias_candidates else 0
    date_count = int(date_candidates["source_row_id"].nunique()) if not date_candidates.empty and "source_row_id" in date_candidates else 0
    rec = _recommendation(source_rows, target_rows, exact_matches, alias_count, date_count)
    reasons = []
    if coverage < 98.0:
        reasons.append("EXACT_JOIN_COVERAGE_BELOW_98_PERCENT")
    if source_rows == target_rows and coverage < 90.0:
        reasons.append("SOURCE_TARGET_ROW_COUNTS_MATCH_BUT_JOIN_COVERAGE_LOW")
    warnings = ["Phase 13.9 is diagnostic/foundation only. No xG values were inferred or invented."]
    return UnderstatJoinDiagnosticResult(
        source_path=str(source_resolved),
        target_path=str(target_resolved),
        source_rows=source_rows,
        target_rows=target_rows,
        exact_matches=exact_matches,
        missing_matches=int(missing),
        exact_coverage_pct=coverage,
        same_date_candidate_matches=alias_count,
        plus_minus_one_day_candidate_matches=date_count,
        team_alias_candidate_count=alias_count,
        date_mismatch_candidate_count=date_count,
        diagnostic_label=_label_for_recommendation(rec, coverage),
        blocking_reasons=reasons,
        warning_notes=warnings,
        recommendation=rec,
        unmatched_source=unmatched_source,
        unmatched_target=unmatched_target,
        alias_candidates=alias_candidates,
        date_candidates=date_candidates,
        team_name_summary=team_summary,
    )


def _markdown_table(df: pd.DataFrame, limit: int = 20) -> str:
    if df.empty:
        return "_None._"
    view = df.head(limit).fillna("")
    columns = [str(col) for col in view.columns]
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _idx, row in view.iterrows():
        rows.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in view.columns) + " |")
    return "\n".join(rows)


def _build_markdown(result: UnderstatJoinDiagnosticResult) -> str:
    lines = [
        "# Understat Join Diagnostics",
        "",
        "Phase 13.9 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- source rows: {result.source_rows}",
        f"- target rows: {result.target_rows}",
        f"- exact matches: {result.exact_matches}",
        f"- missing matches: {result.missing_matches}",
        f"- exact coverage: {result.exact_coverage_pct}%",
        f"- diagnostic label: {result.diagnostic_label}",
        f"- recommendation: {result.recommendation}",
        "",
        "## B. Exact Join Coverage",
        _markdown_table(pd.DataFrame([result.to_dict()])),
        "",
        "## C. Unmatched Source Rows",
        _markdown_table(result.unmatched_source),
        "",
        "## D. Unmatched Target Rows",
        _markdown_table(result.unmatched_target),
        "",
        "## E. Same-Date Team Alias Candidates",
        _markdown_table(result.alias_candidates),
        "",
        "## F. Plus/Minus One-Day Date Candidates",
        _markdown_table(result.date_candidates),
        "",
        "## G. Team Name Difference Summary",
        _markdown_table(result.team_name_summary),
        "",
        "## H. Recommended Next Steps",
        "- Review alias candidates manually before creating an alias map.",
        "- Review date candidates manually before changing any source or target dates.",
        "- Rerun fill, validation, and promotion previews only after a reviewed preview improves exact coverage.",
        "",
        "## I. Safety Checks",
        "- No source CSV was modified.",
        "- No target CSV was modified.",
        "- No aliases were applied automatically.",
        "- No xG values were filled, inferred, or invented.",
        "",
        "## J. Phase 13.9 Recommendation",
        result.recommendation,
        "",
    ]
    return "\n".join(lines)


def write_understat_join_diagnostics(
    result: UnderstatJoinDiagnosticResult,
    output_dir: str | Path = "outputs/diagnostics",
) -> dict[str, Path]:
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_csv": output_root / "understat_join_diagnostics_summary.csv",
        "summary_md": output_root / "understat_join_diagnostics_summary.md",
        "unmatched_source": output_root / "understat_join_unmatched_source.csv",
        "unmatched_target": output_root / "understat_join_unmatched_target.csv",
        "alias_candidates": output_root / "understat_join_team_alias_candidates.csv",
        "date_candidates": output_root / "understat_join_date_candidates.csv",
    }
    for path in paths.values():
        if output_root.resolve() not in path.resolve().parents:
            raise ValueError("Understat join diagnostics output must stay under output_dir")
    pd.DataFrame([result.to_dict()]).to_csv(paths["summary_csv"], index=False)
    paths["summary_md"].write_text(_build_markdown(result), encoding="utf-8")
    result.unmatched_source.to_csv(paths["unmatched_source"], index=False)
    result.unmatched_target.to_csv(paths["unmatched_target"], index=False)
    result.alias_candidates.to_csv(paths["alias_candidates"], index=False)
    result.date_candidates.to_csv(paths["date_candidates"], index=False)
    return paths
