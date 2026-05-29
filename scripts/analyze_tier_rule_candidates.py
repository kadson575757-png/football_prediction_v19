# -*- coding: utf-8 -*-
"""Phase 11 data-driven tier rule evidence mining.

Diagnostic/reporting only. This script does not change probability logic,
recommended-market logic, market-tier logic, betting, staking, ROI, or
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

from football_prediction_v19.diagnostics.ensemble_tier import (  # noqa: E402
    normalize_ensemble_agreement,
)

OUTPUT_CSV = "tier_rule_candidate_summary.csv"
OUTPUT_MD = "tier_rule_candidate_summary.md"
STABILITY_CSV = "tier_rule_stability_summary.csv"
STABILITY_MD = "tier_rule_stability_summary.md"
ENSEMBLE_LABELS = {"HIGH", "MEDIUM", "LOW"}
ACTIONABLE_CATEGORIES = {
    "PROMOTE_CANDIDATE",
    "DOWNGRADE_CANDIDATE",
    "NO_GO_CANDIDATE",
    "SMALL_SAMPLE_OBSERVE",
}

SUMMARY_SECTIONS: tuple[tuple[str, str, list[str]], ...] = (
    ("A", "Overall success by market_tier", ["market_tier"]),
    ("B", "Success by market_tier x ensemble_agreement", ["market_tier", "ensemble_agreement"]),
    ("C", "Success by market_tier x warning_state", ["market_tier", "warning_state"]),
    ("D", "Success by market_tier x league_adjusted_strength", ["market_tier", "league_adjusted_strength"]),
    ("E", "Success by market_tier x recommended_market_subtype", ["market_tier", "recommended_market_subtype"]),
    ("F", "Success by league x market_tier", ["league", "market_tier"]),
    ("G", "Success by league x recommended_market_subtype", ["league", "recommended_market_subtype"]),
    ("H", "Success by market_tier x chaos_bucket", ["market_tier", "chaos_bucket"]),
    ("I", "Success by market_tier x ctrl_bucket", ["market_tier", "ctrl_bucket"]),
    ("J", "Success by market_tier x odds_bucket", ["market_tier", "odds_bucket"]),
    ("K", "Success by market_tier x season_phase", ["market_tier", "season_phase"]),
)


def parse_bool_success(value: Any) -> bool | None:
    """Parse replay/evaluator truth values without treating blanks as False."""
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


def warning_state(value: Any) -> str:
    if value is None or pd.isna(value):
        return "clean"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return "clean"
    return "warned"


def _norm_text(value: Any, default: str = "UNKNOWN") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return default
    return text


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

    if "ensemble_agreement" not in df.columns:
        df["ensemble_agreement"] = "NONE"
    df["ensemble_agreement"] = df["ensemble_agreement"].apply(normalize_ensemble_agreement)

    for col in (
        "league",
        "market_tier",
        "league_adjusted_strength",
        "recommended_market_subtype",
        "league_warning_flags",
        "chaos_bucket",
        "ctrl_bucket",
        "odds_bucket",
        "season_phase",
    ):
        if col not in df.columns:
            df[col] = "UNKNOWN"

    df["league"] = df["league"].apply(_norm_text)
    df["market_tier"] = df["market_tier"].apply(_norm_text)
    df["league_adjusted_strength"] = df["league_adjusted_strength"].apply(_norm_text)
    df["recommended_market_subtype"] = df["recommended_market_subtype"].apply(_norm_text)
    df["chaos_bucket"] = df["chaos_bucket"].apply(_norm_text)
    df["ctrl_bucket"] = df["ctrl_bucket"].apply(_norm_text)
    df["odds_bucket"] = df["odds_bucket"].apply(_norm_text)
    df["season_phase"] = df["season_phase"].apply(_norm_text)
    df["warning_state"] = df["league_warning_flags"].apply(warning_state)
    return df


def ensure_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with all normalized columns required by summary sections."""
    out = df.copy()
    if "type_success_bool" not in out.columns and "type_success" in out.columns:
        out["type_success_bool"] = out["type_success"].apply(parse_bool_success)
        out = out[out["type_success_bool"].notna()].copy()
        out["type_success_bool"] = out["type_success_bool"].astype(bool)
    for col in (
        "league",
        "market_tier",
        "league_adjusted_strength",
        "recommended_market_subtype",
        "chaos_bucket",
        "ctrl_bucket",
        "odds_bucket",
        "season_phase",
    ):
        if col not in out.columns:
            out[col] = "UNKNOWN"
        out[col] = out[col].apply(_norm_text)
    if "ensemble_agreement" not in out.columns:
        out["ensemble_agreement"] = "NONE"
    out["ensemble_agreement"] = out["ensemble_agreement"].apply(normalize_ensemble_agreement)
    if "league_warning_flags" not in out.columns:
        out["league_warning_flags"] = ""
    if "warning_state" not in out.columns:
        out["warning_state"] = out["league_warning_flags"].apply(warning_state)
    return out


