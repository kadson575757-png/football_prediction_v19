# -*- coding: utf-8 -*-
"""Phase 11.5 Ligue 1 defensive relaxation investigation.

Diagnostic/reporting only. This script does not change market-tier rules,
probability logic, recommended-market logic, betting, staking, ROI, or
SUPER_A_TIER activation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

OUTPUT_CSV = "ligue1_defensive_relaxation_summary.csv"
OUTPUT_MD = "ligue1_defensive_relaxation_summary.md"
PHASE_11_3_RE = re.compile(r"phase_11_3_[a-z0-9_]+", re.IGNORECASE)

BREAKDOWN_DIMS = (
    "recommended_market_type",
    "recommended_market_subtype",
    "league_adjusted_strength",
    "warning_state",
    "ctrl_bucket",
    "chaos_bucket",
    "odds_bucket",
    "season_phase",
    "ensemble_agreement",
)
COMPARISON_DIMS = (
    "recommended_market_subtype",
    "phase_11_3_flag",
    "odds_bucket",
    "ctrl_bucket",
    "season_phase",
)


def parse_bool_success(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _norm_text(value: Any, default: str = "UNKNOWN") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return default
    return text


def warning_state(value: Any) -> str:
    text = _norm_text(value, default="")
    return "clean" if not text else "warned"


def _rate(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    return float(df["type_success_bool"].mean())


def _hits(df: pd.DataFrame) -> int:
    return int(df["type_success_bool"].sum()) if not df.empty else 0


def _rate_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _reason_flag_columns(df: pd.DataFrame) -> list[str]:
    return [
        col for col in df.columns
        if "reason" in col.lower() or "flag" in col.lower()
    ]


def extract_phase11_3_flags(row: pd.Series) -> list[str]:
    found: list[str] = []
    for col in _reason_flag_columns(row.to_frame().T):
        value = row.get(col, "")
        if value is None or pd.isna(value):
            continue
        for match in PHASE_11_3_RE.findall(str(value)):
            flag = match.lower()
            if flag not in found:
                found.append(flag)
    return found


def load_evaluation_rows(input_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(input_dir.glob("*_evaluation.csv")):
        df = pd.read_csv(path)
        df["source_file"] = path.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)
    if "type_success" not in df.columns:
        return df.iloc[0:0].copy()

    df["type_success_bool"] = df["type_success"].apply(parse_bool_success)
    df = df[df["type_success_bool"].notna()].copy()
    df["type_success_bool"] = df["type_success_bool"].astype(bool)

    for col in (
        "league",
        "market_tier",
        "recommended_market_type",
        "recommended_market_subtype",
        "league_adjusted_strength",
        "league_warning_flags",
        "ctrl_bucket",
        "chaos_bucket",
        "odds_bucket",
        "season_phase",
        "ensemble_agreement",
        "market_tier_reason",
        "market_tier_flags",
    ):
        if col not in df.columns:
            df[col] = ""

    for col in (
        "league",
        "market_tier",
        "recommended_market_type",
        "recommended_market_subtype",
        "league_adjusted_strength",
        "ctrl_bucket",
        "chaos_bucket",
        "odds_bucket",
        "season_phase",
        "ensemble_agreement",
    ):
        df[col] = df[col].apply(_norm_text)

    df["warning_state"] = df["league_warning_flags"].apply(warning_state)
    df["phase_11_3_flags"] = df.apply(lambda row: " | ".join(extract_phase11_3_flags(row)), axis=1)
    df["phase_11_3_impacted"] = df["phase_11_3_flags"].astype(str).str.contains("phase_11_3", case=False, na=False)
    df["phase_11_3_flag"] = df["phase_11_3_flags"].apply(lambda value: str(value).split("|")[0].strip() or "NONE")
    return df


def split_focus(df: pd.DataFrame, league: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    focus = df[df["league"].astype(str).str.lower() == league.lower()].copy()
    other = df[df["league"].astype(str).str.lower() != league.lower()].copy()
    return focus, other


def build_executive_summary(df: pd.DataFrame, league: str) -> dict[str, Any]:
    focus, other = split_focus(df, league)
    focus_hng = focus[focus["market_tier"] == "HARD_NO_GO"]
    other_hng = other[other["market_tier"] == "HARD_NO_GO"]
    focus_impacted = focus[focus["phase_11_3_impacted"]]
    other_impacted = other[other["phase_11_3_impacted"]]
    focus_impacted_rate = _rate(focus_impacted)
    other_impacted_rate = _rate(other_impacted)
    return {
        "league": league,
        "ligue1_evaluatable_rows": int(len(focus)),
        "ligue1_hard_no_go_rows": int(len(focus_hng)),
        "ligue1_hard_no_go_success_rate": _rate(focus_hng),
        "ligue1_impacted_rows": int(len(focus_impacted)),
        "ligue1_impacted_success_rate": focus_impacted_rate,
        "non_ligue1_hard_no_go_success_rate": _rate(other_hng),
        "non_ligue1_impacted_success_rate": other_impacted_rate,
        "gap_vs_non_ligue1_pp": (
            round((focus_impacted_rate - other_impacted_rate) * 100.0, 2)
            if focus_impacted_rate is not None and other_impacted_rate is not None
            else None
        ),
    }


def _aggregate(df: pd.DataFrame, dimension: str, section: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for value, grp in df.groupby(dimension, dropna=False, sort=True):
        n = int(len(grp))
        hits = _hits(grp)
        rows.append({
            "section": section,
            "dimension": dimension,
            "value": value,
            "n": n,
            "hits": hits,
            "success_rate": round(hits / n, 4) if n else None,
        })
    return pd.DataFrame(rows)


def build_hard_no_go_breakdown(df: pd.DataFrame, league: str) -> pd.DataFrame:
    focus, _ = split_focus(df, league)
    hng = focus[focus["market_tier"] == "HARD_NO_GO"].copy()
    frames = [_aggregate(hng, dim, "ligue1_hard_no_go_breakdown") for dim in BREAKDOWN_DIMS]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def build_flag_breakdown(df: pd.DataFrame, league: str) -> pd.DataFrame:
    focus, _ = split_focus(df, league)
    impacted = focus[focus["phase_11_3_impacted"]].copy()
    rows: list[dict[str, Any]] = []
    for _, row in impacted.iterrows():
        for flag in str(row.get("phase_11_3_flags", "")).split("|"):
            flag = flag.strip()
            if flag:
                item = row.to_dict()
                item["phase_11_3_flag"] = flag
                rows.append(item)
    if not rows:
        return pd.DataFrame()
    exploded = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for flag, grp in exploded.groupby("phase_11_3_flag", sort=True):
        out.append({
            "section": "ligue1_phase_11_3_flag_breakdown",
            "phase_11_3_flag": flag,
            "n": int(len(grp)),
            "hits": _hits(grp),
            "success_rate": round(float(grp["type_success_bool"].mean()), 4),
            "top_subtypes": _top_counts(grp, "recommended_market_subtype"),
            "top_odds_buckets": _top_counts(grp, "odds_bucket"),
            "top_control_buckets": _top_counts(grp, "ctrl_bucket"),
            "top_season_phases": _top_counts(grp, "season_phase"),
        })
    return pd.DataFrame(out)


def _top_counts(df: pd.DataFrame, col: str, limit: int = 5) -> str:
    if col not in df.columns or df.empty:
        return ""
    return ", ".join(f"{idx} ({count})" for idx, count in df[col].value_counts().head(limit).items())


def build_comparison(df: pd.DataFrame, league: str) -> pd.DataFrame:
    focus, other = split_focus(df, league)
    rows: list[dict[str, Any]] = []
    for dim in COMPARISON_DIMS:
        values = sorted(set(focus[dim].dropna().astype(str)) | set(other[dim].dropna().astype(str)))
        for value in values:
            fgrp = focus[focus[dim].astype(str) == value]
            ogrp = other[other[dim].astype(str) == value]
            f_rate = _rate(fgrp)
            o_rate = _rate(ogrp)
            rows.append({
                "section": "ligue1_vs_other_leagues_comparison",
                "dimension": dim,
                "value": value,
                "ligue1_n": int(len(fgrp)),
                "ligue1_rate": round(f_rate, 4) if f_rate is not None else None,
                "other_n": int(len(ogrp)),
                "other_rate": round(o_rate, 4) if o_rate is not None else None,
                "delta_pp": (
                    round((f_rate - o_rate) * 100.0, 2)
                    if f_rate is not None and o_rate is not None
                    else None
                ),
            })
    return pd.DataFrame(rows)


def build_candidate_zones(
    comparison: pd.DataFrame,
    *,
    min_sample: int,
    high_rate_threshold: float,
    delta_threshold_pp: float,
) -> pd.DataFrame:
    categories = {
        "phase_11_3_flag": "LIGUE1_RELAX_PHASE_11_3_FLAG",
        "recommended_market_subtype": "LIGUE1_RELAX_SUBTYPE",
        "odds_bucket": "LIGUE1_RELAX_ODDS_BUCKET",
        "ctrl_bucket": "LIGUE1_RELAX_CONTROL_BUCKET",
        "season_phase": "LIGUE1_RELAX_SEASON_PHASE",
    }
    rows: list[dict[str, Any]] = []
    threshold = high_rate_threshold / 100.0
    for _, row in comparison.iterrows():
        dim = str(row.get("dimension", ""))
        if dim not in categories:
            continue
        n = int(row.get("ligue1_n") or 0)
        rate = row.get("ligue1_rate")
        other_n = int(row.get("other_n") or 0)
        delta = row.get("delta_pp")
        if n < min_sample:
            if n > 0:
                rows.append({
                    "section": "candidate_relaxation_zones",
                    "candidate_category": "OBSERVE_ONLY_SMALL_SAMPLE",
                    **row.to_dict(),
                })
            continue
        if rate is None or pd.isna(rate) or float(rate) < threshold:
            continue
        if other_n > 0 and (delta is None or pd.isna(delta) or float(delta) < delta_threshold_pp):
            continue
        rows.append({
            "section": "candidate_relaxation_zones",
            "candidate_category": categories[dim],
            **row.to_dict(),
        })
    return pd.DataFrame(rows)


def safety_checks() -> dict[str, Any]:
    return {
        "no_rule_changed": True,
        "market_tier_py_modified_by_script": False,
        "probability_logic_changed": False,
        "recommended_market_logic_changed": False,
        "super_a_tier_activated": False,
        "diagnostic_only": True,
    }


def phase11_5_recommendation(
    executive: dict[str, Any],
    flag_breakdown: pd.DataFrame,
    hard_no_go_breakdown: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    min_sample: int,
    high_rate_threshold: float,
) -> str:
    if int(executive.get("ligue1_impacted_rows") or 0) < min_sample:
        return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"
    threshold = high_rate_threshold / 100.0
    if not flag_breakdown.empty:
        flag_hits = flag_breakdown[
            (flag_breakdown["n"] >= min_sample)
            & (flag_breakdown["success_rate"] >= threshold)
        ]
        if not flag_hits.empty:
            return "INVESTIGATE_LIGUE1_FLAG_RELAXATION"
    subtype_hits = hard_no_go_breakdown[
        (hard_no_go_breakdown["dimension"] == "recommended_market_subtype")
        & (hard_no_go_breakdown["n"] >= min_sample)
        & (hard_no_go_breakdown["success_rate"] >= threshold)
    ] if not hard_no_go_breakdown.empty else pd.DataFrame()
    if not subtype_hits.empty:
        return "INVESTIGATE_LIGUE1_SUBTYPE_RELAXATION"
    hng_rate = executive.get("ligue1_hard_no_go_success_rate")
    if hng_rate is not None and hng_rate >= threshold:
        return "INVESTIGATE_LIGUE1_PROFILE_REVIEW"
    actionable = candidates[
        candidates.get("candidate_category", pd.Series(dtype=str)).astype(str).str.startswith("LIGUE1_RELAX")
    ] if not candidates.empty else pd.DataFrame()
    if actionable.empty:
        return "KEEP_PHASE_11_3_AS_IS"
    return "INVESTIGATE_LIGUE1_PROFILE_REVIEW"


def build_summary_table(
    df: pd.DataFrame,
    *,
    league: str = "Ligue 1",
    min_sample: int = 20,
    high_rate_threshold: float = 70.0,
    delta_threshold_pp: float = 5.0,
) -> tuple[pd.DataFrame, dict[str, Any], str]:
    executive = build_executive_summary(df, league)
    hng_breakdown = build_hard_no_go_breakdown(df, league)
    flag_breakdown = build_flag_breakdown(df, league)
    comparison = build_comparison(df, league)
    candidates = build_candidate_zones(
        comparison,
        min_sample=min_sample,
        high_rate_threshold=high_rate_threshold,
        delta_threshold_pp=delta_threshold_pp,
    )
    checks = safety_checks()
    recommendation = phase11_5_recommendation(
        executive,
        flag_breakdown,
        hng_breakdown,
        candidates,
        min_sample=min_sample,
        high_rate_threshold=high_rate_threshold,
    )
    frames = [
        pd.DataFrame([{"section": "executive_summary", **executive}]),
        hng_breakdown,
        flag_breakdown,
        comparison,
        candidates,
        pd.DataFrame([{"section": "safety_checks", **checks}]),
        pd.DataFrame([{"section": "phase_11_5_recommendation", "recommendation": recommendation}]),
    ]
    frames = [frame for frame in frames if not frame.empty]
    table = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    return table, executive, recommendation


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        values = []
        for col in cols:
            val = row.get(col)
            if isinstance(val, float):
                values.append(f"{val * 100:.1f}%" if "rate" in col else f"{val:.2f}")
            else:
                values.append("" if pd.isna(val) else str(val))
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, executive: dict[str, Any], recommendation: str, league: str) -> str:
    hng = table[table["section"] == "ligue1_hard_no_go_breakdown"] if "section" in table.columns else pd.DataFrame()
    flags = table[table["section"] == "ligue1_phase_11_3_flag_breakdown"] if "section" in table.columns else pd.DataFrame()
    comp = table[table["section"] == "ligue1_vs_other_leagues_comparison"] if "section" in table.columns else pd.DataFrame()
    cand = table[table["section"] == "candidate_relaxation_zones"] if "section" in table.columns else pd.DataFrame()
    safety = safety_checks()
    lines = [
        "# Phase 11.5 Ligue 1 Defensive Relaxation Investigation",
        "",
        "Phase 11.5 is diagnostic only. No tier rules were changed.",
        "",
        "## A. Executive Summary",
        f"- {league} evaluatable rows: {executive['ligue1_evaluatable_rows']:,}",
        f"- {league} HARD_NO_GO rows: {executive['ligue1_hard_no_go_rows']:,}",
        f"- {league} HARD_NO_GO success rate: {_rate_pct(executive['ligue1_hard_no_go_success_rate'])}",
        f"- {league} impacted rows: {executive['ligue1_impacted_rows']:,}",
        f"- {league} impacted success rate: {_rate_pct(executive['ligue1_impacted_success_rate'])}",
        f"- non-{league} HARD_NO_GO success rate: {_rate_pct(executive['non_ligue1_hard_no_go_success_rate'])}",
        f"- non-{league} impacted success rate: {_rate_pct(executive['non_ligue1_impacted_success_rate'])}",
        f"- gap vs non-{league}: {executive['gap_vs_non_ligue1_pp'] if executive['gap_vs_non_ligue1_pp'] is not None else 'n/a'} pp",
        "",
        "## B. Ligue 1 HARD_NO_GO Breakdown",
    ]
    lines += _markdown_table(hng, ["dimension", "value", "n", "hits", "success_rate"])
    lines += ["## C. Ligue 1 Phase 11.3 Flag Breakdown"]
    lines += _markdown_table(flags, [
        "phase_11_3_flag", "n", "hits", "success_rate", "top_subtypes",
        "top_odds_buckets", "top_control_buckets", "top_season_phases",
    ])
    lines += ["## D. Ligue 1 vs Other Leagues Comparison"]
    lines += _markdown_table(comp, ["dimension", "value", "ligue1_n", "ligue1_rate", "other_n", "other_rate", "delta_pp"])
    lines += ["## E. Candidate Relaxation Zones"]
    lines += _markdown_table(cand, ["candidate_category", "dimension", "value", "ligue1_n", "ligue1_rate", "other_n", "other_rate", "delta_pp"])
    lines += [
        "## F. Safety Checks",
        f"- No rule changed: {safety['no_rule_changed']}",
        f"- No market_tier.py modified by this script: {not safety['market_tier_py_modified_by_script']}",
        f"- No probability logic changed: {not safety['probability_logic_changed']}",
        f"- No recommended market logic changed: {not safety['recommended_market_logic_changed']}",
        f"- No SUPER_A_TIER activated: {not safety['super_a_tier_activated']}",
        f"- This is diagnostic only: {safety['diagnostic_only']}",
        "",
        "## G. Phase 11.5 Recommendation",
        recommendation,
        "",
    ]
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    league: str = "Ligue 1",
    min_sample: int = 20,
    high_rate_threshold: float = 70.0,
    delta_threshold_pp: float = 5.0,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table, executive, recommendation = build_summary_table(
        df,
        league=league,
        min_sample=min_sample,
        high_rate_threshold=high_rate_threshold,
        delta_threshold_pp=delta_threshold_pp,
    )
    markdown = build_markdown(table, executive, recommendation, league)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "season_replay"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--league", default="Ligue 1")
    parser.add_argument("--min-sample", type=int, default=20)
    parser.add_argument("--high-rate-threshold", type=float, default=70.0)
    parser.add_argument("--delta-threshold-pp", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        league=args.league,
        min_sample=args.min_sample,
        high_rate_threshold=args.high_rate_threshold,
        delta_threshold_pp=args.delta_threshold_pp,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## G. Phase 11.5 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
