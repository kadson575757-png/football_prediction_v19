# -*- coding: utf-8 -*-
"""Phase 11.4 post-11.3 multi-league impact audit.

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

OUTPUT_CSV = "phase11_3_impact_summary.csv"
OUTPUT_MD = "phase11_3_impact_summary.md"
PHASE_11_3_RE = re.compile(r"phase_11_3_[a-z0-9_]+", re.IGNORECASE)


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


def _norm_text(value: Any, default: str = "UNKNOWN") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return default
    return text


def _rate(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    return float(df["type_success_bool"].mean())


def _rate_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _hits(df: pd.DataFrame) -> int:
    return int(df["type_success_bool"].sum()) if not df.empty else 0


def _reason_flag_columns(df: pd.DataFrame) -> list[str]:
    return [
        col for col in df.columns
        if "reason" in col.lower() or "flag" in col.lower()
    ]


def extract_phase11_3_flags(row: pd.Series) -> list[str]:
    """Return unique Phase 11.3 flags from reason/flag-like columns."""
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
        "market_tier_reason",
        "market_tier_flags",
    ):
        if col not in df.columns:
            df[col] = ""

    for col in ("league", "market_tier", "recommended_market_type", "recommended_market_subtype"):
        df[col] = df[col].apply(_norm_text)

    df["phase_11_3_flags"] = df.apply(lambda row: " | ".join(extract_phase11_3_flags(row)), axis=1)
    df["phase_11_3_impacted"] = df["phase_11_3_flags"].astype(str).str.contains("phase_11_3", case=False, na=False)
    return df


def _summary_row(section: str, group: str, df: pd.DataFrame, **extra: Any) -> dict[str, Any]:
    n = int(len(df))
    hits = _hits(df)
    row = {
        "section": section,
        "group": group,
        "n": n,
        "hits": hits,
        "success_rate": round(hits / n, 4) if n else None,
    }
    row.update(extra)
    return row


def build_executive_summary(df: pd.DataFrame) -> dict[str, Any]:
    impacted = df[df["phase_11_3_impacted"]]
    non_impacted = df[~df["phase_11_3_impacted"]]
    hard_no_go = df[df["market_tier"] == "HARD_NO_GO"]
    a_tier = df[df["market_tier"] == "A_TIER"]
    b_tier = df[df["market_tier"] == "B_TIER"]
    total = int(len(df))
    impacted_n = int(len(impacted))
    return {
        "total_evaluatable_rows": total,
        "impacted_rows": impacted_n,
        "impacted_row_percentage": round(impacted_n / total, 4) if total else None,
        "impacted_success_rate": _rate(impacted),
        "non_impacted_success_rate": _rate(non_impacted),
        "hard_no_go_success_rate": _rate(hard_no_go),
        "a_tier_success_rate": _rate(a_tier),
        "b_tier_success_rate": _rate(b_tier),
    }


def build_impact_by_flag(df: pd.DataFrame) -> pd.DataFrame:
    impacted = df[df["phase_11_3_impacted"]].copy()
    rows: list[dict[str, Any]] = []
    for _, row in impacted.iterrows():
        for flag in str(row.get("phase_11_3_flags", "")).split("|"):
            flag = flag.strip()
            if flag:
                item = row.to_dict()
                item["phase_11_3_flag"] = flag
                rows.append(item)
    if not rows:
        return pd.DataFrame(columns=[
            "section", "phase_11_3_flag", "n", "hits", "success_rate",
            "leagues", "top_recommended_market_subtypes",
        ])
    exploded = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for flag, grp in exploded.groupby("phase_11_3_flag", sort=True):
        subtype_counts = grp["recommended_market_subtype"].value_counts().head(5)
        out.append({
            "section": "impact_by_phase_11_3_flag",
            "phase_11_3_flag": flag,
            "n": int(len(grp)),
            "hits": _hits(grp),
            "success_rate": round(float(grp["type_success_bool"].mean()), 4),
            "leagues": ", ".join(sorted(str(x) for x in grp["league"].dropna().unique())),
            "top_recommended_market_subtypes": ", ".join(
                f"{idx} ({count})" for idx, count in subtype_counts.items()
            ),
        })
    return pd.DataFrame(out)


def _impact_group(df: pd.DataFrame, group_col: str, section: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame()
    for value, grp in df.groupby(group_col, dropna=False, sort=True):
        impacted = grp[grp["phase_11_3_impacted"]]
        non_impacted = grp[~grp["phase_11_3_impacted"]]
        n = int(len(grp))
        impacted_n = int(len(impacted))
        rows.append({
            "section": section,
            group_col: value,
            "n": n,
            "impacted_n": impacted_n,
            "impacted_percentage": round(impacted_n / n, 4) if n else None,
            "impacted_hits": _hits(impacted),
            "impacted_success_rate": round(float(impacted["type_success_bool"].mean()), 4) if impacted_n else None,
            "non_impacted_hits": _hits(non_impacted),
            "non_impacted_success_rate": round(float(non_impacted["type_success_bool"].mean()), 4) if len(non_impacted) else None,
        })
    return pd.DataFrame(rows)


def build_impact_by_league(df: pd.DataFrame) -> pd.DataFrame:
    table = _impact_group(df, "league", "impact_by_league")
    if table.empty:
        return table
    tier_rates: list[dict[str, Any]] = []
    for league, grp in df.groupby("league", dropna=False, sort=True):
        row = {
            "league": league,
            "a_tier_success_rate": _rate(grp[grp["market_tier"] == "A_TIER"]),
            "b_tier_success_rate": _rate(grp[grp["market_tier"] == "B_TIER"]),
            "hard_no_go_success_rate": _rate(grp[grp["market_tier"] == "HARD_NO_GO"]),
        }
        tier_rates.append(row)
    return table.merge(pd.DataFrame(tier_rates), on="league", how="left")


def build_defensive_integrity(df: pd.DataFrame) -> dict[str, Any]:
    impacted = df[df["phase_11_3_impacted"]]
    impacted_tiers = set(impacted["market_tier"].dropna().astype(str))
    return {
        "no_impacted_a_tier_rows": int((impacted["market_tier"] == "A_TIER").sum()) == 0,
        "no_impacted_b_tier_rows": int((impacted["market_tier"] == "B_TIER").sum()) == 0,
        "recommended_market_type_field_exists": "recommended_market_type" in df.columns,
        "recommended_market_subtype_field_exists": "recommended_market_subtype" in df.columns,
        "all_impacted_rows_defensive_tier_only": impacted_tiers.issubset({"HARD_NO_GO", "DOWNGRADE"}),
        "no_super_a_tier_present": not (df["market_tier"] == "SUPER_A_TIER").any(),
        "impacted_a_tier_rows": int((impacted["market_tier"] == "A_TIER").sum()),
        "impacted_b_tier_rows": int((impacted["market_tier"] == "B_TIER").sum()),
        "super_a_tier_rows": int((df["market_tier"] == "SUPER_A_TIER").sum()),
    }


def build_league_outliers(
    league_table: pd.DataFrame,
    *,
    min_outlier_sample: int,
    high_rate_threshold: float,
) -> pd.DataFrame:
    if league_table.empty:
        return pd.DataFrame()
    threshold = high_rate_threshold / 100.0
    rows: list[dict[str, Any]] = []
    for _, row in league_table.iterrows():
        reasons: list[str] = []
        impacted_rate = row.get("impacted_success_rate")
        hard_no_go_rate = row.get("hard_no_go_success_rate")
        impacted_n = int(row.get("impacted_n") or 0)
        if impacted_rate is not None and pd.notna(impacted_rate):
            if impacted_n >= min_outlier_sample and float(impacted_rate) >= threshold:
                reasons.append("impacted_hit_rate_high")
        if hard_no_go_rate is not None and pd.notna(hard_no_go_rate):
            if float(hard_no_go_rate) >= threshold:
                reasons.append("hard_no_go_rate_high")
        if reasons:
            item = row.to_dict()
            item["section"] = "league_outlier_watch"
            item["outlier_reason"] = " | ".join(reasons)
            rows.append(item)
    return pd.DataFrame(rows)


def phase11_4_recommendation(
    executive: dict[str, Any],
    integrity: dict[str, Any],
    outliers: pd.DataFrame,
    *,
    high_rate_threshold: float,
) -> str:
    impacted_n = int(executive.get("impacted_rows") or 0)
    impacted_rate = executive.get("impacted_success_rate")
    if impacted_n < 50:
        return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"
    if impacted_rate is not None and impacted_rate >= high_rate_threshold / 100.0:
        return "INVESTIGATE_RULE_TOO_BROAD"
    if not integrity["no_impacted_a_tier_rows"] or not integrity["no_impacted_b_tier_rows"]:
        return "INVESTIGATE_RULE_TOO_BROAD"
    if not outliers.empty:
        return "INVESTIGATE_LEAGUE_SPECIFIC_RELAXATION"
    if impacted_rate is not None and impacted_rate < 0.65:
        return "KEEP_PHASE_11_3_AS_IS"
    return "INCONCLUSIVE_MORE_REPLAY_REQUIRED"


def build_summary_table(
    df: pd.DataFrame,
    *,
    min_outlier_sample: int = 20,
    high_rate_threshold: float = 70.0,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], pd.DataFrame, str]:
    executive = build_executive_summary(df)
    by_flag = build_impact_by_flag(df)
    by_league = build_impact_by_league(df)
    by_type = _impact_group(df, "recommended_market_type", "impact_by_market_type")
    by_subtype = _impact_group(df, "recommended_market_subtype", "impact_by_market_subtype")
    integrity = build_defensive_integrity(df)
    outliers = build_league_outliers(
        by_league,
        min_outlier_sample=min_outlier_sample,
        high_rate_threshold=high_rate_threshold,
    )
    recommendation = phase11_4_recommendation(
        executive,
        integrity,
        outliers,
        high_rate_threshold=high_rate_threshold,
    )

    frames = [
        by_flag,
        by_league,
        by_type,
        by_subtype,
        pd.DataFrame([{"section": "defensive_integrity_checks", **integrity}]),
        outliers,
        pd.DataFrame([{"section": "phase_11_4_recommendation", "recommendation": recommendation}]),
    ]
    non_empty = [frame for frame in frames if not frame.empty]
    table = pd.concat(non_empty, ignore_index=True, sort=False) if non_empty else pd.DataFrame()
    return table, executive, integrity, outliers, recommendation


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        vals = []
        for col in cols:
            val = row.get(col)
            if isinstance(val, float):
                vals.append(f"{val * 100:.1f}%" if "rate" in col or "percentage" in col else f"{val:.4f}")
            else:
                vals.append("" if pd.isna(val) else str(val))
        lines.append("| " + " | ".join(vals) + " |")
    lines.append("")
    return lines


def build_markdown(
    df: pd.DataFrame,
    table: pd.DataFrame,
    executive: dict[str, Any],
    integrity: dict[str, Any],
    outliers: pd.DataFrame,
    recommendation: str,
) -> str:
    by_flag = table[table["section"] == "impact_by_phase_11_3_flag"] if "section" in table.columns else pd.DataFrame()
    by_league = table[table["section"] == "impact_by_league"] if "section" in table.columns else pd.DataFrame()
    by_type = table[table["section"] == "impact_by_market_type"] if "section" in table.columns else pd.DataFrame()
    by_subtype = table[table["section"] == "impact_by_market_subtype"] if "section" in table.columns else pd.DataFrame()

    lines = [
        "# Phase 11.4 Post-11.3 Multi-League Impact Audit",
        "",
        "Phase 11.4 is diagnostic only. No tier rules were changed.",
        "",
        "## A. Executive Summary",
        f"- Total evaluatable rows: {executive['total_evaluatable_rows']:,}",
        f"- Impacted rows: {executive['impacted_rows']:,}",
        f"- Impacted row percentage: {_rate_pct(executive['impacted_row_percentage'])}",
        f"- Impacted success rate: {_rate_pct(executive['impacted_success_rate'])}",
        f"- Non-impacted success rate: {_rate_pct(executive['non_impacted_success_rate'])}",
        f"- HARD_NO_GO success rate overall: {_rate_pct(executive['hard_no_go_success_rate'])}",
        f"- A_TIER success rate: {_rate_pct(executive['a_tier_success_rate'])}",
        f"- B_TIER success rate: {_rate_pct(executive['b_tier_success_rate'])}",
        "",
        "## B. Impact by Phase 11.3 Flag",
    ]
    lines += _markdown_table(by_flag, [
        "phase_11_3_flag", "n", "hits", "success_rate", "leagues",
        "top_recommended_market_subtypes",
    ])
    lines += ["## C. Impact by League"]
    lines += _markdown_table(by_league, [
        "league", "n", "impacted_n", "impacted_percentage",
        "impacted_success_rate", "non_impacted_success_rate",
        "a_tier_success_rate", "b_tier_success_rate", "hard_no_go_success_rate",
    ])
    lines += ["## D. Impact by Market Type"]
    lines += _markdown_table(by_type, [
        "recommended_market_type", "n", "impacted_n", "impacted_percentage",
        "impacted_success_rate", "non_impacted_success_rate",
    ])
    lines += ["## E. Impact by Market Subtype"]
    lines += _markdown_table(by_subtype, [
        "recommended_market_subtype", "n", "impacted_n", "impacted_percentage",
        "impacted_success_rate", "non_impacted_success_rate",
    ])
    lines += [
        "## F. Defensive Integrity Checks",
        f"- No impacted A_TIER rows: {integrity['no_impacted_a_tier_rows']}",
        f"- No impacted B_TIER rows: {integrity['no_impacted_b_tier_rows']}",
        f"- recommended_market_type unchanged field exists: {integrity['recommended_market_type_field_exists']}",
        f"- recommended_market_subtype unchanged field exists: {integrity['recommended_market_subtype_field_exists']}",
        f"- All impacted rows are HARD_NO_GO or defensive tier only: {integrity['all_impacted_rows_defensive_tier_only']}",
        f"- No SUPER_A_TIER present: {integrity['no_super_a_tier_present']}",
        "",
        "## G. League Outlier Watch",
    ]
    lines += _markdown_table(outliers, [
        "league", "impacted_n", "impacted_success_rate",
        "hard_no_go_success_rate", "outlier_reason",
    ])
    lines += [
        "## H. Phase 11.4 Recommendation",
        recommendation,
        "",
    ]
    return "\n".join(lines)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    min_outlier_sample: int = 20,
    high_rate_threshold: float = 70.0,
) -> tuple[pd.DataFrame, str]:
    df = load_evaluation_rows(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    table, executive, integrity, outliers, recommendation = build_summary_table(
        df,
        min_outlier_sample=min_outlier_sample,
        high_rate_threshold=high_rate_threshold,
    )
    markdown = build_markdown(df, table, executive, integrity, outliers, recommendation)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "season_replay"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--min-outlier-sample", type=int, default=20)
    parser.add_argument("--high-rate-threshold", type=float, default=70.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        min_outlier_sample=args.min_outlier_sample,
        high_rate_threshold=args.high_rate_threshold,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## H. Phase 11.4 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