class EvidenceScopes(dict):
    @property
    def all_rows(self) -> pd.DataFrame:
        return self["all_rows"]

    @property
    def modern_tier_rows(self) -> pd.DataFrame:
        return self["modern_tier_rows"]

    @property
    def ensemble_rows(self) -> pd.DataFrame:
        return self["ensemble_rows"]


def build_scopes(df: pd.DataFrame) -> EvidenceScopes:
    all_rows = ensure_analysis_columns(df)
    modern_tier_rows = all_rows[
        all_rows["market_tier"].astype(str).str.strip().ne("")
        & (all_rows["market_tier"] != "UNKNOWN")
    ].copy()
    ensemble_rows = all_rows[all_rows["ensemble_agreement"].isin(ENSEMBLE_LABELS)].copy()
    return EvidenceScopes(
        all_rows=all_rows,
        modern_tier_rows=modern_tier_rows,
        ensemble_rows=ensemble_rows,
    )


def select_decision_rows(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    scopes = build_scopes(df)
    if scope == "all":
        return scopes.all_rows
    if scope == "ensemble-only":
        return scopes.ensemble_rows
    return scopes.modern_tier_rows


def aggregate_section(df: pd.DataFrame, section_id: str, title: str, group_cols: list[str]) -> pd.DataFrame:
    columns = [
        "section_id",
        "section",
        "group_cols",
        *group_cols,
        "n",
        "hits",
        "success_rate",
        "parent_market_tier_rate",
        "delta_vs_parent_pp",
        "candidate_category",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    parent_rates = (
        df.groupby("market_tier")["type_success_bool"].mean().to_dict()
        if "market_tier" in df.columns
        else {}
    )
    rows: list[dict[str, Any]] = []
    for keys, grp in df.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n = int(len(grp))
        hits = int(grp["type_success_bool"].sum())
        rate = hits / n if n else 0.0
        market_tier = str(dict(zip(group_cols, keys)).get("market_tier", "UNKNOWN"))
        parent_rate = parent_rates.get(market_tier)
        delta = None if parent_rate is None else (rate - float(parent_rate)) * 100.0
        row: dict[str, Any] = {
            "section_id": section_id,
            "section": title,
            "group_cols": " x ".join(group_cols),
            "n": n,
            "hits": hits,
            "success_rate": round(rate, 4),
            "parent_market_tier_rate": round(float(parent_rate), 4) if parent_rate is not None else None,
            "delta_vs_parent_pp": round(delta, 2) if delta is not None else None,
            "candidate_category": "",
        }
        row.update(dict(zip(group_cols, keys)))
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_analysis_columns(df)
    tables = [
        aggregate_section(df, section_id, title, group_cols)
        for section_id, title, group_cols in SUMMARY_SECTIONS
    ]
    non_empty = [
        table.dropna(axis=1, how="all")
        for table in tables
        if not table.empty and not table.dropna(axis=1, how="all").empty
    ]
    return pd.concat(non_empty, ignore_index=True, sort=False) if non_empty else pd.DataFrame()


def apply_candidate_detection(
    table: pd.DataFrame,
    *,
    min_sample: int,
    small_sample: int,
    threshold_pp: float,
) -> pd.DataFrame:
    out = table.copy()
    categories: list[str] = []
    for _, row in out.iterrows():
        n = int(row.get("n", 0) or 0)
        rate = float(row.get("success_rate", 0.0) or 0.0)
        delta = row.get("delta_vs_parent_pp")
        if n < small_sample:
            categories.append("SMALL_SAMPLE_OBSERVE")
        elif n >= min_sample and rate < 0.65:
            categories.append("NO_GO_CANDIDATE")
        elif n >= min_sample and pd.notna(delta) and float(delta) >= threshold_pp:
            categories.append("PROMOTE_CANDIDATE")
        elif n >= min_sample and pd.notna(delta) and float(delta) <= -threshold_pp:
            categories.append("DOWNGRADE_CANDIDATE")
        else:
            categories.append("")
    out["candidate_category"] = categories
    return out


def phase11_recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE"
    total = len(table)
    small = int((table["candidate_category"] == "SMALL_SAMPLE_OBSERVE").sum())
    actionable = table[table["candidate_category"].isin([
        "PROMOTE_CANDIDATE",
        "DOWNGRADE_CANDIDATE",
        "NO_GO_CANDIDATE",
    ])]
    if actionable.empty and total and small > total / 2:
        return "INCONCLUSIVE"
    has_promote = (table["candidate_category"] == "PROMOTE_CANDIDATE").any()
    has_downgrade = table["candidate_category"].isin([
        "DOWNGRADE_CANDIDATE",
        "NO_GO_CANDIDATE",
    ]).any()
    if has_promote and has_downgrade:
        return "INVESTIGATE_PROMOTION_AND_DOWNGRADE_RULES"
    if has_promote:
        return "INVESTIGATE_PROMOTION_RULES"
    if has_downgrade:
        return "INVESTIGATE_DOWNGRADE_RULES"
    return "HOLD_CURRENT_RULES"


def _candidate_mask(df: pd.DataFrame, row: pd.Series) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    group_cols = str(row.get("group_cols", "")).split(" x ")
    for col in group_cols:
        if not col or col == "league":
            continue
        if col in df.columns and col in row and pd.notna(row.get(col)):
            mask &= df[col].astype(str) == str(row.get(col))
    return mask


def _candidate_key(row: pd.Series) -> str:
    group_cols = [c for c in str(row.get("group_cols", "")).split(" x ") if c]
    parts = [
        f"{col}={row.get(col, '')}"
        for col in group_cols
        if col in row and pd.notna(row.get(col))
    ]
    return " | ".join(parts)


def build_stability_table(
    df: pd.DataFrame,
    candidate_table: pd.DataFrame,
    *,
    min_sample: int,
    threshold_pp: float,
) -> pd.DataFrame:
    df = ensure_analysis_columns(df)
    if df.empty or candidate_table.empty:
        return pd.DataFrame(columns=[
            "section_id", "section", "candidate_key", "candidate_category",
            "market_tier", "n", "hits", "success_rate", "parent_market_tier_rate",
            "delta_vs_parent_pp", "leagues_with_n_ge_10",
            "leagues_beating_parent_by_threshold", "leagues_trailing_parent_by_threshold",
            "min_league_rate", "max_league_rate", "stability_label",
        ])

    candidates = candidate_table[
        candidate_table["candidate_category"].astype(str).isin(ACTIONABLE_CATEGORIES)
    ].copy()
    parent_rates = df.groupby("market_tier")["type_success_bool"].mean().to_dict()
    rows: list[dict[str, Any]] = []

    for _, cand in candidates.iterrows():
        sub = df[_candidate_mask(df, cand)].copy()
        n = int(len(sub))
        hits = int(sub["type_success_bool"].sum()) if n else 0
        rate = hits / n if n else 0.0
        market_tier = str(cand.get("market_tier", "UNKNOWN"))
        parent_rate = parent_rates.get(market_tier)
        delta = None if parent_rate is None else (rate - float(parent_rate)) * 100.0

        leagues_with_n = 0
        beating = 0
        trailing = 0
        league_rates: list[float] = []
        for league, lg in sub.groupby("league", dropna=False):
            lg_n = int(len(lg))
            if lg_n < 10:
                continue
            leagues_with_n += 1
            lg_rate = float(lg["type_success_bool"].mean())
            league_rates.append(lg_rate)
            parent_lg = df[(df["league"] == league) & (df["market_tier"] == market_tier)]
            if parent_lg.empty:
                continue
            lg_delta = (lg_rate - float(parent_lg["type_success_bool"].mean())) * 100.0
            if lg_delta >= threshold_pp:
                beating += 1
            if lg_delta <= -threshold_pp:
                trailing += 1

        min_lg = min(league_rates) if league_rates else None
        max_lg = max(league_rates) if league_rates else None
        label = _stability_label(
            n=n,
            rate=rate,
            delta=delta,
            leagues_with_n=leagues_with_n,
            beating=beating,
            trailing=trailing,
            min_sample=min_sample,
            threshold_pp=threshold_pp,
        )
        rows.append({
            "section_id": cand.get("section_id", ""),
            "section": cand.get("section", ""),
            "candidate_key": _candidate_key(cand),
            "candidate_category": cand.get("candidate_category", ""),
            "market_tier": market_tier,
            "n": n,
            "hits": hits,
            "success_rate": round(rate, 4),
            "parent_market_tier_rate": round(float(parent_rate), 4) if parent_rate is not None else None,
            "delta_vs_parent_pp": round(delta, 2) if delta is not None else None,
            "leagues_with_n_ge_10": leagues_with_n,
            "leagues_beating_parent_by_threshold": beating,
            "leagues_trailing_parent_by_threshold": trailing,
            "min_league_rate": round(min_lg, 4) if min_lg is not None else None,
            "max_league_rate": round(max_lg, 4) if max_lg is not None else None,
            "stability_label": label,
        })
    return pd.DataFrame(rows)


def _stability_label(
    *,
    n: int,
    rate: float,
    delta: float | None,
    leagues_with_n: int,
    beating: int,
    trailing: int,
    min_sample: int,
    threshold_pp: float,
) -> str:
    strong = (
        delta is not None
        and (delta >= threshold_pp or delta <= -threshold_pp or rate < 0.65)
    )
    if n < min_sample or leagues_with_n < 2:
        return "SMALL_SAMPLE"
    if strong and leagues_with_n <= 2:
        return "LEAGUE_SPECIFIC"
    if n >= min_sample and rate < 0.65 and leagues_with_n >= 3 and trailing >= 2:
        return "STABLE_NO_GO"
    if beating >= 1 and trailing >= 1:
        return "UNSTABLE"
    if (
        n >= min_sample
        and delta is not None
        and delta >= threshold_pp
        and leagues_with_n >= 3
        and beating >= 2
        and trailing <= 1
    ):
        return "STABLE_PROMOTE"
    if (
        n >= min_sample
        and delta is not None
        and delta <= -threshold_pp
        and leagues_with_n >= 3
        and trailing >= 2
        and beating <= 1
    ):
        return "STABLE_DOWNGRADE"
    return "UNSTABLE" if strong else "SMALL_SAMPLE"


def stability_recommendation(stability_table: pd.DataFrame) -> str:
    if stability_table.empty:
        return "HOLD_CURRENT_RULES"
    labels = set(stability_table["stability_label"].astype(str))
    has_promote = "STABLE_PROMOTE" in labels
    has_down = bool({"STABLE_DOWNGRADE", "STABLE_NO_GO"} & labels)
    if has_promote and has_down:
        return "RECOMMEND_INVESTIGATE_PROMOTION_AND_DOWNGRADE_PATCH"
    if has_down:
        return "RECOMMEND_INVESTIGATE_DOWNGRADE_RULE_PATCH"
    if has_promote:
        return "RECOMMEND_INVESTIGATE_PROMOTION_RULE_PATCH"
    if labels <= {"LEAGUE_SPECIFIC", "SMALL_SAMPLE"} and "LEAGUE_SPECIFIC" in labels:
        return "RECOMMEND_LEAGUE_SPECIFIC_RULE_REVIEW"
    return "HOLD_CURRENT_RULES"


def build_stability_markdown(stability_table: pd.DataFrame, *, scope: str) -> str:
    lines = [
        "# Phase 11.2 Candidate Stability Validation",
        "",
        "Phase 11.2 is diagnostic only. No tier rules were changed.",
        "",
        f"- Decision scope used: {scope}",
        f"- Candidate groups validated: {len(stability_table):,}",
        "",
    ]
    sections = [
        ("A", "Stability Summary", None),
        ("B", "Stable Promote Candidates", "STABLE_PROMOTE"),
        ("C", "Stable Downgrade Candidates", "STABLE_DOWNGRADE"),
        ("D", "Stable No-Go Candidates", "STABLE_NO_GO"),
        ("E", "League-Specific Candidates", "LEAGUE_SPECIFIC"),
        ("F", "Unstable / Conflicting Candidates", "UNSTABLE"),
        ("G", "Small-Sample Candidates", "SMALL_SAMPLE"),
    ]
    for section_id, title, label in sections:
        sub = stability_table if label is None else stability_table[
            stability_table["stability_label"] == label
        ]
        lines += [f"## {section_id}. {title}", ""]
        if sub.empty:
            lines += ["No candidates.", ""]
            continue
        cols = [
            "candidate_key", "n", "hits", "success_rate", "delta_vs_parent_pp",
            "leagues_with_n_ge_10", "leagues_beating_parent_by_threshold",
            "leagues_trailing_parent_by_threshold", "stability_label",
        ]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for _, row in sub.iterrows():
            values = [
                str(row.get("candidate_key", "")),
                str(int(row.get("n", 0))),
                str(int(row.get("hits", 0))),
                f"{float(row.get('success_rate', 0.0)):.1%}",
                "" if pd.isna(row.get("delta_vs_parent_pp")) else f"{float(row.get('delta_vs_parent_pp')):.1f}",
                str(int(row.get("leagues_with_n_ge_10", 0))),
                str(int(row.get("leagues_beating_parent_by_threshold", 0))),
                str(int(row.get("leagues_trailing_parent_by_threshold", 0))),
                str(row.get("stability_label", "")),
            ]
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")
    lines += [
        "## H. Recommended Next Action",
        "",
        stability_recommendation(stability_table),
        "",
    ]
    return "\n".join(lines)


def _format_section(table: pd.DataFrame, section_id: str, title: str) -> list[str]:
    if table.empty or "section_id" not in table.columns:
        return [f"## {section_id}. {title}", "", "No evaluatable rows.", ""]
    sub = table[table["section_id"] == section_id].copy()
    lines = [f"## {section_id}. {title}", ""]
    if sub.empty:
        return lines + ["No evaluatable rows.", ""]
    group_cols = str(sub["group_cols"].iloc[0]).split(" x ")
    columns = [*group_cols, "n", "hits", "success_rate", "delta_vs_parent_pp", "candidate_category"]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in sub.iterrows():
        values = [str(row.get(col, "")) for col in group_cols]
        values += [
            str(int(row["n"])),
            str(int(row["hits"])),
            f"{float(row['success_rate']):.1%}",
            "" if pd.isna(row.get("delta_vs_parent_pp")) else f"{float(row['delta_vs_parent_pp']):.1f}",
            str(row.get("candidate_category", "")),
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(df: pd.DataFrame, table: pd.DataFrame, *, scope: str = "modern-tier") -> str:
    scopes = build_scopes(df)
    recommendation = phase11_recommendation(table)
    unknown_n = int((scopes.all_rows["market_tier"] == "UNKNOWN").sum()) if not scopes.all_rows.empty else 0
    lines = [
        "# Phase 11 Tier Rule Candidate Analysis",
        "",
        "Phase 11 is diagnostic only. No tier rules were changed.",
        "",
        f"- Total evaluatable rows: {len(scopes.all_rows):,}",
        f"- Modern tier rows: {len(scopes.modern_tier_rows):,}",
        f"- UNKNOWN market_tier rows: {unknown_n:,}",
        f"- Ensemble rows: {len(scopes.ensemble_rows):,}",
        f"- Decision scope used: {scope}",
        f"- Candidate groups: {int(table['candidate_category'].astype(str).ne('').sum()) if not table.empty else 0:,}",
        "",
    ]
    for section_id, title, _ in SUMMARY_SECTIONS:
        lines += _format_section(table, section_id, title)
    lines += [
        "## Phase 11 Recommendation",
        "",
        recommendation,
        "",
        "No betting logic, staking logic, ROI logic, probability logic, or recommended-market logic was changed.",
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    input_dir: Path,
    output_dir: Path,
    min_sample: int = 50,
    small_sample: int = 20,
    threshold_pp: float = 3.0,
    scope: str = "modern-tier",
    stability_report: bool = False,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    decision_df = select_decision_rows(df, scope)
    table = build_summary_table(decision_df)
    table = apply_candidate_detection(
        table,
        min_sample=min_sample,
        small_sample=small_sample,
        threshold_pp=threshold_pp,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    markdown = build_markdown(df, table, scope=scope)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    if stability_report:
        stability = build_stability_table(
            decision_df,
            table,
            min_sample=min_sample,
            threshold_pp=threshold_pp,
        )
        stability.to_csv(output_dir / STABILITY_CSV, index=False)
        stability_md = build_stability_markdown(stability, scope=scope)
        (output_dir / STABILITY_MD).write_text(stability_md, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(ROOT / "outputs/season_replay"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/diagnostics"))
    parser.add_argument("--min-sample", type=int, default=50)
    parser.add_argument("--small-sample", type=int, default=20)
    parser.add_argument("--threshold-pp", type=float, default=3.0)
    parser.add_argument(
        "--scope",
        choices=["all", "modern-tier", "ensemble-only"],
        default="modern-tier",
        help="Evidence cohort used for candidate detection and Phase 11 recommendation.",
    )
    parser.add_argument(
        "--stability-report",
        action="store_true",
        help="Generate Phase 11.2 candidate stability CSV and markdown reports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        min_sample=args.min_sample,
        small_sample=args.small_sample,
        threshold_pp=args.threshold_pp,
        scope=args.scope,
        stability_report=args.stability_report,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(f"Phase 11 recommendation: {phase11_recommendation(table)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
