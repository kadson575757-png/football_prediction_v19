# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date  # noqa: E402
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league  # noqa: E402
from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog  # noqa: E402


DEFAULT_OUTPUT_DIR = "outputs/v2112_exact_scoreline_pattern_test"
OUTCOMES = ["HOME", "DRAW", "AWAY"]


def team_scoreline_pattern(row: pd.Series | dict[str, object], team: str) -> dict[str, object]:
    home = str(row.get("home_team", row.get("HomeTeam", "")))
    away = str(row.get("away_team", row.get("AwayTeam", "")))
    home_goals = _score(row.get("actual_home_goals", row.get("home_goals", row.get("FTHG", ""))))
    away_goals = _score(row.get("actual_away_goals", row.get("away_goals", row.get("FTAG", ""))))
    team_norm = normalize_team_or_league(team)
    if home_goals is None or away_goals is None:
        return {"pattern": "", "goals_for": "", "goals_against": ""}
    if normalize_team_or_league(home) == team_norm:
        gf, ga = home_goals, away_goals
    elif normalize_team_or_league(away) == team_norm:
        gf, ga = away_goals, home_goals
    else:
        return {"pattern": "", "goals_for": "", "goals_against": ""}
    result = "W" if gf > ga else ("L" if gf < ga else "D")
    return {"pattern": f"{result} {gf}:{ga}", "goals_for": gf, "goals_against": ga}


def actual_result(home_goals: object, away_goals: object) -> str:
    home = _score(home_goals)
    away = _score(away_goals)
    if home is None or away is None:
        return "UNKNOWN"
    if home > away:
        return "HOME"
    if home < away:
        return "AWAY"
    return "DRAW"


