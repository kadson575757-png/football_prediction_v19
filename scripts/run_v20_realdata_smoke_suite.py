# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_v20_match import run_v20_match  # noqa: E402


def run_v20_realdata_smoke_suite(**kwargs: object) -> dict[str, object]:
    out = Path(str(kwargs.get("output_dir") or "outputs/analysis_preview/v201_realdata_smoke"))
    out.mkdir(parents=True, exist_ok=True)
    matches = _load_matches(Path(str(kwargs["matches"])))
    rows: list[dict[str, object]] = []
    for idx, match in enumerate(matches, start=1):
        match_out = out / f"match_{idx}"
        result = run_v20_match(
            home_team=match["home_team"],
            away_team=match["away_team"],
            competition=match["competition"],
            season=match["season"],
            match_date=match["match_date"],
            kickoff_time=match.get("kickoff_time", ""),
            source_profile=kwargs.get("source_profile", "config/v20_internet_sources.yaml"),
            output_dir=str(match_out),
            mock_data_dir=kwargs.get("mock_data_dir", ""),
            cache_dir=kwargs.get("cache_dir", ""),
            enable_network=bool(kwargs.get("enable_network", False)),
            cache_only=bool(kwargs.get("cache_only", False)),
            base_dir=str(ROOT),
        )
        live = result.get("live_sources", {})
        rows.append(
            {
                "match_id": result.get("match_context", {}).get("match_id", f"match_{idx}"),
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "decision_class": result.get("decision_class"),
                "status": result.get("v20_match_status"),
                "football_data_status": live.get("football", {}).get("football_data_live_status", "MOCK_MODE" if kwargs.get("mock_data_dir") else ""),
                "understat_status": live.get("xg", {}).get("understat_live_status", "MOCK_MODE" if kwargs.get("mock_data_dir") else ""),
                "odds_api_status": live.get("odds", {}).get("odds_api_status", "DISABLED_MISSING_KEY"),
                "table_available": result.get("table_available"),
                "xg_available": result.get("xg_available"),
                "odds_available": result.get("odds_available"),
                "cache_used": result.get("cache_used"),
            }
        )
    frame = pd.DataFrame(rows)
    total = len(frame)
    result = {
        "v20_realdata_smoke_status": "READY" if total and not frame["decision_class"].eq("DATA_BLOCKED").all() else ("PARTIAL" if total else "BLOCKED"),
        "matches_total": total,
        "matches_ready": int(frame["decision_class"].isin(["MODEL_TIP", "ANALYST_LEAN"]).sum()) if total else 0,
        "matches_partial": int(frame["decision_class"].eq("NO_BET").sum()) if total else 0,
        "matches_no_bet": int(frame["decision_class"].eq("NO_BET").sum()) if total else 0,
        "matches_data_blocked": int(frame["decision_class"].eq("DATA_BLOCKED").sum()) if total else 0,
        "football_data_success_count": int(frame["table_available"].astype(bool).sum()) if total else 0,
        "understat_success_count": int(frame["xg_available"].astype(bool).sum()) if total else 0,
        "odds_missing_key_count": int((frame["odds_available"].astype(bool) == False).sum()) if total else 0,
        "network_calls_enabled": bool(kwargs.get("enable_network", False)) and not bool(kwargs.get("cache_only", False)),
        "cache_used": bool(frame["cache_used"].astype(bool).any()) if total else False,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    frame.to_csv(out / "v20_realdata_smoke_results.csv", index=False)
    (out / "v20_realdata_smoke_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "v20_realdata_smoke_missing_data.md").write_text("# v2.0.1 Realdata Smoke Missing Data\n\n" + frame.to_csv(index=False), encoding="utf-8")
    (out / "v20_realdata_smoke_cache_report.md").write_text(f"# v2.0.1 Cache Report\n\ncache_used={str(result['cache_used']).lower()}\nnetwork_calls_enabled={str(result['network_calls_enabled']).lower()}\n", encoding="utf-8")
    (out / "v20_realdata_smoke_dashboard.md").write_text("# v2.0.1 Realdata Smoke Dashboard\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()), encoding="utf-8")
    return result


def _load_matches(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        return list(data.get("matches", data if isinstance(data, list) else []))
    rows = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        if clean == "matches:":
            continue
        if clean.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            clean = clean[2:].strip()
        if ":" in clean:
            key, value = clean.split(":", 1)
            current[key.strip()] = value.strip().strip('"').strip("'")
    if current:
        rows.append(current)
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--matches", required=True)
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    p.add_argument("--output-dir", default="outputs/analysis_preview/v201_realdata_smoke")
    p.add_argument("--mock-data-dir", default="")
    p.add_argument("--cache-dir", default="")
    p.add_argument("--enable-network", action="store_true")
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    result = run_v20_realdata_smoke_suite(**vars(p.parse_args(argv)))
    for key in ["v20_realdata_smoke_status", "matches_total", "matches_ready", "matches_partial", "matches_no_bet", "matches_data_blocked", "football_data_success_count", "understat_success_count", "odds_missing_key_count", "network_calls_enabled", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
