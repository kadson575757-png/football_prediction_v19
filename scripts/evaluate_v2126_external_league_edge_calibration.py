# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league  # noqa: E402
from football_prediction_v19.analysis.v2126_external_league_edge_calibration import (  # noqa: E402
    EXPECTED_FIXTURE_COUNTS,
    evaluate_external_league_edge_calibration,
)

DEFAULT_COMPETITIONS = ["La Liga", "Bundesliga", "Serie A"]
DEFAULT_SEASONS = ["2023/24", "2024/25", "2025/26"]
DEFAULT_OUTPUT_DIR = "outputs/v2126_external_league_edge_calibration"


def evaluate_v2126_external_league_edge_calibration(
    *,
    competitions: list[str] | tuple[str, ...] = tuple(DEFAULT_COMPETITIONS),
    seasons: list[str] | tuple[str, ...] = tuple(DEFAULT_SEASONS),
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    out = Path(output_dir)
    inputs: dict[tuple[str, str], pd.DataFrame] = {}
    load_info: dict[tuple[str, str], dict[str, object]] = {}
    canonical_competitions: list[str] = []
    for requested in competitions:
        mapping = resolve_source_league(requested, seasons[0] if seasons else "")
        canonical = mapping.canonical_competition
        canonical_competitions.append(canonical)
        for season in seasons:
            frame, info = load_or_build_competition_season(
                canonical,
                season,
                source_profile=source_profile,
                enable_network=enable_network,
                output_dir=out / "competition_runs" / _slug(canonical) / _slug(season),
            )
            inputs[(canonical, season)] = frame
            load_info[(canonical, season)] = info
    return evaluate_external_league_edge_calibration(
        inputs,
        competitions=canonical_competitions,
        seasons=list(seasons),
        load_info=load_info,
        expected_fixture_counts=EXPECTED_FIXTURE_COUNTS,
        output_dir=out,
    )


def load_or_build_competition_season(
    competition: str,
    season: str,
    *,
    source_profile: str,
    enable_network: bool,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    mapping = resolve_source_league(competition, season)
    if mapping.status == "UNSUPPORTED":
        return pd.DataFrame(), {"load_status": "UNSUPPORTED_COMPETITION", "load_reason": "; ".join(mapping.warnings), "fixtures_found": 0}
    for candidate in _local_candidates(competition, season, Path(output_dir)):
        if candidate.exists():
            try:
                frame = pd.read_csv(candidate, keep_default_na=False)
                return frame, {"load_status": "LOADED_LOCAL", "load_reason": str(candidate), "fixtures_found": len(frame)}
            except Exception as exc:  # noqa: BLE001
                local_error = f"{candidate}: {type(exc).__name__}: {exc}"
                break
    else:
        local_error = "no local competition-season artifact found"
    if not enable_network:
        return pd.DataFrame(), {"load_status": "MISSING_NETWORK_DISABLED", "load_reason": local_error, "fixtures_found": 0}
    try:
        return _build_with_existing_components(
            competition, season, source_profile=source_profile, output_dir=output_dir,
        )
    except Exception as exc:  # noqa: BLE001 - continue other competition-seasons.
        return pd.DataFrame(), {
            "load_status": "NETWORK_BUILD_FAILED",
            "load_reason": f"{type(exc).__name__}: {exc}",
            "fixtures_found": 0,
        }


def _build_with_existing_components(
    competition: str,
    season: str,
    *,
    source_profile: str,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    from football_prediction_v19.analysis.v21_season_fixture_catalog import build_v21_season_fixture_catalog
    from scripts.evaluate_v2111_pl_2025_26_analysis_quality import evaluate_pl_analysis_quality

    out = Path(output_dir)
    catalog = build_v21_season_fixture_catalog(
        competition,
        season,
        out / "fixture_load",
        source_profile=source_profile,
        enable_network=True,
        cache_only=False,
    )
    fixture_path = Path(str(catalog.get("season_fixture_catalog_csv_path", "")))
    fixtures = pd.read_csv(fixture_path, keep_default_na=False) if fixture_path.exists() else pd.DataFrame()
    if fixtures.empty:
        raise RuntimeError(f"fixture catalog unavailable: {catalog}")
    analysis_path, reused, executed = _run_resumable_analysis(
        fixtures,
        competition=competition,
        season=season,
        source_profile=source_profile,
        output_dir=out / "prematch_analysis",
    )
    quality = evaluate_pl_analysis_quality(
        analysis_path,
        results_frame=fixtures,
        source_profile=source_profile,
        enable_network=False,
        cache_only=True,
        output_dir=out / "quality",
    )
    quality_path = Path(str(quality["quality_rows_csv_path"]))
    frame = pd.read_csv(quality_path, keep_default_na=False)
    return frame, {
        "load_status": "BUILT_WITH_NETWORK",
        "load_reason": f"fixtures={len(fixtures)}; reused={reused}; executed={executed}; existing probability and as-of components reused",
        "fixtures_found": len(fixtures),
    }


def _run_resumable_analysis(
    fixtures: pd.DataFrame,
    *,
    competition: str,
    season: str,
    source_profile: str,
    output_dir: str | Path,
    max_workers: int = 12,
) -> tuple[Path, int, int]:
    from scripts.run_match_probability_analysis import run_match_probability_analysis

    out = Path(output_dir)
    match_root = out / "match_runs"
    match_root.mkdir(parents=True, exist_ok=True)
    indexed = [(int(index), row.to_dict()) for index, row in fixtures.reset_index(drop=True).iterrows()]
    results: dict[int, dict[str, object]] = {}
    pending = []
    reused = 0
    for index, fixture in indexed:
        snapshot = _read_snapshot(match_root / f"match_{index + 1}" / "winner_analysis.json", fixture, competition, season)
        if snapshot is None:
            pending.append((index, fixture))
        else:
            results[index] = snapshot
            reused += 1

    def run_one(index: int, fixture: dict[str, object]) -> tuple[int, dict[str, object]]:
        match_date = str(fixture.get("match_date", ""))
        parsed = pd.to_datetime(match_date, errors="coerce")
        as_of_date = (parsed - timedelta(days=1)).strftime("%Y-%m-%d") if pd.notna(parsed) else ""
        try:
            result = run_match_probability_analysis(
                competition=competition,
                season=season,
                home=fixture.get("home_team", ""),
                away=fixture.get("away_team", ""),
                match_date=match_date,
                as_of_date=as_of_date,
                source_profile=source_profile,
                cache_only=False,
                enable_network=True,
                output_dir=match_root / f"match_{index + 1}",
            )
            return index, dict(result)
        except Exception as exc:  # noqa: BLE001
            return index, {
                "probability_analysis_status": "FAILED",
                "failure_reason": f"{type(exc).__name__}: {exc}",
                "competition": competition, "season": season,
                "home_team": fixture.get("home_team", ""), "away_team": fixture.get("away_team", ""),
                "match_date": match_date, "as_of_date": as_of_date,
                "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
            }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_one, index, fixture) for index, fixture in pending]
        for future in as_completed(futures):
            index, result = future.result()
            results[index] = result

    rows = []
    for index, fixture in indexed:
        row = dict(results[index])
        row.update({
            "competition": competition, "season": season,
            "home_team": fixture.get("home_team", row.get("home_team", "")),
            "away_team": fixture.get("away_team", row.get("away_team", "")),
            "match_date": fixture.get("match_date", row.get("match_date", "")),
            "post_match_analysis": False,
            "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
        })
        rows.append(row)
    path = out / "resumable_analysis_rows.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path, reused, len(pending)


def _read_snapshot(path: Path, fixture: dict[str, object], competition: str, season: str) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    checks = (
        str(payload.get("competition", "")) == competition,
        str(payload.get("season", "")) == season,
        str(payload.get("home_team", "")) == str(fixture.get("home_team", "")),
        str(payload.get("away_team", "")) == str(fixture.get("away_team", "")),
        str(payload.get("top_probability_outcome", "")) in {"HOME", "DRAW", "AWAY"},
    )
    return payload if all(checks) else None


def _local_candidates(competition: str, season: str, run_dir: Path) -> list[Path]:
    competition_slug = _slug(competition)
    season_slug = _slug(season)
    return [
        run_dir / "quality" / "pl_2025_26_analysis_quality_rows.csv",
        Path(f"outputs/{competition_slug}_{season_slug}_analysis_quality/analysis_quality_rows.csv"),
        Path(f"outputs/{competition_slug}_{season_slug}_full_analysis/analysis_rows.csv"),
    ]


def _slug(value: str) -> str:
    return "_".join(str(value).strip().lower().replace("/", "_").replace("-", "_").split())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate fixed edge calibration on external leagues.")
    parser.add_argument("--competitions", nargs="+", default=DEFAULT_COMPETITIONS)
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true", help="Emit all validation artifacts (currently always enabled).")
    args = parser.parse_args(argv)
    result = evaluate_v2126_external_league_edge_calibration(
        competitions=args.competitions,
        seasons=args.seasons,
        source_profile=args.source_profile,
        enable_network=args.enable_network,
        output_dir=args.output_dir,
    )
    keys = [
        "v2126_external_league_edge_calibration_status", "competitions_requested",
        "competitions_evaluated", "competition_seasons_evaluated", "combined_evaluable_count",
        "combined_baseline_hit_rate", "combined_shadow_hit_rate", "combined_hit_rate_delta",
        "combined_baseline_brier_score", "combined_shadow_brier_score", "combined_brier_improvement",
        "positive_brier_competition_season_count", "negative_brier_competition_season_count",
        "positive_brier_competition_count", "total_adjustment_applied_count",
        "total_top_outcome_change_count", "total_newly_corrected_count", "total_newly_broken_count",
        "total_net_corrected_count", "post_match_rows_used_count", "external_validation_status",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
