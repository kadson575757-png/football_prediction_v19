# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league, resolve_league_support
from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog


def build_real_season_corpus(
    competition: str,
    season: str,
    output_dir: str | Path,
    *,
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    cache_dir: str | Path | None = None,
    mock_data_dir: str | Path | None = None,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    catalog_result = build_v21_season_fixture_catalog(
        competition,
        season,
        out / "catalog_build",
        source_profile=source_profile,
        enable_network=enable_network,
        cache_only=cache_only,
        cache_dir=cache_dir,
        mock_data_dir=mock_data_dir,
    )
    catalog = pd.read_csv(catalog_result["season_fixture_catalog_csv_path"], keep_default_na=False)
    support = resolve_league_support(competition)
    corpus = _catalog_to_corpus(catalog, competition, season, support.prediction_tier)
    paths = _write_outputs(out, corpus, catalog_result, support.to_dict())
    status = "READY" if not corpus.empty else ("SOURCE_LIMITED" if catalog_result.get("football_data_status") else "EMPTY")
    return {
        "v22_real_season_corpus_status": status,
        "competition": competition,
        "season": season,
        "matches_total": int(len(corpus)),
        "completed_matches": int(corpus["match_completed"].sum()) if not corpus.empty else 0,
        "backtestable_matches": int(corpus["can_backtest"].sum()) if not corpus.empty else 0,
        "football_data_status": catalog_result.get("football_data_status"),
        "understat_status": catalog_result.get("understat_status"),
        "cache_used": bool(catalog_result.get("cache_used")),
        "network_calls_enabled": bool(enable_network and not cache_only),
        **paths,
    }


def _catalog_to_corpus(catalog: pd.DataFrame, competition: str, season: str, prediction_tier: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in catalog.iterrows():
        home_goals = _num_or_blank(row.get("home_goals", ""))
        away_goals = _num_or_blank(row.get("away_goals", ""))
        result = _result_1x2(home_goals, away_goals, row.get("actual_result", ""))
        completed = result != ""
        xg_available = bool(row.get("xg_available", False))
        can_backtest = completed and bool(row.get("football_data_available", False))
        rows.append(
            {
                "canonical_match_id": row.get("canonical_match_id", ""),
                "competition": competition,
                "season": season,
                "match_date": row.get("match_date", ""),
                "home_team": row.get("home_team", ""),
                "away_team": row.get("away_team", ""),
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result_1x2": result,
                "result_available": completed,
                "match_completed": completed,
                "football_data_available": bool(row.get("football_data_available", False)),
                "understat_available": bool(row.get("understat_available", False)),
                "xg_available": xg_available,
                "home_xg": "",
                "away_xg": "",
                "home_xga": "",
                "away_xga": "",
                "odds_available": bool(row.get("odds_available", False)),
                "prediction_tier": row.get("prediction_tier", prediction_tier),
                "source_quality_band": "MEDIUM" if can_backtest and xg_available else ("LOW" if can_backtest else "BLOCKED"),
                "can_backtest": can_backtest,
                "cannot_backtest_reason": "" if can_backtest else "result unavailable or football-data missing",
                "home_team_normalized": normalize_team_or_league(row.get("home_team", "")),
                "away_team_normalized": normalize_team_or_league(row.get("away_team", "")),
            }
        )
    return pd.DataFrame(rows, columns=_CORPUS_COLUMNS)


def _write_outputs(out: Path, corpus: pd.DataFrame, catalog_result: dict[str, object], support: dict[str, object]) -> dict[str, str]:
    csv_path = out / "real_season_corpus.csv"
    json_path = out / "real_season_corpus.json"
    report_path = out / "real_season_corpus_report.md"
    coverage_path = out / "source_coverage_summary.csv"
    alias_path = out / "team_alias_map_used.csv"
    unmatched_path = out / "unmatched_source_rows.csv"
    manifest_path = out / "corpus_build_manifest.json"
    corpus.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(corpus.to_dict(orient="records"), indent=2), encoding="utf-8")
    coverage = _coverage(corpus)
    pd.DataFrame([coverage]).to_csv(coverage_path, index=False)
    corpus[["home_team", "home_team_normalized"]].drop_duplicates().rename(columns={"home_team": "source_team", "home_team_normalized": "canonical_team"}).to_csv(alias_path, index=False)
    pd.DataFrame(columns=["source", "reason", "row"]).to_csv(unmatched_path, index=False)
    manifest = {"support": support, "catalog": catalog_result, "coverage": coverage}
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    report_path.write_text(
        "# v2.2 Real Season Corpus\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in coverage.items())
        + "\n\nNo automatic betting. No stake. No ROI.\n",
        encoding="utf-8",
    )
    return {
        "real_season_corpus_csv_path": str(csv_path.resolve()),
        "real_season_corpus_json_path": str(json_path.resolve()),
        "real_season_corpus_report_path": str(report_path.resolve()),
        "source_coverage_summary_path": str(coverage_path.resolve()),
        "team_alias_map_used_path": str(alias_path.resolve()),
        "unmatched_source_rows_path": str(unmatched_path.resolve()),
        "corpus_build_manifest_path": str(manifest_path.resolve()),
    }


def _coverage(corpus: pd.DataFrame) -> dict[str, object]:
    total = len(corpus)
    return {
        "matches_total": total,
        "completed_matches": int(corpus["match_completed"].sum()) if total else 0,
        "backtestable_matches": int(corpus["can_backtest"].sum()) if total else 0,
        "football_data_rows": int(corpus["football_data_available"].sum()) if total else 0,
        "understat_rows": int(corpus["understat_available"].sum()) if total else 0,
        "xg_join_rate": round(float(corpus["xg_available"].mean()), 4) if total else 0.0,
        "result_available_rate": round(float(corpus["result_available"].mean()), 4) if total else 0.0,
        "backtestable_rate": round(float(corpus["can_backtest"].mean()), 4) if total else 0.0,
    }


def _num_or_blank(value: object) -> int | str:
    try:
        if str(value).strip() == "":
            return ""
        return int(float(value))
    except (TypeError, ValueError):
        return ""


def _result_1x2(home_goals: object, away_goals: object, existing: object = "") -> str:
    if str(existing).strip() in {"H", "D", "A"}:
        return str(existing).strip()
    if home_goals == "" or away_goals == "":
        return ""
    if int(home_goals) > int(away_goals):
        return "H"
    if int(home_goals) < int(away_goals):
        return "A"
    return "D"


_CORPUS_COLUMNS = [
    "canonical_match_id", "competition", "season", "match_date", "home_team", "away_team",
    "home_goals", "away_goals", "result_1x2", "result_available", "match_completed",
    "football_data_available", "understat_available", "xg_available", "home_xg", "away_xg",
    "home_xga", "away_xga", "odds_available", "prediction_tier", "source_quality_band",
    "can_backtest", "cannot_backtest_reason", "home_team_normalized", "away_team_normalized",
]
