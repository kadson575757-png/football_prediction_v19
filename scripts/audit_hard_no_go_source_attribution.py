# -*- coding: utf-8 -*-
"""Phase 11.6 HARD_NO_GO source attribution audit.

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

OUTPUT_CSV = "hard_no_go_source_attribution_summary.csv"
OUTPUT_MD = "hard_no_go_source_attribution_summary.md"

SOURCE_CATEGORIES = (
    "PHASE_11_3_DEFENSIVE_FLAG",
    "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO",
    "SUPPRESSED_WITH_WARNING",
    "LEAGUE_PROFILE_SUPPRESSION",
    "LIGUE1_DIRECTION_HARD_NO_GO",
    "LOW_CONTROL_CONFIRMATION",
    "MEDIUM_FAV_CONFIRMATION",
    "LATE_SEASON_DOWNGRADE",
    "UNKNOWN_HARD_NO_GO_SOURCE",
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


def _rate(df: pd.DataFrame) -> float | None:
    return None if df.empty else float(df["type_success_bool"].mean())


def _hits(df: pd.DataFrame) -> int:
    return int(df["type_success_bool"].sum()) if not df.empty else 0


def _rate_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _num(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("%"):
            text = text[:-1].strip()
            try:
                return float(text) / 100.0
            except ValueError:
                return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reason_flag_columns(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if "reason" in col.lower() or "flag" in col.lower()]


def _combined_signal(row: pd.Series) -> str:
    parts = []
    for col in _reason_flag_columns(row.to_frame().T):
        value = row.get(col, "")
        if value is not None and not pd.isna(value):
            parts.append(str(value))
    for col in ("recommended_market_subtype", "league_adjusted_strength", "league"):
        value = row.get(col, "")
        if value is not None and not pd.isna(value):
            parts.append(str(value))
    return " | ".join(parts).lower()


def classify_hard_no_go_sources(row: pd.Series) -> list[str]:
    signal = _combined_signal(row)
    subtype = _norm_text(row.get("recommended_market_subtype"), "").upper()
    strength = _norm_text(row.get("league_adjusted_strength"), "").upper()
    warning = _norm_text(row.get("league_warning_flags"), "")
    league = _norm_text(row.get("league"), "")
    sources: list[str] = []

    if "phase_11_3" in signal:
        sources.append("PHASE_11_3_DEFENSIVE_FLAG")
    if subtype == "BOTH_OVER25_BTTS" or "both_over25_btts" in signal:
        sources.append("BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO")
    if strength == "SUPPRESSED" and warning:
        sources.append("SUPPRESSED_WITH_WARNING")
    if "suppressed league_adjusted_strength" in signal or "suppressed_strength" in signal:
        sources.append("SUPPRESSED_WITH_WARNING")
    if "league_profile" in signal or "profile suppression" in signal or "subtype_suppressed" in signal:
        sources.append("LEAGUE_PROFILE_SUPPRESSION")
    if ("ligue 1" in league.lower() or "ligue 1" in signal) and "direction" in signal:
        sources.append("LIGUE1_DIRECTION_HARD_NO_GO")
    if "low_control_confirmed" in signal or "low_control_no_go" in signal:
        sources.append("LOW_CONTROL_CONFIRMATION")
    if "medium_fav_confirmed" in signal or "medium_fav_no_go" in signal:
        sources.append("MEDIUM_FAV_CONFIRMATION")
    if "late_season_no_go" in signal:
        sources.append("LATE_SEASON_DOWNGRADE")

    unique = []
    for source in sources:
        if source not in unique:
            unique.append(source)
    return unique or ["UNKNOWN_HARD_NO_GO_SOURCE"]


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
        "recommended_market_subtype",
        "recommended_market_type",
        "league_adjusted_strength",
        "league_warning_flags",
        "market_tier_reason",
        "market_tier_flags",
        "odds_bucket",
        "ctrl_bucket",
        "season_phase",
    ):
        if col not in df.columns:
            df[col] = ""
    for col in (
        "league",
        "market_tier",
        "recommended_market_subtype",
        "recommended_market_type",
        "league_adjusted_strength",
        "odds_bucket",
        "ctrl_bucket",
        "season_phase",
    ):
        df[col] = df[col].apply(_norm_text)
    return df


def hard_no_go_rows(df: pd.DataFrame) -> pd.DataFrame:
    hng = df[df["market_tier"] == "HARD_NO_GO"].copy()
    if hng.empty:
        hng["source_categories"] = []
        return hng
    hng["source_categories"] = hng.apply(lambda row: " | ".join(classify_hard_no_go_sources(row)), axis=1)
    return hng


def explode_sources(hng: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in hng.iterrows():
        for source in str(row.get("source_categories", "")).split("|"):
            source = source.strip()
            if source:
                item = row.to_dict()
                item["source_category"] = source
                rows.append(item)
    return pd.DataFrame(rows)


def _top_counts(df: pd.DataFrame, col: str, limit: int = 5) -> str:
    if df.empty or col not in df.columns:
        return ""
    return ", ".join(f"{idx} ({count})" for idx, count in df[col].value_counts().head(limit).items())


def _reason_snippets(df: pd.DataFrame, limit: int = 3) -> str:
    vals = []
    for value in df.get("market_tier_reason", pd.Series(dtype=str)).dropna().astype(str):
        text = value.strip()
        if text and text not in vals:
            vals.append(text[:80])
        if len(vals) >= limit:
            break
    return " || ".join(vals)


def build_executive_summary(df: pd.DataFrame, focus_league: str) -> dict[str, Any]:
    hng = hard_no_go_rows(df)
    exploded = explode_sources(hng)
    focus_hng = hng[hng["league"].str.lower() == focus_league.lower()]
    other_hng = hng[hng["league"].str.lower() != focus_league.lower()]
    top_source = exploded["source_category"].value_counts().idxmax() if not exploded.empty else "NONE"
    focus_exp = exploded[exploded["league"].str.lower() == focus_league.lower()] if not exploded.empty else exploded
    top_focus = focus_exp["source_category"].value_counts().idxmax() if not focus_exp.empty else "NONE"
    return {
        "total_evaluatable_rows": int(len(df)),
        "total_hard_no_go_rows": int(len(hng)),
        "hard_no_go_success_rate": _rate(hng),
        "ligue1_hard_no_go_rows": int(len(focus_hng)),
        "ligue1_hard_no_go_success_rate": _rate(focus_hng),
        "non_ligue1_hard_no_go_success_rate": _rate(other_hng),
        "top_hard_no_go_source_category": top_source,
        "top_ligue1_hard_no_go_source_category": top_focus,
        "source_attribution_coverage": (
            float((hng["source_categories"] != "UNKNOWN_HARD_NO_GO_SOURCE").mean()) if not hng.empty else None
        ),
    }


def build_source_overall(hng: pd.DataFrame) -> pd.DataFrame:
    exploded = explode_sources(hng)
    rows = []
    for source, grp in exploded.groupby("source_category", sort=True):
        n = int(len(grp))
        hits = _hits(grp)
        rows.append({
            "section": "hard_no_go_source_attribution_overall",
            "source_category": source,
            "n": n,
            "hits": hits,
            "success_rate": round(hits / n, 4) if n else None,
            "leagues": ", ".join(sorted(grp["league"].dropna().astype(str).unique())),
            "top_recommended_market_subtypes": _top_counts(grp, "recommended_market_subtype"),
            "top_market_tier_reason_snippets": _reason_snippets(grp),
        })
    return pd.DataFrame(rows)


def build_source_by_league(hng: pd.DataFrame) -> pd.DataFrame:
    exploded = explode_sources(hng)
    if exploded.empty:
        return pd.DataFrame()
    league_totals = hng.groupby("league").size().to_dict()
    rows = []
    for (league, source), grp in exploded.groupby(["league", "source_category"], sort=True):
        n = int(len(grp))
        hits = _hits(grp)
        rows.append({
            "section": "hard_no_go_source_attribution_by_league",
            "league": league,
            "source_category": source,
            "n": n,
            "hits": hits,
            "success_rate": round(hits / n, 4) if n else None,
            "share_of_league_hard_no_go_rows": round(n / league_totals.get(league, n), 4),
        })
    return pd.DataFrame(rows)


def build_focus_source_attribution(hng: pd.DataFrame, focus_league: str) -> pd.DataFrame:
    exploded = explode_sources(hng)
    focus = exploded[exploded["league"].str.lower() == focus_league.lower()] if not exploded.empty else exploded
    rows = []
    for source, grp in focus.groupby("source_category", sort=True):
        n = int(len(grp))
        hits = _hits(grp)
        rows.append({
            "section": "ligue1_hard_no_go_source_attribution",
            "source_category": source,
            "n": n,
            "hits": hits,
            "success_rate": round(hits / n, 4) if n else None,
            "recommended_market_subtype_distribution": _top_counts(grp, "recommended_market_subtype"),
            "odds_bucket_distribution": _top_counts(grp, "odds_bucket"),
            "ctrl_bucket_distribution": _top_counts(grp, "ctrl_bucket"),
            "season_phase_distribution": _top_counts(grp, "season_phase"),
        })
    return pd.DataFrame(rows)


def build_focus_vs_other_comparison(hng: pd.DataFrame, focus_league: str) -> pd.DataFrame:
    exploded = explode_sources(hng)
    rows = []
    for source in SOURCE_CATEGORIES:
        focus = exploded[
            (exploded["source_category"] == source)
            & (exploded["league"].str.lower() == focus_league.lower())
        ] if not exploded.empty else pd.DataFrame()
        other = exploded[
            (exploded["source_category"] == source)
            & (exploded["league"].str.lower() != focus_league.lower())
        ] if not exploded.empty else pd.DataFrame()
        f_rate = _rate(focus)
        o_rate = _rate(other)
        rows.append({
            "section": "ligue1_vs_other_leagues_by_source",
            "source_category": source,
            "ligue1_n": int(len(focus)),
            "ligue1_rate": round(f_rate, 4) if f_rate is not None else None,
            "other_n": int(len(other)),
            "other_rate": round(o_rate, 4) if o_rate is not None else None,
            "delta_pp": (
                round((f_rate - o_rate) * 100.0, 2)
                if f_rate is not None and o_rate is not None
                else None
            ),
        })
    out = pd.DataFrame(rows)
    return out.drop_duplicates(subset=["source_category"], keep="first").reset_index(drop=True)


def build_candidate_sources(
    comparison: pd.DataFrame,
    overall: pd.DataFrame,
    *,
    min_sample: int,
    global_min_sample: int,
    high_rate_threshold: float,
    delta_threshold_pp: float,
) -> pd.DataFrame:
    rows = []
    threshold = high_rate_threshold / 100.0
    comparison = comparison.drop_duplicates(subset=["source_category"], keep="first")
    for _, row in comparison.iterrows():
        source = str(row["source_category"])
        ligue_n = int(row.get("ligue1_n") or 0)
        ligue_rate = _num(row.get("ligue1_rate"))
        other_n = int(row.get("other_n") or 0)
        delta = _num(row.get("delta_pp"))
        label = "SOURCE_OK"
        if source == "UNKNOWN_HARD_NO_GO_SOURCE" and ligue_n >= min_sample:
            label = "UNKNOWN_SOURCE_REVIEW"
        elif ligue_n < min_sample and ligue_n > 0:
            label = "SMALL_SAMPLE_OBSERVE"
        elif ligue_rate is not None and ligue_n >= min_sample and ligue_rate >= threshold:
            if other_n == 0 or (delta is not None and delta >= delta_threshold_pp):
                label = "LIGUE1_SOURCE_TOO_STRICT"
        if label != "SOURCE_OK":
            rows.append({**row.to_dict(), "section": "candidate_source_problems", "candidate_label": label})

    for _, row in overall.iterrows():
        global_rate = _num(row.get("success_rate")) or 0.0
        if int(row.get("n") or 0) >= global_min_sample and global_rate >= threshold:
            rows.append({
                "section": "candidate_source_problems",
                "candidate_label": "GLOBAL_SOURCE_TOO_STRICT",
                "source_category": row["source_category"],
                "global_n": row["n"],
                "global_rate": row["success_rate"],
            })
    return pd.DataFrame(rows)


def safety_checks() -> dict[str, Any]:
    return {
        "no_rule_changed": True,
        "market_tier_py_modified_by_script": False,
        "probability_logic_changed": False,
        "recommended_market_logic_changed": False,
        "betting_staking_roi_logic_changed": False,
        "super_a_tier_activated": False,
        "diagnostic_only": True,
    }


def phase11_6_recommendation(
    executive: dict[str, Any],
    candidates: pd.DataFrame,
    *,
    min_sample: int,
) -> str:
    if executive["total_hard_no_go_rows"] < 100 or executive["ligue1_hard_no_go_rows"] < 50:
        return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"
    labels = set(candidates.get("candidate_label", pd.Series(dtype=str)).dropna().astype(str))
    if "LIGUE1_SOURCE_TOO_STRICT" in labels:
        return "INVESTIGATE_LIGUE1_SOURCE_RELAXATION"
    if "GLOBAL_SOURCE_TOO_STRICT" in labels:
        return "INVESTIGATE_GLOBAL_SOURCE_RELAXATION"
    unknown_n = 0
    if not candidates.empty:
        unknown_n = int(candidates[
            (candidates.get("source_category") == "UNKNOWN_HARD_NO_GO_SOURCE")
            & (candidates.get("candidate_label") == "UNKNOWN_SOURCE_REVIEW")
        ].get("ligue1_n", pd.Series(dtype=int)).max() or 0)
    if unknown_n >= min_sample:
        return "INVESTIGATE_UNKNOWN_HARD_NO_GO_SOURCES"
    if (executive.get("source_attribution_coverage") or 0.0) >= 0.95 and not labels:
        return "KEEP_CURRENT_HARD_NO_GO_SOURCES"
    return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"


def build_summary_table(
    df: pd.DataFrame,
    *,
    focus_league: str = "Ligue 1",
    min_sample: int = 20,
    global_min_sample: int = 50,
    high_rate_threshold: float = 70.0,
    delta_threshold_pp: float = 5.0,
) -> tuple[pd.DataFrame, dict[str, Any], str]:
    hng = hard_no_go_rows(df)
    executive = build_executive_summary(df, focus_league)
    overall = build_source_overall(hng)
    by_league = build_source_by_league(hng)
    focus_attr = build_focus_source_attribution(hng, focus_league)
    comparison = build_focus_vs_other_comparison(hng, focus_league)
    candidates = build_candidate_sources(
        comparison,
        overall,
        min_sample=min_sample,
        global_min_sample=global_min_sample,
        high_rate_threshold=high_rate_threshold,
        delta_threshold_pp=delta_threshold_pp,
    )
    recommendation = phase11_6_recommendation(executive, candidates, min_sample=min_sample)
    frames = [
        pd.DataFrame([{"section": "executive_summary", **executive}]),
        overall,
        by_league,
        focus_attr,
        comparison,
        candidates,
        pd.DataFrame([{"section": "safety_checks", **safety_checks()}]),
        pd.DataFrame([{"section": "phase_11_6_recommendation", "recommendation": recommendation}]),
    ]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True, sort=False), executive, recommendation


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [c for c in columns if c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        vals = []
        for col in cols:
            val = row.get(col)
            if isinstance(val, float):
                vals.append(f"{val * 100:.1f}%" if "rate" in col or "share" in col else f"{val:.2f}")
            else:
                vals.append("" if pd.isna(val) else str(val))
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, executive: dict[str, Any], recommendation: str, focus_league: str) -> str:
    sec = lambda name: table[table["section"] == name] if "section" in table.columns else pd.DataFrame()
    safety = safety_checks()
    lines = [
        "# Phase 11.6 HARD_NO_GO Source Attribution Audit",
        "",
        "Phase 11.6 is diagnostic only. No tier rules were changed.",
        "",
        "## A. Executive Summary",
        f"- Total evaluatable rows: {executive['total_evaluatable_rows']:,}",
        f"- Total HARD_NO_GO rows: {executive['total_hard_no_go_rows']:,}",
        f"- HARD_NO_GO success rate: {_rate_pct(executive['hard_no_go_success_rate'])}",
        f"- {focus_league} HARD_NO_GO rows: {executive['ligue1_hard_no_go_rows']:,}",
        f"- {focus_league} HARD_NO_GO success rate: {_rate_pct(executive['ligue1_hard_no_go_success_rate'])}",
        f"- non-{focus_league} HARD_NO_GO success rate: {_rate_pct(executive['non_ligue1_hard_no_go_success_rate'])}",
        f"- Top HARD_NO_GO source category: {executive['top_hard_no_go_source_category']}",
        f"- Top {focus_league} HARD_NO_GO source category: {executive['top_ligue1_hard_no_go_source_category']}",
        "",
        "## B. HARD_NO_GO Source Attribution Overall",
    ]
    lines += _markdown_table(sec("hard_no_go_source_attribution_overall"), [
        "source_category", "n", "hits", "success_rate", "leagues",
        "top_recommended_market_subtypes", "top_market_tier_reason_snippets",
    ])
    lines += ["## C. HARD_NO_GO Source Attribution by League"]
    lines += _markdown_table(sec("hard_no_go_source_attribution_by_league"), [
        "league", "source_category", "n", "hits", "success_rate", "share_of_league_hard_no_go_rows",
    ])
    lines += [f"## D. {focus_league} HARD_NO_GO Source Attribution"]
    lines += _markdown_table(sec("ligue1_hard_no_go_source_attribution"), [
        "source_category", "n", "hits", "success_rate",
        "recommended_market_subtype_distribution", "odds_bucket_distribution",
        "ctrl_bucket_distribution", "season_phase_distribution",
    ])
    lines += [f"## E. Compare {focus_league} vs Other Leagues by Source"]
    lines += _markdown_table(sec("ligue1_vs_other_leagues_by_source"), [
        "source_category", "ligue1_n", "ligue1_rate", "other_n", "other_rate", "delta_pp",
    ])
    lines += ["## F. Candidate Source Problems"]
    lines += _markdown_table(sec("candidate_source_problems"), [
        "candidate_label", "source_category", "ligue1_n", "ligue1_rate",
        "other_n", "other_rate", "delta_pp", "global_n", "global_rate",
    ])
    lines += [
        "## G. Safety Checks",
        f"- No rule changed: {safety['no_rule_changed']}",
        f"- No market_tier.py modified by this script: {not safety['market_tier_py_modified_by_script']}",
        f"- No probability logic changed: {not safety['probability_logic_changed']}",
        f"- No recommended market logic changed: {not safety['recommended_market_logic_changed']}",
        f"- No betting/staking/ROI logic changed: {not safety['betting_staking_roi_logic_changed']}",
        f"- No SUPER_A_TIER activated: {not safety['super_a_tier_activated']}",
        f"- This is diagnostic only: {safety['diagnostic_only']}",
        "",
        "## H. Phase 11.6 Recommendation",
        recommendation,
        "",
    ]
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    focus_league: str = "Ligue 1",
    min_sample: int = 20,
    global_min_sample: int = 50,
    high_rate_threshold: float = 70.0,
    delta_threshold_pp: float = 5.0,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table, executive, recommendation = build_summary_table(
        df,
        focus_league=focus_league,
        min_sample=min_sample,
        global_min_sample=global_min_sample,
        high_rate_threshold=high_rate_threshold,
        delta_threshold_pp=delta_threshold_pp,
    )
    markdown = build_markdown(table, executive, recommendation, focus_league)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "season_replay"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--focus-league", default="Ligue 1")
    parser.add_argument("--min-sample", type=int, default=20)
    parser.add_argument("--global-min-sample", type=int, default=50)
    parser.add_argument("--high-rate-threshold", type=float, default=70.0)
    parser.add_argument("--delta-threshold-pp", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        focus_league=args.focus_league,
        min_sample=args.min_sample,
        global_min_sample=args.global_min_sample,
        high_rate_threshold=args.high_rate_threshold,
        delta_threshold_pp=args.delta_threshold_pp,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## H. Phase 11.6 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
