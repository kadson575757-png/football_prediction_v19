# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus  # noqa: E402


DEFAULT_LEAGUES = ["Premier League", "Bundesliga", "Serie A", "La Liga", "Ligue 1"]


def warm_v22_multileague_cache(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs.get("output_dir") or "outputs/corpus/v22/cache_warm"))
    out.mkdir(parents=True, exist_ok=True)
    competitions = [c.strip() for c in str(kwargs.get("competitions") or ",".join(DEFAULT_LEAGUES)).split(",") if c.strip()]
    rows = []
    for comp in competitions:
        result = build_real_season_corpus(comp, str(kwargs["season"]), out / comp.replace(" ", "_"), source_profile=str(kwargs.get("source_profile", "")), enable_network=bool(kwargs.get("enable_network")), cache_only=bool(kwargs.get("cache_only")), mock_data_dir=kwargs.get("mock_data_dir") or None)
        rows.append({"competition": comp, **{k: result.get(k) for k in ["v22_real_season_corpus_status", "matches_total", "backtestable_matches", "football_data_status", "understat_status"]}})
    frame = pd.DataFrame(rows)
    status = "READY" if not frame.empty and frame["backtestable_matches"].sum() > 0 else "FAILED"
    result = {
        "v22_cache_warm_status": status,
        "leagues_requested": len(competitions),
        "leagues_ready": int(frame["v22_real_season_corpus_status"].eq("READY").sum()) if not frame.empty else 0,
        "leagues_partial": int(frame["v22_real_season_corpus_status"].eq("SOURCE_LIMITED").sum()) if not frame.empty else 0,
        "leagues_failed": int(frame["v22_real_season_corpus_status"].eq("EMPTY").sum()) if not frame.empty else len(competitions),
        "total_matches_available": int(frame["matches_total"].sum()) if not frame.empty else 0,
        "total_backtestable_matches": int(frame["backtestable_matches"].sum()) if not frame.empty else 0,
        "football_data_success_count": int(frame["football_data_status"].isin(["SUCCESS", "CACHE_HIT"]).sum()) if not frame.empty else 0,
        "understat_success_count": int(frame["understat_status"].isin(["SUCCESS", "CACHE_HIT"]).sum()) if not frame.empty else 0,
        "cache_written_count": 0,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    frame.to_csv(out / "multileague_cache_warm_results.csv", index=False)
    (out / "league_corpus_status.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "failed_sources_report.md").write_text("# v2.2 Failed Sources\n\n" + frame.to_csv(index=False), encoding="utf-8")
    (out / "multileague_cache_warm_dashboard.md").write_text("# v2.2 Cache Warm\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--season", required=True); p.add_argument("--competitions", default=""); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--output-dir", default=""); p.add_argument("--mock-data-dir", default=""); p.add_argument("--enable-network", action="store_true"); p.add_argument("--cache-only", action="store_true"); p.add_argument("--emit-all", action="store_true")
    result = warm_v22_multileague_cache(**vars(p.parse_args(argv)))
    for key in ["v22_cache_warm_status", "leagues_requested", "leagues_ready", "leagues_partial", "leagues_failed", "total_matches_available", "total_backtestable_matches", "football_data_success_count", "understat_success_count", "cache_written_count", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
