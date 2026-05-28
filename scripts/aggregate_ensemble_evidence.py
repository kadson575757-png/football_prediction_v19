# -*- coding: utf-8 -*-
"""Aggregate Phase-10.5 ensemble evidence before any SUPER_A_TIER activation.

Diagnostic only. This script does not change model logic, market-tier logic,
recommended-market logic, probabilities, betting, ROI, or staking.
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

from football_prediction_v19.diagnostics.ensemble_tier import (  # noqa: E402
    normalize_ensemble_agreement,
)

AGREEMENT_ORDER = ["HIGH", "MEDIUM", "LOW", "NONE"]
ENSEMBLE_AGREEMENTS = {"HIGH", "MEDIUM", "LOW"}
OUTPUT_CSV = "ensemble_evidence_summary.csv"
OUTPUT_MD = "ensemble_evidence_summary.md"


class EvidenceScopes(dict):
    """Container for all evaluatable, ensemble-only, and tiered audit scopes."""

    @property
    def all_rows(self) -> pd.DataFrame:
        return self["all_rows"]

    @property
    def ensemble_rows(self) -> pd.DataFrame:
        return self["ensemble_rows"]

    @property
    def tiered_rows(self) -> pd.DataFrame:
        return self["tiered_rows"]

    @property
    def decision_rows(self) -> pd.DataFrame:
        return self["decision_rows"]


def _parse_bool(value: Any) -> bool | None:
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


def _clean_warning_flag(value: Any) -> str:
    if value is None or pd.isna(value):
        return "clean"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return "clean"
    return "warned"


def load_evaluation_rows(input_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted(input_dir.glob("*_evaluation.csv")):
        df = pd.read_csv(path)
        df["source_file"] = path.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True, sort=False)
    if "type_success" not in out.columns:
        return out.iloc[0:0].copy()

    out["type_success_bool"] = out["type_success"].apply(_parse_bool)
    out = out[out["type_success_bool"].notna()].copy()
    out["type_success_bool"] = out["type_success_bool"].astype(bool)

    if "ensemble_agreement" not in out.columns:
        out["ensemble_agreement"] = "NONE"
    out["ensemble_agreement"] = out["ensemble_agreement"].apply(normalize_ensemble_agreement)

    for col in (
        "league",
        "market_tier",
        "recommended_market_subtype",
        "league_warning_flags",
    ):
        if col not in out.columns:
            out[col] = ""
    out["market_tier"] = out["market_tier"].fillna("").astype(str).str.strip()
    out["league"] = out["league"].fillna("").astype(str).str.strip()
    out["recommended_market_subtype"] = (
        out["recommended_market_subtype"].fillna("").astype(str).str.strip()
    )
    out["warning_state"] = out["league_warning_flags"].apply(_clean_warning_flag)
    return out


def build_scopes(df: pd.DataFrame) -> EvidenceScopes:
    """Separate all, ensemble-only, tiered, and decision evidence scopes."""
    if df.empty:
        empty = df.copy()
        return EvidenceScopes(
            all_rows=empty,
            ensemble_rows=empty,
            tiered_rows=empty,
            decision_rows=empty,
        )
    all_rows = df.copy()
    ensemble_rows = all_rows[all_rows["ensemble_agreement"].isin(ENSEMBLE_AGREEMENTS)].copy()
    tiered_rows = all_rows[all_rows["market_tier"].astype(str).str.strip().ne("")].copy()
    decision_rows = ensemble_rows[
        ensemble_rows["market_tier"].astype(str).str.strip().ne("")
    ].copy()
    return EvidenceScopes(
        all_rows=all_rows,
        ensemble_rows=ensemble_rows,
        tiered_rows=tiered_rows,
        decision_rows=decision_rows,
    )


def _aggregate(df: pd.DataFrame, group_cols: list[str], section: str) -> pd.DataFrame:
    cols = ["section", *group_cols, "n", "hits", "success_rate", "small_sample"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    rows: list[dict[str, Any]] = []
    for keys, grp in df.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n = int(len(grp))
        hits = int(grp["type_success_bool"].sum())
        row = {
            "section": section,
            "n": n,
            "hits": hits,
            "success_rate": round(hits / n, 4) if n else 0.0,
            "small_sample": n < 20,
        }
        row.update(dict(zip(group_cols, keys)))
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def build_summary_table(df: pd.DataFrame, *, include_none: bool = True) -> pd.DataFrame:
    scopes = build_scopes(df)
    all_rows = scopes.all_rows if include_none else scopes.ensemble_rows
    ensemble_rows = scopes.ensemble_rows
    tiered_rows = scopes.tiered_rows
    decision_rows = scopes.decision_rows
    sections = [
        _aggregate(all_rows, ["ensemble_agreement"], "success_by_ensemble_agreement"),
        _aggregate(tiered_rows, ["market_tier"], "success_by_market_tier"),
        _aggregate(decision_rows, ["market_tier", "ensemble_agreement"], "success_by_market_tier_x_ensemble_agreement"),
        _aggregate(decision_rows, ["league", "market_tier", "ensemble_agreement"], "success_by_league_x_market_tier_x_ensemble_agreement"),
        _aggregate(ensemble_rows, ["recommended_market_subtype", "ensemble_agreement"], "success_by_recommended_market_subtype_x_ensemble_agreement"),
        _aggregate(all_rows, ["warning_state"], "success_by_league_warning_flags_clean_vs_warned"),
    ]
    return pd.concat(sections, ignore_index=True, sort=False) if sections else pd.DataFrame()


def _rate_for(df: pd.DataFrame, **filters: str) -> tuple[int, float | None]:
    sub = df.copy()
    for col, value in filters.items():
        sub = sub[sub[col] == value]
    n = int(len(sub))
    if n == 0:
        return 0, None
    return n, float(sub["type_success_bool"].sum()) / n


def super_a_tier_decision(df: pd.DataFrame) -> tuple[str, list[str]]:
    df = build_scopes(df).decision_rows
    reasons: list[str] = []
    reasons.append("Decision is based on ensemble-only rows.")
    a_high_n, a_high_rate = _rate_for(df, market_tier="A_TIER", ensemble_agreement="HIGH")
    a_med_n, a_med_rate = _rate_for(df, market_tier="A_TIER", ensemble_agreement="MEDIUM")
    a_all_n, a_all_rate = _rate_for(df, market_tier="A_TIER")

    if a_high_n < 50 or a_med_rate is None or a_all_rate is None:
        reasons.append(
            "INCONCLUSIVE: A_TIER + HIGH or comparison sample is too small."
        )
        return "INCONCLUSIVE", reasons

    high_vs_medium = a_high_rate - a_med_rate
    high_vs_overall = a_high_rate - a_all_rate
    reasons.append(
        f"A_TIER + HIGH: n={a_high_n}, rate={a_high_rate:.1%}; "
        f"A_TIER + MEDIUM: n={a_med_n}, rate={a_med_rate:.1%}; "
        f"overall A_TIER: n={a_all_n}, rate={a_all_rate:.1%}."
    )

    if high_vs_medium <= 0:
        reasons.append("NO: A_TIER + HIGH is worse than or equal to A_TIER + MEDIUM.")
        return "NO", reasons
    if high_vs_medium < 0.02 or high_vs_overall < 0.02:
        reasons.append("NO: A_TIER + HIGH does not clear the required 2 percentage point uplift.")
        return "NO", reasons

    stable_leagues = 0
    inconsistent: list[str] = []
    for league, grp in df[df["market_tier"] == "A_TIER"].groupby("league", dropna=False):
        high_n, high_rate = _rate_for(grp, ensemble_agreement="HIGH")
        med_n, med_rate = _rate_for(grp, ensemble_agreement="MEDIUM")
        if high_n < 10:
            continue
        if med_rate is None:
            inconsistent.append(str(league))
            continue
        if high_rate - med_rate >= 0.02:
            stable_leagues += 1
        else:
            inconsistent.append(str(league))

    if stable_leagues >= 3 and not inconsistent:
        reasons.append(
            f"YES: A_TIER + HIGH uplift is stable in {stable_leagues} leagues with n>=10."
        )
        return "YES", reasons

    reasons.append(
        f"NO: evidence is inconsistent across leagues; stable leagues={stable_leagues}, "
        f"inconsistent={', '.join(inconsistent) if inconsistent else 'none'}."
    )
    return "NO", reasons


def _format_section(table: pd.DataFrame, section: str, title: str, group_cols: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    sub = table[table["section"] == section].copy()
    if sub.empty:
        lines += ["No evaluatable rows.", ""]
        return lines
    lines.append("| " + " | ".join([*group_cols, "n", "hits", "success_rate", "small_sample"]) + " |")
    lines.append("| " + " | ".join(["---"] * (len(group_cols) + 4)) + " |")
    for _, row in sub.iterrows():
        values = [str(row.get(col, "")) for col in group_cols]
        values += [
            str(int(row["n"])),
            str(int(row["hits"])),
            f"{float(row['success_rate']):.1%}",
            "YES" if bool(row["small_sample"]) else "",
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(df: pd.DataFrame, table: pd.DataFrame) -> str:
    scopes = build_scopes(df)
    decision, reasons = super_a_tier_decision(df)
    non_ensemble_n = int(len(scopes.all_rows) - len(scopes.ensemble_rows))
    blank_tier_n = int(scopes.all_rows["market_tier"].astype(str).str.strip().eq("").sum()) if not scopes.all_rows.empty else 0
    lines: list[str] = [
        "# Phase 10.5 Ensemble Evidence Audit",
        "",
        "Diagnostic evidence summary before any SUPER_A_TIER activation.",
        "",
        "SUPER_A_TIER should not be activated unless HIGH ensemble consensus shows a stable uplift.",
        "",
        f"- Total evaluatable rows: {len(scopes.all_rows):,}",
        f"- Ensemble evaluatable rows: {len(scopes.ensemble_rows):,}",
        f"- Non-ensemble/NONE rows: {non_ensemble_n:,}",
        f"- Blank market_tier rows: {blank_tier_n:,}",
        "",
    ]
    if non_ensemble_n or blank_tier_n:
        lines += [
            "> WARNING: old/non-ensemble rows or blank market_tier rows are present. "
            "Decision logic excludes them and uses ensemble-only rows with non-empty market_tier.",
            "",
        ]
    lines += _format_section(table, "success_by_ensemble_agreement", "Success by ensemble_agreement", ["ensemble_agreement"])
    lines += _format_section(table, "success_by_market_tier", "Success by market_tier", ["market_tier"])
    lines += _format_section(table, "success_by_market_tier_x_ensemble_agreement", "Success by market_tier x ensemble_agreement", ["market_tier", "ensemble_agreement"])
    lines += _format_section(table, "success_by_league_x_market_tier_x_ensemble_agreement", "Success by league x market_tier x ensemble_agreement", ["league", "market_tier", "ensemble_agreement"])
    lines += _format_section(table, "success_by_recommended_market_subtype_x_ensemble_agreement", "Success by recommended_market_subtype x ensemble_agreement", ["recommended_market_subtype", "ensemble_agreement"])
    lines += _format_section(table, "success_by_league_warning_flags_clean_vs_warned", "Success by league_warning_flags clean vs warned", ["warning_state"])
    lines += [
        "## Small-Sample Warning",
        "",
        "Rows with n < 20 are marked as small_sample=YES and should remain observational.",
        "",
        "## SUPER_A_TIER Evidence Decision",
        "",
        f"Decision: **{decision}**",
        "",
    ]
    lines += [f"- {reason}" for reason in reasons]
    lines.append("")
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    ensemble_only: bool = False,
    include_none: bool = True,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    scopes = build_scopes(df)
    summary_df = scopes.ensemble_rows if ensemble_only else df
    table = build_summary_table(summary_df, include_none=include_none)
    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    markdown = build_markdown(df, table)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(ROOT / "outputs/season_replay"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/season_replay"))
    parser.add_argument(
        "--ensemble-only",
        action="store_true",
        help="Write summary tables from ensemble rows only. Decision always uses ensemble-only tiered rows.",
    )
    parser.add_argument(
        "--include-none",
        action="store_true",
        default=True,
        help="Include diagnostic NONE rows in summary tables when not using --ensemble-only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        Path(args.input_dir),
        Path(args.output_dir),
        ensemble_only=args.ensemble_only,
        include_none=args.include_none,
    )
    decision = "UNKNOWN"
    for line in markdown.splitlines():
        if line.startswith("Decision:"):
            decision = line.replace("Decision:", "").strip().strip("*")
            break
    print(f"Wrote {len(table)} summary rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(f"SUPER_A_TIER evidence decision: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