def analyze_exact_scoreline_patterns(fixtures: pd.DataFrame, *, competition: str = "Premier League", season: str = "2025/26", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    matches = _prepare_matches(fixtures, competition, season)
    rows = [_analyze_target_match(matches, idx) for idx in matches.index]
    rows_frame = pd.DataFrame(rows)
    summary = compute_summary(rows_frame, fixtures_loaded=len(matches), competition=competition, season=season, output_dir=out)
    ref_sources = reference_source_breakdown(rows_frame)
    patterns = pattern_breakdown(rows_frame)

    rows_path = out / "v2112_exact_scoreline_pattern_rows.csv"
    summary_path = out / "v2112_exact_scoreline_pattern_summary.json"
    report_path = out / "v2112_exact_scoreline_pattern_report.md"
    ref_path = out / "v2112_exact_scoreline_pattern_reference_sources.csv"
    patterns_path = out / "v2112_exact_scoreline_pattern_patterns.csv"
    rows_frame.to_csv(rows_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    report_path.write_text(render_report(summary), encoding="utf-8")
    ref_sources.to_csv(ref_path, index=False)
    patterns.to_csv(patterns_path, index=False)
    return {
        **summary,
        "rows_csv_path": str(rows_path.resolve()),
        "summary_json_path": str(summary_path.resolve()),
        "report_md_path": str(report_path.resolve()),
        "reference_sources_csv_path": str(ref_path.resolve()),
        "patterns_csv_path": str(patterns_path.resolve()),
    }


def _analyze_target_match(matches: pd.DataFrame, idx: int) -> dict[str, object]:
    target = matches.loc[idx]
    prior = matches[matches["match_date"] < target["match_date"]]
    home_last = _last_team_match(prior, target["home_team"])
    away_last = _last_team_match(prior, target["away_team"])
    home_pattern = team_scoreline_pattern(home_last, target["home_team"]) if home_last is not None else {"pattern": "", "goals_for": "", "goals_against": ""}
    away_pattern = team_scoreline_pattern(away_last, target["away_team"]) if away_last is not None else {"pattern": "", "goals_for": "", "goals_against": ""}
    home_own_count = _own_pattern_seen_count(prior, target["home_team"], home_last, str(home_pattern["pattern"]))
    away_own_count = _own_pattern_seen_count(prior, target["away_team"], away_last, str(away_pattern["pattern"]))
    refs = find_references(matches, idx, str(home_pattern["pattern"]), str(away_pattern["pattern"]))
    final = choose_final_reference(refs)
    actual = actual_result(target["actual_home_goals"], target["actual_away_goals"])
    hit = _reference_hit(final["top_outcome"], actual)
    row = {
        "competition": target["competition"],
        "season": target["season"],
        "match_date": target["match_date"],
        "home_team": target["home_team"],
        "away_team": target["away_team"],
        "actual_home_goals": target["actual_home_goals"],
        "actual_away_goals": target["actual_away_goals"],
        "actual_result": actual,
        "home_last_match_date": "" if home_last is None else home_last["match_date"],
        "home_last_pattern": home_pattern["pattern"],
        "home_last_goals_for": home_pattern["goals_for"],
        "home_last_goals_against": home_pattern["goals_against"],
        "away_last_match_date": "" if away_last is None else away_last["match_date"],
        "away_last_pattern": away_pattern["pattern"],
        "away_last_goals_for": away_pattern["goals_for"],
        "away_last_goals_against": away_pattern["goals_against"],
        "home_own_pattern_seen_before": home_own_count > 0,
        "home_own_pattern_seen_before_count": home_own_count,
        "away_own_pattern_seen_before": away_own_count > 0,
        "away_own_pattern_seen_before_count": away_own_count,
        "final_reference_source": final["source"],
        "final_reference_count": final["reference_count"],
        "final_reference_home_rate": final["home_rate"],
        "final_reference_draw_rate": final["draw_rate"],
        "final_reference_away_rate": final["away_rate"],
        "final_reference_top_outcome": final["top_outcome"],
        "reference_hit": hit,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for name, stats in refs.items():
        row.update(_prefixed_stats(name, stats))
    return row


def _own_pattern_seen_count(prior: pd.DataFrame, team: str, last_match: pd.Series | None, pattern: str) -> int:
    if last_match is None or not pattern:
        return 0
    earlier = prior[prior["match_date"] < last_match["match_date"]]
    return int(sum(team_scoreline_pattern(row, team)["pattern"] == pattern for _, row in earlier.iterrows()))


def find_references(matches: pd.DataFrame, target_idx: int, home_pattern: str, away_pattern: str) -> dict[str, dict[str, object]]:
    target = matches.loc[target_idx]
    candidates = matches[matches["match_date"] < target["match_date"]]
    exact_indices: list[int] = []
    home_indices: list[int] = []
    away_indices: list[int] = []
    for idx, row in candidates.iterrows():
        cand_prior = matches[matches["match_date"] < row["match_date"]]
        cand_home_last = _last_team_match(cand_prior, row["home_team"])
        cand_away_last = _last_team_match(cand_prior, row["away_team"])
        cand_home_pattern = team_scoreline_pattern(cand_home_last, row["home_team"])["pattern"] if cand_home_last is not None else ""
        cand_away_pattern = team_scoreline_pattern(cand_away_last, row["away_team"])["pattern"] if cand_away_last is not None else ""
        home_hit = bool(home_pattern and cand_home_pattern == home_pattern)
        away_hit = bool(away_pattern and cand_away_pattern == away_pattern)
        if home_hit:
            home_indices.append(idx)
        if away_hit:
            away_indices.append(idx)
        if home_hit and away_hit:
            exact_indices.append(idx)
    combined = sorted(set(home_indices) | set(away_indices))
    return {
        "exact_pair": _reference_stats(matches.loc[exact_indices] if exact_indices else matches.iloc[0:0]),
        "home_single": _reference_stats(matches.loc[home_indices] if home_indices else matches.iloc[0:0]),
        "away_single": _reference_stats(matches.loc[away_indices] if away_indices else matches.iloc[0:0]),
        "combined_single": _reference_stats(matches.loc[combined] if combined else matches.iloc[0:0]),
    }


def choose_final_reference(refs: dict[str, dict[str, object]]) -> dict[str, object]:
    for source, label in [("exact_pair", "EXACT_PAIR"), ("combined_single", "COMBINED_SINGLE"), ("home_single", "HOME_SINGLE"), ("away_single", "AWAY_SINGLE")]:
        stats = refs[source]
        if int(stats["reference_count"]) > 0:
            return {"source": label, **stats}
    return {"source": "NO_REFERENCE", **_reference_stats(pd.DataFrame())}


def compute_summary(rows: pd.DataFrame, *, fixtures_loaded: int, competition: str, season: str, output_dir: Path) -> dict[str, object]:
    evaluatable = rows[rows["reference_hit"].astype(str).str.lower().isin(["true", "false"])] if not rows.empty else pd.DataFrame()
    hit_count = int(evaluatable["reference_hit"].astype(str).str.lower().eq("true").sum()) if not evaluatable.empty else 0
    summary = {
        "v2112_exact_scoreline_pattern_test_status": "READY",
        "competition": competition,
        "season": season,
        "fixtures_loaded": int(fixtures_loaded),
        "fixtures_analyzed": int(len(rows)),
        "final_reference_evaluable_count": int(len(evaluatable)),
        "final_reference_hit_count": hit_count,
        "final_reference_miss_count": int(len(evaluatable) - hit_count),
        "final_reference_hit_rate": _rate(hit_count, len(evaluatable)),
        "evaluatable_reference_count": int(len(evaluatable)),
        "no_reference_count": int(rows["final_reference_top_outcome"].astype(str).eq("NO_REFERENCE").sum()) if not rows.empty else 0,
        "no_clear_top_count": int(rows["final_reference_top_outcome"].astype(str).eq("NO_CLEAR_TOP").sum()) if not rows.empty else 0,
        "reference_hit_count": hit_count,
        "reference_miss_count": int(len(evaluatable) - hit_count),
        "reference_hit_rate": _rate(hit_count, len(evaluatable)),
        "home_own_pattern_seen_before_rate": _rate(int(rows["home_own_pattern_seen_before"].astype(bool).sum()) if not rows.empty else 0, len(rows)),
        "away_own_pattern_seen_before_rate": _rate(int(rows["away_own_pattern_seen_before"].astype(bool).sum()) if not rows.empty else 0, len(rows)),
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    for source in ["exact_pair", "combined_single", "home_single", "away_single"]:
        source_eval = _source_evaluable_rows(rows, source)
        source_hits = int(source_eval[f"{source}_hit"].sum()) if not source_eval.empty else 0
        summary[f"{source}_reference_count"] = int((rows[f"{source}_reference_count"] > 0).sum()) if f"{source}_reference_count" in rows.columns else 0
        summary[f"{source}_evaluable_count"] = int(len(source_eval))
        summary[f"{source}_hit_count"] = source_hits
        summary[f"{source}_miss_count"] = int(len(source_eval) - source_hits)
        summary[f"{source}_hit_rate"] = _rate(source_hits, len(source_eval))
    return summary


def _source_evaluable_rows(rows: pd.DataFrame, source: str) -> pd.DataFrame:
    count_col = f"{source}_reference_count"
    top_col = f"{source}_top_outcome"
    if rows.empty or count_col not in rows.columns or top_col not in rows.columns or "actual_result" not in rows.columns:
        return pd.DataFrame()
    work = rows.copy()
    mask = (
        pd.to_numeric(work[count_col], errors="coerce").fillna(0).gt(0)
        & work[top_col].astype(str).isin(OUTCOMES)
        & work["actual_result"].astype(str).isin(OUTCOMES)
    )
    out = work[mask].copy()
    out[f"{source}_hit"] = out[top_col].astype(str).eq(out["actual_result"].astype(str))
    return out


def reference_source_breakdown(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for source, group in rows.groupby("final_reference_source", dropna=False) if not rows.empty else []:
        evaluatable = group[group["reference_hit"].astype(str).str.lower().isin(["true", "false"])]
        hits = int(evaluatable["reference_hit"].astype(str).str.lower().eq("true").sum()) if not evaluatable.empty else 0
        records.append({"final_reference_source": source, "n": len(group), "evaluatable": len(evaluatable), "hit_rate": _rate(hits, len(evaluatable))})
    return pd.DataFrame(records)


def pattern_breakdown(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for side in ["home", "away"]:
        column = f"{side}_last_pattern"
        if column in rows.columns:
            for pattern, group in rows.groupby(column, dropna=False):
                records.append({"side": side, "pattern": pattern, "n": len(group)})
    return pd.DataFrame(records)


def render_report(summary: dict[str, object]) -> str:
    return "\n".join([
        "# v2.11.2 Exact Previous Scoreline Pattern Test",
        "",
        f"- fixtures_loaded: {summary['fixtures_loaded']}",
        f"- fixtures_analyzed: {summary['fixtures_analyzed']}",
        f"- evaluatable_reference_count: {summary['evaluatable_reference_count']}",
        f"- reference_hit_rate: {summary['reference_hit_rate']}",
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def load_fixture_results(competition: str, season: str, output_dir: str | Path, *, source_profile: str, enable_network: bool, cache_only: bool) -> pd.DataFrame:
    catalog = build_v21_season_fixture_catalog(competition, season, Path(output_dir) / "fixture_catalog", source_profile=source_profile, enable_network=enable_network, cache_only=cache_only)
    path = Path(str(catalog.get("season_fixture_catalog_csv_path", "")))
    return pd.read_csv(path, keep_default_na=False) if path.exists() else pd.DataFrame()


def _prepare_matches(fixtures: pd.DataFrame, competition: str, season: str) -> pd.DataFrame:
    frame = fixtures.copy().rename(columns={"Date": "match_date", "HomeTeam": "home_team", "AwayTeam": "away_team", "FTHG": "actual_home_goals", "FTAG": "actual_away_goals", "home_goals": "actual_home_goals", "away_goals": "actual_away_goals"})
    for column in ["competition", "season", "match_date", "home_team", "away_team", "actual_home_goals", "actual_away_goals"]:
        if column not in frame.columns:
            frame[column] = ""
    frame["competition"] = frame["competition"].replace("", competition)
    frame["season"] = frame["season"].replace("", season)
    frame["match_date"] = frame["match_date"].map(_safe_date)
    frame = frame[frame["match_date"].astype(str).ne("")]
    return frame.sort_values(["match_date", "home_team", "away_team"]).reset_index(drop=True)


def _last_team_match(prior: pd.DataFrame, team: str) -> pd.Series | None:
    team_norm = normalize_team_or_league(team)
    rows = prior[(prior["home_team"].map(normalize_team_or_league).eq(team_norm)) | (prior["away_team"].map(normalize_team_or_league).eq(team_norm))]
    return None if rows.empty else rows.sort_values("match_date").iloc[-1]


def _reference_stats(rows: pd.DataFrame) -> dict[str, object]:
    if rows.empty:
        return {"reference_count": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "home_rate": 0.0, "draw_rate": 0.0, "away_rate": 0.0, "top_outcome": "NO_REFERENCE", "tie_breaker": "NONE"}
    outcomes = [actual_result(row["actual_home_goals"], row["actual_away_goals"]) for _, row in rows.iterrows()]
    count = len(outcomes)
    home = outcomes.count("HOME")
    draw = outcomes.count("DRAW")
    away = outcomes.count("AWAY")
    rates = {"HOME": _rate(home, count), "DRAW": _rate(draw, count), "AWAY": _rate(away, count)}
    best_rate = max(rates.values())
    leaders = [key for key, value in rates.items() if value == best_rate]
    top = leaders[0] if len(leaders) == 1 else "NO_CLEAR_TOP"
    return {"reference_count": count, "home_wins": home, "draws": draw, "away_wins": away, "home_rate": rates["HOME"], "draw_rate": rates["DRAW"], "away_rate": rates["AWAY"], "top_outcome": top, "tie_breaker": "NONE"}


def _prefixed_stats(prefix: str, stats: dict[str, object]) -> dict[str, object]:
    return {f"{prefix}_{key}": value for key, value in stats.items()}


def _reference_hit(top_outcome: object, actual: str) -> object:
    top = str(top_outcome)
    if top not in OUTCOMES or actual not in OUTCOMES:
        return ""
    return top == actual


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return str(value).strip()


def _score(value: object) -> int | None:
    try:
        if str(value).strip() == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="Premier League")
    parser.add_argument("--season", default="2025/26")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--team", default="")
    parser.add_argument("--from-date", default="")
    parser.add_argument("--to-date", default="")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    fixtures = load_fixture_results(args.competition, args.season, args.output_dir, source_profile=args.source_profile, enable_network=args.enable_network, cache_only=args.cache_only)
    fixtures = _prepare_matches(fixtures, args.competition, args.season)
    if args.team:
        team = normalize_team_or_league(args.team)
        fixtures = fixtures[(fixtures["home_team"].map(normalize_team_or_league).eq(team)) | (fixtures["away_team"].map(normalize_team_or_league).eq(team))]
    if args.from_date:
        fixtures = fixtures[fixtures["match_date"] >= args.from_date]
    if args.to_date:
        fixtures = fixtures[fixtures["match_date"] <= args.to_date]
    if args.limit:
        fixtures = fixtures.head(args.limit)
    result = analyze_exact_scoreline_patterns(fixtures, competition=args.competition, season=args.season, output_dir=args.output_dir)
    for key in [
        "v2112_exact_scoreline_pattern_test_status", "competition", "season", "fixtures_loaded", "fixtures_analyzed",
        "final_reference_evaluable_count", "final_reference_hit_count", "final_reference_miss_count",
        "final_reference_hit_rate", "exact_pair_evaluable_count", "exact_pair_hit_rate",
        "combined_single_evaluable_count", "combined_single_hit_rate", "home_single_evaluable_count",
        "home_single_hit_rate", "away_single_evaluable_count", "away_single_hit_rate",
        "home_own_pattern_seen_before_rate", "away_own_pattern_seen_before_rate", "output_dir",
        "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
