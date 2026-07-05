# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league  # noqa: E402
from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog  # noqa: E402
from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date  # noqa: E402


OUTPUT_DIR = "outputs/premier_league_2025_26_analysis_quality"
INDICATOR_PREFIXES = ["ppg", "gd", "gf", "ga", "dt", "vr", "gm", "vsb", "csfts", "rdc", "tsg", "cbl", "oarf", "rgt", "vrm", "rvc", "rsp", "srp", "h2hc", "lzp", "cop", "sbp", "rar", "hre", "adm", "vsd", "dpc", "sca"]
CALIBRATION_BUCKETS = [(0.30, 0.35), (0.35, 0.40), (0.40, 0.45), (0.45, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, None)]


def evaluate_pl_analysis_quality(
    analysis_rows: str | Path | pd.DataFrame,
    *,
    results_frame: pd.DataFrame | None = None,
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    analysis = _read_frame(analysis_rows)
    if results_frame is None:
        results_frame = load_result_rows_from_catalog(analysis, out, source_profile=source_profile, enable_network=enable_network, cache_only=cache_only)
    rows = attach_results(analysis, results_frame)
    summary = compute_quality_summary(rows)
    confusion = compute_confusion_matrix(rows)
    calibration = compute_calibration_buckets(rows)
    bands = compute_quality_band_breakdown(rows)
    indicator_quality = compute_indicator_quality_vs_hit_rate(rows)

    rows_path = out / "pl_2025_26_analysis_quality_rows.csv"
    summary_path = out / "pl_2025_26_analysis_quality_summary.json"
    report_path = out / "pl_2025_26_analysis_quality_report.md"
    confusion_path = out / "pl_2025_26_confusion_matrix.csv"
    calibration_path = out / "pl_2025_26_calibration_buckets.csv"
    bands_path = out / "pl_2025_26_quality_band_breakdown.csv"
    indicator_path = out / "pl_2025_26_indicator_quality_vs_hit_rate.csv"

    rows.to_csv(rows_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    report_path.write_text(render_quality_report(summary), encoding="utf-8")
    confusion.to_csv(confusion_path, index=False)
    calibration.to_csv(calibration_path, index=False)
    bands.to_csv(bands_path, index=False)
    indicator_quality.to_csv(indicator_path, index=False)

    return {
        **summary,
        "quality_rows_csv_path": str(rows_path.resolve()),
        "quality_summary_json_path": str(summary_path.resolve()),
        "quality_report_md_path": str(report_path.resolve()),
        "confusion_matrix_csv_path": str(confusion_path.resolve()),
        "calibration_buckets_csv_path": str(calibration_path.resolve()),
        "quality_band_breakdown_csv_path": str(bands_path.resolve()),
        "indicator_quality_vs_hit_rate_csv_path": str(indicator_path.resolve()),
    }


def load_result_rows_from_catalog(
    analysis: pd.DataFrame,
    output_dir: str | Path,
    *,
    source_profile: str,
    enable_network: bool,
    cache_only: bool,
) -> pd.DataFrame:
    competition = str(analysis.get("competition", pd.Series(["Premier League"])).iloc[0] if len(analysis) else "Premier League")
    season = str(analysis.get("season", pd.Series(["2025/26"])).iloc[0] if len(analysis) else "2025/26")
    catalog = build_v21_season_fixture_catalog(
        competition=competition,
        season=season,
        output_dir=Path(output_dir) / "result_catalog",
        source_profile=source_profile,
        enable_network=enable_network,
        cache_only=cache_only,
    )
    path = Path(str(catalog.get("season_fixture_catalog_csv_path", "")))
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, keep_default_na=False)
    return frame.rename(columns={"home_goals": "actual_home_goals", "away_goals": "actual_away_goals"})


def attach_results(analysis: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    rows = analysis.copy()
    for column in ["actual_home_goals", "actual_away_goals", "actual_result", "top_probability_hit"]:
        if column not in rows.columns:
            rows[column] = ""
    result_lookup = _result_lookup(results)
    actual_home: list[object] = []
    actual_away: list[object] = []
    actual_result: list[str] = []
    top_hit: list[object] = []
    for _, row in rows.iterrows():
        key = _match_key(row)
        found = result_lookup.get(key)
        home_goals = "" if found is None else found.get("actual_home_goals", found.get("home_goals", found.get("FTHG", "")))
        away_goals = "" if found is None else found.get("actual_away_goals", found.get("away_goals", found.get("FTAG", "")))
        result = _actual_result(home_goals, away_goals, "" if found is None else found.get("actual_result", found.get("FTR", "")))
        actual_home.append(home_goals)
        actual_away.append(away_goals)
        actual_result.append(result)
        top_hit.append(_top_probability_hit(row.get("top_probability_outcome", ""), result))
    rows["actual_home_goals"] = actual_home
    rows["actual_away_goals"] = actual_away
    rows["actual_result"] = actual_result
    rows["top_probability_hit"] = top_hit
    return rows


def compute_quality_summary(rows: pd.DataFrame) -> dict[str, object]:
    known = rows["actual_result"].astype(str).isin(["HOME", "DRAW", "AWAY"]) if "actual_result" in rows.columns else pd.Series([False] * len(rows))
    evaluatable = rows[known & rows.get("top_probability_outcome", pd.Series([""] * len(rows))).astype(str).isin(["HOME", "DRAW", "AWAY"])]
    hits = evaluatable["top_probability_hit"].astype(str).str.lower().eq("true") if not evaluatable.empty else pd.Series(dtype=bool)
    summary = {
        "v2111_pl_analysis_quality_status": "READY",
        "rows_loaded": int(len(rows)),
        "result_known_count": int(known.sum()),
        "result_unknown_count": int((~known).sum()),
        "evaluatable_count": int(len(evaluatable)),
        "top_probability_hit_count": int(hits.sum()),
        "top_probability_miss_count": int(len(evaluatable) - hits.sum()),
        "top_probability_hit_rate": _rate(int(hits.sum()), len(evaluatable)),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for outcome in ["HOME", "DRAW", "AWAY"]:
        pred = evaluatable[evaluatable["top_probability_outcome"].astype(str).eq(outcome)]
        pred_hits = pred["top_probability_hit"].astype(str).str.lower().eq("true") if not pred.empty else pd.Series(dtype=bool)
        summary[f"{outcome.lower()}_prediction_count"] = int(len(pred))
        summary[f"{outcome.lower()}_prediction_hit_count"] = int(pred_hits.sum())
        summary[f"{outcome.lower()}_prediction_hit_rate"] = _rate(int(pred_hits.sum()), len(pred))
        summary[f"actual_{outcome.lower()}_count"] = int(rows["actual_result"].astype(str).eq(outcome).sum()) if "actual_result" in rows.columns else 0
    summary.update(_calibration_summary(evaluatable))
    return summary


def compute_quality_band_breakdown(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for column in ["probability_edge_band", "uncertainty_level", "data_quality_band", "source_quality_band"]:
        if column not in rows.columns:
            continue
        for value, group in rows.groupby(column, dropna=False):
            evaluatable = group[group["top_probability_hit"].astype(str).str.lower().isin(["true", "false"])]
            hit_count = int(evaluatable["top_probability_hit"].astype(str).str.lower().eq("true").sum())
            records.append({"breakdown_type": column, "band": value, "n": int(len(evaluatable)), "hit_count": hit_count, "hit_rate": _rate(hit_count, len(evaluatable))})
    return pd.DataFrame(records)


def compute_confusion_matrix(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for predicted in ["HOME", "DRAW", "AWAY"]:
        subset = rows[rows.get("top_probability_outcome", pd.Series([""] * len(rows))).astype(str).eq(predicted)]
        record = {"predicted": predicted}
        for actual in ["HOME", "DRAW", "AWAY"]:
            record[f"actual_{actual.lower()}"] = int(subset.get("actual_result", pd.Series(dtype=str)).astype(str).eq(actual).sum())
        record["total"] = sum(record[f"actual_{actual.lower()}"] for actual in ["HOME", "DRAW", "AWAY"])
        records.append(record)
    return pd.DataFrame(records)


def compute_calibration_buckets(rows: pd.DataFrame) -> pd.DataFrame:
    work = rows.copy()
    if work.empty:
        return pd.DataFrame(columns=["bucket", "n", "average_top_probability", "hit_rate", "calibration_error"])
    work["top_probability"] = work.apply(_top_probability, axis=1)
    work = work[work["top_probability_hit"].astype(str).str.lower().isin(["true", "false"])]
    records = []
    for low, high in CALIBRATION_BUCKETS:
        label = f"{low:.2f}-{high:.2f}" if high is not None else f"{low:.2f}+"
        subset = work[work["top_probability"].ge(low) & (work["top_probability"].lt(high) if high is not None else True)]
        hit_count = int(subset["top_probability_hit"].astype(str).str.lower().eq("true").sum()) if not subset.empty else 0
        avg_prob = round(float(subset["top_probability"].mean()), 4) if not subset.empty else 0.0
        hit_rate = _rate(hit_count, len(subset))
        records.append({"bucket": label, "n": int(len(subset)), "average_top_probability": avg_prob, "hit_rate": hit_rate, "calibration_error": round(abs(avg_prob - hit_rate), 4)})
    return pd.DataFrame(records)


def compute_indicator_quality_vs_hit_rate(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for prefix in INDICATOR_PREFIXES:
        quality_col = _quality_col(prefix)
        applied_col = f"{prefix}_adjustment_applied"
        qualities = rows[quality_col].astype(str).str.upper() if quality_col in rows.columns else pd.Series(["MISSING"] * len(rows))
        applied = rows[applied_col].astype(str).str.lower().isin(["true", "1", "yes"]) if applied_col in rows.columns else pd.Series([False] * len(rows))
        record = {
            "prefix": prefix,
            "full_quality_count": int(qualities.eq("FULL").sum()),
            "partial_quality_count": int(qualities.eq("PARTIAL").sum()),
            "low_quality_count": int(qualities.eq("LOW").sum()),
            "adjustment_applied_count": int(applied.sum()),
            "hit_rate_when_full": _hit_rate(rows[qualities.eq("FULL")]),
            "hit_rate_when_partial": _hit_rate(rows[qualities.eq("PARTIAL")]),
            "hit_rate_when_low": _hit_rate(rows[qualities.eq("LOW")]),
            "hit_rate_when_adjustment_applied": _hit_rate(rows[applied]),
            "hit_rate_when_no_adjustment": _hit_rate(rows[~applied]),
        }
        records.append(record)
    return pd.DataFrame(records)


def render_quality_report(summary: dict[str, object]) -> str:
    return "\n".join([
        "# Premier League 2025/26 Analysis Quality Evaluation",
        "",
        "## Summary",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- result_known_count: {summary['result_known_count']}",
        f"- evaluatable_count: {summary['evaluatable_count']}",
        f"- top_probability_hit_rate: {summary['top_probability_hit_rate']}",
        f"- multiclass_brier_score: {summary['multiclass_brier_score']}",
        f"- expected_calibration_error: {summary['expected_calibration_error']}",
        "",
        "## Safety",
        "- automatic_betting_enabled=false",
        "- staking_logic_enabled=false",
        "- roi_logic_enabled=false",
        "",
        "Evaluation only. Results are joined after prematch analysis rows have already been produced.",
    ])


def _calibration_summary(evaluatable: pd.DataFrame) -> dict[str, object]:
    if evaluatable.empty:
        return {"multiclass_brier_score": 0.0, "average_top_probability": 0.0, "empirical_top_hit_rate": 0.0, "calibration_gap": 0.0, "expected_calibration_error": 0.0, "max_calibration_error": 0.0}
    top_probs = evaluatable.apply(_top_probability, axis=1)
    hit_rate = _rate(int(evaluatable["top_probability_hit"].astype(str).str.lower().eq("true").sum()), len(evaluatable))
    calibration = compute_calibration_buckets(evaluatable)
    weighted_error = 0.0
    if not calibration.empty and len(evaluatable):
        weighted_error = float((calibration["n"] * calibration["calibration_error"]).sum() / len(evaluatable))
    return {
        "multiclass_brier_score": _brier_score(evaluatable),
        "average_top_probability": round(float(top_probs.mean()), 4),
        "empirical_top_hit_rate": hit_rate,
        "calibration_gap": round(float(top_probs.mean()) - hit_rate, 4),
        "expected_calibration_error": round(weighted_error, 4),
        "max_calibration_error": round(float(calibration["calibration_error"].max()), 4) if not calibration.empty else 0.0,
    }


def _brier_score(rows: pd.DataFrame) -> float:
    if rows.empty:
        return 0.0
    total = 0.0
    for _, row in rows.iterrows():
        actual = str(row.get("actual_result", ""))
        total += (_num(row.get("home_win_probability")) - (1.0 if actual == "HOME" else 0.0)) ** 2
        total += (_num(row.get("draw_probability")) - (1.0 if actual == "DRAW" else 0.0)) ** 2
        total += (_num(row.get("away_win_probability")) - (1.0 if actual == "AWAY" else 0.0)) ** 2
    return round(total / len(rows), 4)


def _result_lookup(results: pd.DataFrame) -> dict[tuple[str, str, str, str, str], dict[str, object]]:
    lookup: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    if results is None or results.empty:
        return lookup
    for _, row in results.iterrows():
        lookup[_match_key(row)] = row.to_dict()
    return lookup


def _match_key(row: pd.Series | dict[str, object]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("competition", "")),
        str(row.get("season", "")),
        _safe_date(row.get("match_date", row.get("Date", ""))),
        normalize_team_or_league(str(row.get("home_team", row.get("HomeTeam", "")))),
        normalize_team_or_league(str(row.get("away_team", row.get("AwayTeam", "")))),
    )


def _actual_result(home_goals: object, away_goals: object, raw_result: object = "") -> str:
    text = str(raw_result).strip().upper()
    if text in {"HOME", "H", "HOME_WIN"}:
        return "HOME"
    if text in {"DRAW", "D"}:
        return "DRAW"
    if text in {"AWAY", "A", "AWAY_WIN"}:
        return "AWAY"
    home = _maybe_int(home_goals)
    away = _maybe_int(away_goals)
    if home is None or away is None:
        return "UNKNOWN"
    if home > away:
        return "HOME"
    if home < away:
        return "AWAY"
    return "DRAW"


def _top_probability_hit(predicted: object, actual: str) -> object:
    pred = str(predicted).strip().upper().replace("_WIN", "")
    if actual == "UNKNOWN" or pred not in {"HOME", "DRAW", "AWAY"}:
        return ""
    return pred == actual


def _top_probability(row: pd.Series) -> float:
    outcome = str(row.get("top_probability_outcome", "")).strip().upper().replace("_WIN", "")
    column = {"HOME": "home_win_probability", "DRAW": "draw_probability", "AWAY": "away_win_probability"}.get(outcome)
    if column:
        return _num(row.get(column))
    return max(_num(row.get("home_win_probability")), _num(row.get("draw_probability")), _num(row.get("away_win_probability")))


def _quality_col(prefix: str) -> str:
    return {"gd": "goal_difference_indicator_quality", "gf": "goals_for_indicator_quality", "ga": "goals_against_indicator_quality"}.get(prefix, f"{prefix}_indicator_quality")


def _hit_rate(rows: pd.DataFrame) -> float:
    if rows.empty or "top_probability_hit" not in rows.columns:
        return 0.0
    known = rows["top_probability_hit"].astype(str).str.lower().isin(["true", "false"])
    hits = rows.loc[known, "top_probability_hit"].astype(str).str.lower().eq("true")
    return _rate(int(hits.sum()), int(known.sum()))


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _maybe_int(value: object) -> int | None:
    try:
        if str(value).strip() == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return str(value).strip()


def _read_frame(value: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return pd.read_csv(value, keep_default_na=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-rows", required=True)
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate_pl_analysis_quality(args.analysis_rows, source_profile=args.source_profile, enable_network=args.enable_network, cache_only=args.cache_only, output_dir=args.output_dir)
    for key in [
        "v2111_pl_analysis_quality_status", "rows_loaded", "result_known_count", "result_unknown_count",
        "evaluatable_count", "top_probability_hit_count", "top_probability_miss_count",
        "top_probability_hit_rate", "home_prediction_hit_rate", "draw_prediction_hit_rate",
        "away_prediction_hit_rate", "multiclass_brier_score", "average_top_probability",
        "empirical_top_hit_rate", "calibration_gap", "expected_calibration_error",
        "output_dir", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]:
        value = result.get(key, args.output_dir if key == "output_dir" else "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
