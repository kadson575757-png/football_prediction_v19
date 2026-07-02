# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


INDICATORS = {
    "dt": "DRAW_TENDENCY",
    "vr": "VENUE_RESULT_RATE",
    "gm": "GOAL_MARGIN_PROFILE",
    "vsb": "VENUE_SCORING_BALANCE",
}


def analyze_multi_indicator_shadow_mix(rows: str | Path, output_dir: str | Path = "outputs/v2104_multi_indicator_shadow_mix") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = _prepare(frame)
    summary = _summary(work)
    rows_path = out / "v2104_multi_indicator_shadow_mix_rows.csv"
    json_path = out / "v2104_multi_indicator_shadow_mix_summary.json"
    md_path = out / "v2104_multi_indicator_shadow_mix_report.md"
    work.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    for column in ["home_win_probability", "draw_probability", "away_win_probability"]:
        if column not in work.columns:
            work[column] = 0.0
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    work["base_shadow_top_outcome"] = [_top(h, d, a) for h, d, a in zip(work["home_win_probability"], work["draw_probability"], work["away_win_probability"], strict=False)]
    work["base_shadow_result"] = [_hit(top, result) for top, result in zip(work["base_shadow_top_outcome"], work.get("real_result", ""), strict=False)]
    for prefix in list(INDICATORS) + ["mix"]:
        for suffix in ["home_win_probability", "draw_probability", "away_win_probability"]:
            column = f"{prefix}_adjusted_{suffix}"
            if column not in work.columns:
                work[column] = work[suffix]
            work[column] = pd.to_numeric(work[column], errors="coerce").fillna(work[suffix])
        work[f"{prefix}_shadow_top_outcome"] = [_top(h, d, a) for h, d, a in zip(work[f"{prefix}_adjusted_home_win_probability"], work[f"{prefix}_adjusted_draw_probability"], work[f"{prefix}_adjusted_away_probability"], strict=False)]
        work[f"{prefix}_shadow_result"] = [_hit(top, result) for top, result in zip(work[f"{prefix}_shadow_top_outcome"], work.get("real_result", ""), strict=False)]
    return work


