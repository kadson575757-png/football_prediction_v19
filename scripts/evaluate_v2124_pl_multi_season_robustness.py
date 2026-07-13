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

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness  # noqa: E402

DEFAULT_SEASONS = ["2023/24", "2024/25", "2025/26"]
DEFAULT_OUTPUT_DIR = "outputs/v2124_pl_multi_season_robustness"


def evaluate_v2124_pl_multi_season_robustness(
    *,
    seasons: list[str] | tuple[str, ...] = tuple(DEFAULT_SEASONS),
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    out = Path(output_dir)
    season_inputs: dict[str, pd.DataFrame] = {}
    load_info: dict[str, dict[str, object]] = {}
    for season in seasons:
        frame, info = load_or_build_season_rows(
            season,
            source_profile=source_profile,
            enable_network=enable_network,
            output_dir=out / "season_runs" / _season_slug(season),
        )
        season_inputs[season] = frame
        load_info[season] = info
    return evaluate_pl_multi_season_robustness(
        season_inputs,
        seasons=list(seasons),
        season_load_info=load_info,
        output_dir=out,
    )


def load_or_build_season_rows(
    season: str,
    *,
    source_profile: str,
    enable_network: bool,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    for candidate in _local_season_candidates(season):
        if candidate.exists():
            try:
                return pd.read_csv(candidate, keep_default_na=False), {
                    "load_status": "LOADED_LOCAL",
                    "load_reason": str(candidate),
                }
            except Exception as exc:  # noqa: BLE001 - another candidate or network may still work.
                local_error = f"{candidate}: {type(exc).__name__}: {exc}"
                break
    else:
        local_error = "no local season artifact found"
    if not enable_network:
        return pd.DataFrame(), {
            "load_status": "MISSING_NETWORK_DISABLED",
            "load_reason": local_error,
        }
    try:
        return _build_season_with_existing_runners(
            season,
            source_profile=source_profile,
            output_dir=output_dir,
        )
    except Exception as exc:  # noqa: BLE001 - one failed season must not stop the others.
        return pd.DataFrame(), {
            "load_status": "NETWORK_BUILD_FAILED",
            "load_reason": f"{type(exc).__name__}: {exc}",
        }


def _build_season_with_existing_runners(
    season: str,
    *,
    source_profile: str,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    from scripts.evaluate_v2111_pl_2025_26_analysis_quality import evaluate_pl_analysis_quality
    from scripts.run_v2110_premier_league_2025_26_full_season_analysis import load_pl_fixtures

    out = Path(output_dir)
    fixtures, fixture_summary = load_pl_fixtures(
        "Premier League",
        season,
        out / "fixture_load",
        source_profile=source_profile,
        enable_network=True,
        cache_only=False,
    )
    if fixtures.empty:
        raise RuntimeError(f"fixture catalog empty: {fixture_summary}")
    analysis_path, reused_count, executed_count = _run_resumable_prematch_analysis(
        fixtures,
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
    path = Path(str(quality["quality_rows_csv_path"]))
    return pd.read_csv(path, keep_default_na=False), {
        "load_status": "BUILT_WITH_NETWORK",
        "load_reason": f"fixtures={len(fixtures)}; reused={reused_count}; executed={executed_count}; prematch runner and as-of guards reused",
    }


def _run_resumable_prematch_analysis(
    fixtures: pd.DataFrame,
    *,
    season: str,
    source_profile: str,
    output_dir: str | Path,
    max_workers: int = 8,
) -> tuple[Path, int, int]:
    from scripts.run_match_probability_analysis import run_match_probability_analysis

    out = Path(output_dir)
    match_root = out / "match_runs"
    match_root.mkdir(parents=True, exist_ok=True)
    indexed_fixtures = [(int(index), row.to_dict()) for index, row in fixtures.reset_index(drop=True).iterrows()]
    results: dict[int, dict[str, object]] = {}
    pending: list[tuple[int, dict[str, object]]] = []
    reused_count = 0
    for index, fixture in indexed_fixtures:
        snapshot_path = match_root / f"match_{index + 1}" / "winner_analysis.json"
        snapshot = _read_valid_snapshot(snapshot_path, fixture, season)
        if snapshot is not None:
            results[index] = snapshot
            reused_count += 1
        else:
            pending.append((index, fixture))

    def run_one(index: int, fixture: dict[str, object]) -> tuple[int, dict[str, object]]:
        match_date = str(fixture.get("match_date", ""))
        parsed = pd.to_datetime(match_date, errors="coerce")
        as_of_date = (parsed - timedelta(days=1)).strftime("%Y-%m-%d") if pd.notna(parsed) else ""
        try:
            result = run_match_probability_analysis(
                competition="Premier League",
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
        except Exception as exc:  # noqa: BLE001 - retain explicit per-row failure.
            return index, {
                "probability_analysis_status": "FAILED",
                "failure_reason": f"{type(exc).__name__}: {exc}",
                "competition": "Premier League", "season": season,
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
    for index, fixture in indexed_fixtures:
        row = dict(results[index])
        row.update({
            "competition": "Premier League", "season": season,
            "home_team": fixture.get("home_team", row.get("home_team", "")),
            "away_team": fixture.get("away_team", row.get("away_team", "")),
            "match_date": fixture.get("match_date", row.get("match_date", "")),
            "post_match_analysis": False,
            "leakage_warning": bool(row.get("leakage_warning", False)),
            "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
        })
        rows.append(row)
    analysis_path = out / "resumable_analysis_rows.csv"
    pd.DataFrame(rows).to_csv(analysis_path, index=False)
    return analysis_path, reused_count, len(pending)


def _read_valid_snapshot(path: Path, fixture: dict[str, object], season: str) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if str(payload.get("season", "")) != season:
        return None
    if str(payload.get("home_team", "")) != str(fixture.get("home_team", "")):
        return None
    if str(payload.get("away_team", "")) != str(fixture.get("away_team", "")):
        return None
    if str(payload.get("top_probability_outcome", "")) not in {"HOME", "DRAW", "AWAY"}:
        return None
    return payload


def _local_season_candidates(season: str) -> list[Path]:
    slug = _season_slug(season)
    return [
        Path(f"outputs/premier_league_{slug}_analysis_quality/pl_{slug}_analysis_quality_rows.csv"),
        Path(f"outputs/premier_league_{slug}_full_analysis/pl_{slug}_analysis_rows.csv"),
        Path(f"outputs/v27_prematch_evaluation_{slug}/v27_prematch_evaluation_rows.csv"),
    ]


def _season_slug(season: str) -> str:
    return season.replace("/", "_").replace("-", "_")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate unchanged Premier League probabilities across seasons.")
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true", help="Emit all evaluation artifacts (currently always enabled).")
    args = parser.parse_args(argv)
    result = evaluate_v2124_pl_multi_season_robustness(
        seasons=args.seasons,
        source_profile=args.source_profile,
        enable_network=args.enable_network,
        output_dir=args.output_dir,
    )
    keys = [
        "v2124_pl_multi_season_robustness_status", "seasons_requested", "seasons_evaluated",
        "combined_evaluable_count", "combined_hit_rate", "combined_brier_score",
        "mean_season_hit_rate", "minimum_season_hit_rate", "maximum_season_hit_rate",
        "season_hit_rate_standard_deviation", "most_common_error_type_across_seasons",
        "seasons_with_draw_never_top", "seasons_with_home_top_actual_draw_as_biggest_error",
        "stable_error_pattern", "stable_edge_pattern", "post_match_rows_used_count",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
