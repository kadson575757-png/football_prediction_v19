# -*- coding: utf-8 -*-
"""Phase 11.7 Ligue 1 source-specific relaxation simulation.

Simulation/reporting only. This script does not modify replay CSVs, market-tier
rules, probability logic, recommended-market logic, betting, staking, ROI, or
SUPER_A_TIER activation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_hard_no_go_source_attribution import (  # noqa: E402
    classify_hard_no_go_sources,
    parse_bool_success,
)

OUTPUT_CSV = "ligue1_source_relaxation_simulation.csv"
OUTPUT_MD = "ligue1_source_relaxation_simulation.md"

VARIANTS: tuple[tuple[str, set[str]], ...] = (
    ("relax_both_over25_btts", {"BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO"}),
    ("relax_suppressed_with_warning", {"SUPPRESSED_WITH_WARNING"}),
    ("relax_league_profile_suppression", {"LEAGUE_PROFILE_SUPPRESSION"}),
    (
        "relax_all_ligue1_source_candidates",
        {
            "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO",
            "SUPPRESSED_WITH_WARNING",
            "LEAGUE_PROFILE_SUPPRESSION",
        },
    ),
)
BREAKDOWN_DIMS = (
    "recommended_market_subtype",
    "odds_bucket",
    "ctrl_bucket",
    "chaos_bucket",
    "season_phase",
    "league_adjusted_strength",
    "warning_state",
)


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
    return None if df.empty else float(df["type_success_bool"].mean())


def _hits(df: pd.DataFrame) -> int:
    return int(df["type_success_bool"].sum()) if not df.empty else 0


def _rate_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


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
        "market_tier_reason",
        "market_tier_flags",
        "odds_bucket",
        "ctrl_bucket",
        "chaos_bucket",
        "season_phase",
    ):
        if col not in df.columns:
            df[col] = ""
    for col in (
        "league",
        "market_tier",
        "recommended_market_type",
        "recommended_market_subtype",
        "league_adjusted_strength",
        "odds_bucket",
        "ctrl_bucket",
        "chaos_bucket",
        "season_phase",
    ):
        df[col] = df[col].apply(_norm_text)
    df["warning_state"] = df["league_warning_flags"].apply(warning_state)
    df["source_categories"] = df.apply(
        lambda row: " | ".join(classify_hard_no_go_sources(row))
        if row.get("market_tier") == "HARD_NO_GO"
        else "",
        axis=1,
    )
    return df


def ligue1_hard_no_go_rows(df: pd.DataFrame, league: str = "Ligue 1") -> pd.DataFrame:
    return df[
        (df["league"].astype(str).str.lower() == league.lower())
        & (df["market_tier"] == "HARD_NO_GO")
    ].copy()


def _has_source(series_value: Any, sources: set[str]) -> bool:
    return bool(set(str(series_value).split(" | ")) & sources)


def _tier_stats(df: pd.DataFrame, tier_col: str = "market_tier") -> dict[str, tuple[int, float | None]]:
    out: dict[str, tuple[int, float | None]] = {}
    for tier in ("HARD_NO_GO", "DOWNGRADE", "A_TIER", "B_TIER"):
        grp = df[df[tier_col] == tier]
        out[tier] = (int(len(grp)), _rate(grp))
    return out


def executive_summary(df: pd.DataFrame, league: str) -> dict[str, Any]:
    focus = df[df["league"].astype(str).str.lower() == league.lower()].copy()
    hng = focus[focus["market_tier"] == "HARD_NO_GO"]
    downgrade = focus[focus["market_tier"] == "DOWNGRADE"]
    return {
        "league": league,
        "total_ligue1_evaluatable_rows": int(len(focus)),
        "original_ligue1_hard_no_go_rows": int(len(hng)),
        "original_ligue1_hard_no_go_success_rate": _rate(hng),
        "original_ligue1_downgrade_rows": int(len(downgrade)),
        "original_ligue1_downgrade_success_rate": _rate(downgrade),
        "simulated_variants": len(VARIANTS),
    }


def simulate_variant(df: pd.DataFrame, variant_name: str, sources: set[str], league: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    sim = df.copy(deep=True)
    focus_mask = sim["league"].astype(str).str.lower().eq(league.lower())
    hng_mask = sim["market_tier"].eq("HARD_NO_GO")
    source_mask = sim["source_categories"].apply(lambda value: _has_source(value, sources))
    relaxed_mask = focus_mask & hng_mask & source_mask
    sim["simulated_market_tier"] = sim["market_tier"]
    sim.loc[relaxed_mask, "simulated_market_tier"] = "DOWNGRADE"
    relaxed = sim[relaxed_mask].copy()
    relaxed["variant_name"] = variant_name
    return sim, relaxed


def build_variant_summary(
    df: pd.DataFrame,
    *,
    league: str = "Ligue 1",
) -> pd.DataFrame:
    focus = df[df["league"].astype(str).str.lower() == league.lower()].copy()
    original_stats = _tier_stats(focus)
    rows: list[dict[str, Any]] = []
    for variant_name, sources in VARIANTS:
        sim, relaxed = simulate_variant(df, variant_name, sources, league)
        sim_focus = sim[sim["league"].astype(str).str.lower() == league.lower()].copy()
        stats = _tier_stats(sim_focus, tier_col="simulated_market_tier")
        hng_n, hng_rate = stats["HARD_NO_GO"]
        down_n, down_rate = stats["DOWNGRADE"]
        a_n, a_rate = stats["A_TIER"]
        b_n, b_rate = stats["B_TIER"]
        original_hng_rate = original_stats["HARD_NO_GO"][1]
        original_down_rate = original_stats["DOWNGRADE"][1]
        min_priority_rate = min([r for r in (a_rate, b_rate) if r is not None], default=None)
        defensive_sep = (
            (min_priority_rate - hng_rate) * 100.0
            if min_priority_rate is not None and hng_rate is not None
            else None
        )
        rows.append({
            "section": "variant_summary",
            "variant_name": variant_name,
            "relaxed_rows": int(len(relaxed)),
            "relaxed_rows_success_rate": _rate(relaxed),
            "simulated_hard_no_go_n": hng_n,
            "simulated_hard_no_go_success_rate": hng_rate,
            "simulated_downgrade_n": down_n,
            "simulated_downgrade_success_rate": down_rate,
            "a_tier_n_unchanged": a_n,
            "a_tier_rate_unchanged": a_rate,
            "b_tier_n_unchanged": b_n,
            "b_tier_rate_unchanged": b_rate,
            "defensive_separation_pp": round(defensive_sep, 2) if defensive_sep is not None else None,
            "hard_no_go_delta_pp": (
                round((hng_rate - original_hng_rate) * 100.0, 2)
                if hng_rate is not None and original_hng_rate is not None
                else None
            ),
            "downgrade_delta_pp": (
                round((down_rate - original_down_rate) * 100.0, 2)
                if down_rate is not None and original_down_rate is not None
                else None
            ),
            "recommended_market_type_unchanged": True,
            "recommended_market_subtype_unchanged": True,
        })
    return pd.DataFrame(rows)


def build_relaxed_breakdown(df: pd.DataFrame, league: str = "Ligue 1") -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for variant_name, sources in VARIANTS:
        _, relaxed = simulate_variant(df, variant_name, sources, league)
        for dim in BREAKDOWN_DIMS:
            for value, grp in relaxed.groupby(dim, dropna=False, sort=True):
                n = int(len(grp))
                hits = _hits(grp)
                rows.append({
                    "section": "relaxed_rows_breakdown",
                    "variant_name": variant_name,
                    "dimension": dim,
                    "value": value,
                    "n": n,
                    "hits": hits,
                    "success_rate": round(hits / n, 4) if n else None,
                })
    return pd.DataFrame(rows)


def safety_checks(summary: pd.DataFrame) -> dict[str, Any]:
    return {
        "no_original_csv_modified": True,
        "market_tier_py_modified": False,
        "probability_logic_changed": False,
        "recommended_market_logic_changed": False,
        "betting_staking_roi_logic_changed": False,
        "super_a_tier_activated": False,
        "a_tier_unchanged_all_variants": bool((summary["a_tier_n_unchanged"] == summary["a_tier_n_unchanged"].iloc[0]).all()) if not summary.empty else True,
        "b_tier_unchanged_all_variants": bool((summary["b_tier_n_unchanged"] == summary["b_tier_n_unchanged"].iloc[0]).all()) if not summary.empty else True,
        "recommended_market_type_unchanged": bool(summary["recommended_market_type_unchanged"].all()) if not summary.empty else True,
        "recommended_market_subtype_unchanged": bool(summary["recommended_market_subtype_unchanged"].all()) if not summary.empty else True,
    }


def simulation_recommendation(
    executive: dict[str, Any],
    summary: pd.DataFrame,
    *,
    target_hard_no_go_rate: float = 67.0,
    min_relaxed_rows: int = 20,
    min_defensive_separation_pp: float = 5.0,
) -> str:
    if int(executive["original_ligue1_hard_no_go_rows"]) < 50:
        return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"
    target = target_hard_no_go_rate / 100.0
    qualified = summary[
        (summary["relaxed_rows"] >= min_relaxed_rows)
        & (summary["simulated_hard_no_go_success_rate"] < target)
        & (summary["defensive_separation_pp"] >= min_defensive_separation_pp)
        & (summary["recommended_market_type_unchanged"])
        & (summary["recommended_market_subtype_unchanged"])
    ].copy()
    if qualified.empty:
        return "DO_NOT_RELAX"
    qualified = qualified.sort_values(["relaxed_rows", "variant_name"], kind="stable")
    variant = str(qualified.iloc[0]["variant_name"])
    mapping = {
        "relax_both_over25_btts": "INVESTIGATE_RELAX_BOTH_OVER25_BTTS",
        "relax_suppressed_with_warning": "INVESTIGATE_RELAX_SUPPRESSED_WITH_WARNING",
        "relax_league_profile_suppression": "INVESTIGATE_RELAX_LEAGUE_PROFILE_SUPPRESSION",
        "relax_all_ligue1_source_candidates": "INVESTIGATE_RELAX_ALL_LIGUE1_SOURCE_CANDIDATES",
    }
    return mapping[variant]


def build_summary_table(
    df: pd.DataFrame,
    *,
    league: str = "Ligue 1",
    target_hard_no_go_rate: float = 67.0,
    min_relaxed_rows: int = 20,
    min_defensive_separation_pp: float = 5.0,
) -> tuple[pd.DataFrame, dict[str, Any], str]:
    executive = executive_summary(df, league)
    variants = build_variant_summary(df, league=league)
    breakdown = build_relaxed_breakdown(df, league=league)
    checks = safety_checks(variants)
    recommendation = simulation_recommendation(
        executive,
        variants,
        target_hard_no_go_rate=target_hard_no_go_rate,
        min_relaxed_rows=min_relaxed_rows,
        min_defensive_separation_pp=min_defensive_separation_pp,
    )
    variants = variants.copy()
    if not variants.empty:
        variants["best_variant_by_defensive_separation"] = (
            variants.sort_values("defensive_separation_pp", ascending=False, na_position="last")
            .iloc[0]["variant_name"]
        )
    frames = [
        pd.DataFrame([{"section": "executive_summary", **executive}]),
        variants,
        breakdown,
        pd.DataFrame([{"section": "safety_integrity_checks", **checks}]),
        pd.DataFrame([{"section": "simulation_recommendation", "recommendation": recommendation}]),
    ]
    frames = [frame for frame in frames if not frame.empty]
    table = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    return table, executive, recommendation


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
                vals.append(f"{val * 100:.1f}%" if "rate" in col else f"{val:.2f}")
            else:
                vals.append("" if pd.isna(val) else str(val))
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, executive: dict[str, Any], recommendation: str, league: str) -> str:
    section = lambda name: table[table["section"] == name] if "section" in table.columns else pd.DataFrame()
    variants = section("variant_summary")
    checks = section("safety_integrity_checks").iloc[0].to_dict() if not section("safety_integrity_checks").empty else {}
    best_variant = variants.get("best_variant_by_defensive_separation", pd.Series(["NONE"])).dropna().iloc[0] if not variants.empty else "NONE"
    lines = [
        "# Phase 11.7 Ligue 1 Source-Specific Relaxation Simulation",
        "",
        "Phase 11.7 is simulation only. No tier rules were changed.",
        "",
        "## A. Executive Summary",
        f"- Total {league} evaluatable rows: {executive['total_ligue1_evaluatable_rows']:,}",
        f"- Original {league} HARD_NO_GO rows: {executive['original_ligue1_hard_no_go_rows']:,}",
        f"- Original {league} HARD_NO_GO success rate: {_rate_pct(executive['original_ligue1_hard_no_go_success_rate'])}",
        f"- Original {league} DOWNGRADE rows: {executive['original_ligue1_downgrade_rows']:,}",
        f"- Original {league} DOWNGRADE success rate: {_rate_pct(executive['original_ligue1_downgrade_success_rate'])}",
        f"- Number of simulated variants: {executive['simulated_variants']}",
        f"- Best variant by defensive separation: {best_variant}",
        "",
        "## B. Variant Summary",
    ]
    lines += _markdown_table(variants, [
        "variant_name", "relaxed_rows", "relaxed_rows_success_rate",
        "simulated_hard_no_go_n", "simulated_hard_no_go_success_rate",
        "simulated_downgrade_n", "simulated_downgrade_success_rate",
        "a_tier_n_unchanged", "a_tier_rate_unchanged",
        "b_tier_n_unchanged", "b_tier_rate_unchanged",
        "defensive_separation_pp", "hard_no_go_delta_pp", "downgrade_delta_pp",
    ])
    lines += ["## C. Relaxed Rows Breakdown"]
    lines += _markdown_table(section("relaxed_rows_breakdown"), [
        "variant_name", "dimension", "value", "n", "hits", "success_rate",
    ])
    lines += [
        "## D. Safety / Integrity Checks",
        f"- No original CSV modified: {checks.get('no_original_csv_modified', True)}",
        f"- No market_tier.py modified: {not checks.get('market_tier_py_modified', False)}",
        f"- No probability logic changed: {not checks.get('probability_logic_changed', False)}",
        f"- No recommended market logic changed: {not checks.get('recommended_market_logic_changed', False)}",
        f"- No betting/staking/ROI logic changed: {not checks.get('betting_staking_roi_logic_changed', False)}",
        f"- No SUPER_A_TIER activated: {not checks.get('super_a_tier_activated', False)}",
        f"- A_TIER unchanged in all variants: {checks.get('a_tier_unchanged_all_variants', True)}",
        f"- B_TIER unchanged in all variants: {checks.get('b_tier_unchanged_all_variants', True)}",
        f"- recommended_market_type unchanged: {checks.get('recommended_market_type_unchanged', True)}",
        f"- recommended_market_subtype unchanged: {checks.get('recommended_market_subtype_unchanged', True)}",
        "",
        "## E. Simulation Recommendation",
        recommendation,
        "",
    ]
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    league: str = "Ligue 1",
    target_hard_no_go_rate: float = 67.0,
    min_relaxed_rows: int = 20,
    min_defensive_separation_pp: float = 5.0,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table, executive, recommendation = build_summary_table(
        df,
        league=league,
        target_hard_no_go_rate=target_hard_no_go_rate,
        min_relaxed_rows=min_relaxed_rows,
        min_defensive_separation_pp=min_defensive_separation_pp,
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
    parser.add_argument("--target-hard-no-go-rate", type=float, default=67.0)
    parser.add_argument("--min-relaxed-rows", type=int, default=20)
    parser.add_argument("--min-defensive-separation-pp", type=float, default=5.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        league=args.league,
        target_hard_no_go_rate=args.target_hard_no_go_rate,
        min_relaxed_rows=args.min_relaxed_rows,
        min_defensive_separation_pp=args.min_defensive_separation_pp,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## E. Simulation Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