def _summary(work: pd.DataFrame) -> dict[str, object]:
    base_rate = _hit_rate(work["base_shadow_result"])
    indicator_summaries = {prefix: _indicator_summary(work, prefix) for prefix in INDICATORS}
    best_prefix = max(indicator_summaries, key=lambda key: indicator_summaries[key]["shadow_top_hit_rate"]) if indicator_summaries else ""
    best_rate = indicator_summaries[best_prefix]["shadow_top_hit_rate"] if best_prefix else 0.0
    mix_rate = _hit_rate(work["mix_shadow_result"])
    recommendation = _recommendation(base_rate, best_rate, mix_rate)
    summary = {
        "v2104_multi_indicator_shadow_mix_status": "READY",
        "rows_analyzed": int(len(work)),
        "base_top_probability_hit_rate": base_rate,
        "mix_indicator_count_average": round(float(pd.to_numeric(work.get("mix_indicator_count", pd.Series([0] * len(work))), errors="coerce").fillna(0).mean()), 4) if len(work) else 0.0,
        "mix_top_hit_rate": mix_rate,
        "mix_top_home_count": int(work["mix_shadow_top_outcome"].eq("HOME").sum()),
        "mix_top_draw_count": int(work["mix_shadow_top_outcome"].eq("DRAW").sum()),
        "mix_top_away_count": int(work["mix_shadow_top_outcome"].eq("AWAY").sum()),
        "mix_changed_top_outcome_count": int((work["mix_shadow_top_outcome"] != work["base_shadow_top_outcome"]).sum()),
        "best_single_indicator_name": INDICATORS.get(best_prefix, ""),
        "best_single_indicator_hit_rate": best_rate,
        "mix_vs_base_delta": round(mix_rate - base_rate, 4),
        "mix_vs_best_single_delta": round(mix_rate - best_rate, 4),
        "recommendation": recommendation,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for prefix, values in indicator_summaries.items():
        summary[f"{prefix}_shadow_top_hit_rate"] = values["shadow_top_hit_rate"]
        summary[f"{prefix}_summary"] = values
    return summary


def _indicator_summary(work: pd.DataFrame, prefix: str) -> dict[str, object]:
    applied = work.get(f"{prefix}_adjustment_applied", pd.Series([False] * len(work))).astype(str).str.lower().isin(["true", "1", "yes"])
    return {
        "indicator_name": INDICATORS[prefix],
        "adjustment_applied_count": int(applied.sum()),
        "shadow_top_hit_rate": _hit_rate(work[f"{prefix}_shadow_result"]),
        "hit_rate_adjusted_rows": _hit_rate(work.loc[applied, f"{prefix}_shadow_result"]),
        "hit_rate_unchanged_rows": _hit_rate(work.loc[~applied, f"{prefix}_shadow_result"]),
        "average_home_shift": _avg_shift(work, prefix, "home_win_probability"),
        "average_draw_shift": _avg_shift(work, prefix, "draw_probability"),
        "average_away_shift": _avg_shift(work, prefix, "away_win_probability"),
        "top_home_before_count": int(work["base_shadow_top_outcome"].eq("HOME").sum()),
        "top_draw_before_count": int(work["base_shadow_top_outcome"].eq("DRAW").sum()),
        "top_away_before_count": int(work["base_shadow_top_outcome"].eq("AWAY").sum()),
        "top_home_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("HOME").sum()),
        "top_draw_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("DRAW").sum()),
        "top_away_after_count": int(work[f"{prefix}_shadow_top_outcome"].eq("AWAY").sum()),
    }


def _recommendation(base_rate: float, best_rate: float, mix_rate: float) -> str:
    if mix_rate > base_rate and mix_rate >= best_rate:
        return "MULTI_INDICATOR_MIX_PROMISING"
    if best_rate > mix_rate and best_rate > base_rate:
        return "SINGLE_INDICATOR_STRONGER_THAN_MIX"
    if mix_rate <= base_rate and best_rate <= base_rate:
        return "SHADOW_INDICATORS_NOT_HELPFUL"
    return "KEEP_SHADOW_ONLY_MORE_DATA_NEEDED"


def _avg_shift(work: pd.DataFrame, prefix: str, base_col: str) -> float:
    adjusted_col = f"{prefix}_adjusted_{base_col}"
    return round(float((work[adjusted_col] - work[base_col]).mean()), 4) if len(work) else 0.0


def _hit_rate(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    known = values.astype(str).isin(["HIT", "MISS"])
    return round(float(values.astype(str).eq("HIT").sum() / known.sum()), 4) if int(known.sum()) else 0.0


def _hit(top: object, real: object) -> str:
    expected = {"HOME": "HOME_WIN", "DRAW": "DRAW", "AWAY": "AWAY_WIN"}.get(str(top))
    if not expected or str(real) == "RESULT_UNKNOWN" or str(real).strip() == "":
        return "RESULT_UNKNOWN"
    return "HIT" if str(real) == expected else "MISS"


def _top(home: object, draw: object, away: object) -> str:
    values = {"HOME": _num(home), "DRAW": _num(draw), "AWAY": _num(away)}
    return max(values.items(), key=lambda item: item[1])[0]


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.10.4 Multi Indicator Shadow Mix",
            "",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- base_top_probability_hit_rate: {summary['base_top_probability_hit_rate']}",
            f"- mix_top_hit_rate: {summary['mix_top_hit_rate']}",
            f"- best_single_indicator_name: {summary['best_single_indicator_name']}",
            f"- recommendation: {summary['recommendation']}",
            "",
            "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v2104_multi_indicator_shadow_mix")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_multi_indicator_shadow_mix(args.rows, args.output_dir)
    for key in [
        "v2104_multi_indicator_shadow_mix_status",
        "rows_analyzed",
        "base_top_probability_hit_rate",
        "dt_shadow_top_hit_rate",
        "vr_shadow_top_hit_rate",
        "gm_shadow_top_hit_rate",
        "vsb_shadow_top_hit_rate",
        "mix_top_hit_rate",
        "best_single_indicator_name",
        "best_single_indicator_hit_rate",
        "mix_vs_base_delta",
        "mix_vs_best_single_delta",
        "recommendation",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
