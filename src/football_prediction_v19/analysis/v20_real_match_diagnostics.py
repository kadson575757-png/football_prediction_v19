# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import json


PROVIDERS = {
    "football_data": ("football", "football_data_live_status"),
    "understat": ("xg", "understat_live_status"),
    "odds_api": ("odds", "odds_api_status"),
    "api_football": ("api_football", "api_football_optional_status"),
}


def build_real_match_diagnostics(result: dict[str, object]) -> dict[str, object]:
    live = result.get("live_sources", {}) or {}
    coverage = result.get("coverage", {}) or {}
    source_status = {name: _provider_status(live.get(live_key, {}) or {}, status_key) for name, (live_key, status_key) in PROVIDERS.items()}
    missing_data = {
        "table_form": not bool(result.get("table_available")),
        "xg": not bool(result.get("xg_available")),
        "player_xg": not bool(coverage.get("player_xg_available", False)),
        "odds": not bool(result.get("odds_available")),
        "fixture": result.get("fixture_resolution_status") in {"NOT_FOUND", "AMBIGUOUS"},
        "lineups": not bool(result.get("features", {}).get("lineups_available", False)),
        "injuries": not bool(result.get("features", {}).get("injuries_available", False)),
    }
    block_reasons = _block_reasons(result, source_status, missing_data)
    main_block_reason = block_reasons[0] if block_reasons else ""
    return {
        "source_status": source_status,
        "missing_data": missing_data,
        "block_reasons": block_reasons,
        "main_block_reason": main_block_reason,
        "recommended_fix": _recommended_fix(main_block_reason, source_status),
    }


def write_debug_reports(result: dict[str, object], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    diagnostics = build_real_match_diagnostics(result)
    summary_json = out / "debug_source_summary.json"
    summary_md = out / "debug_source_summary.md"
    cache_md = out / "debug_cache_summary.md"
    fixture_md = out / "debug_fixture_resolution.md"
    block_md = out / "debug_block_reason.md"
    summary_json.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    summary_md.write_text(_source_status_markdown(diagnostics), encoding="utf-8")
    cache_md.write_text(_cache_markdown(diagnostics), encoding="utf-8")
    fixture_md.write_text(f"# Fixture Resolution\n\n- status: {result.get('fixture_resolution_status')}\n- reason: {result.get('reason', '')}\n- matched_sources: {result.get('matched_sources', [])}\n- candidate_matches: {len(result.get('candidate_matches', []))}\n- suggested_team_names: {', '.join(result.get('suggested_team_names', [])) if result.get('suggested_team_names') else 'none'}\n", encoding="utf-8")
    block_md.write_text(f"# Block Reason\n\n- main_block_reason: {diagnostics['main_block_reason'] or 'none'}\n- recommended_fix: {diagnostics['recommended_fix']}\n", encoding="utf-8")
    return {
        "debug_source_summary_json_path": str(summary_json.resolve()),
        "debug_source_summary_md_path": str(summary_md.resolve()),
        "debug_cache_summary_md_path": str(cache_md.resolve()),
        "debug_fixture_resolution_md_path": str(fixture_md.resolve()),
        "debug_block_reason_md_path": str(block_md.resolve()),
    }


def _provider_status(payload: dict[str, object], status_key: str) -> dict[str, object]:
    status = str(payload.get(status_key, "MISSING"))
    cache_diag = payload.get("cache_diagnostics", {}) or {}
    cache_status = payload.get("cache_status", {}) or {}
    return {
        "status": status,
        "reason": _reason(status, payload),
        "cache_used": bool(payload.get("cache_used", False)),
        "cache_written": bool(cache_diag.get("cache_write_success", False)),
        "records_count": int(payload.get("records_count", payload.get("matches_used", 0)) or 0),
        "network_attempted": bool(cache_diag.get("network_attempted", False)),
        "request_blocked": bool(cache_diag.get("request_blocked", False)),
        "fetch_success": bool(cache_diag.get("fetch_success", False)),
        "cache_lookup_attempted": bool(cache_diag.get("cache_lookup_attempted", True)),
        "expected_cache_path": cache_diag.get("expected_cache_path") or cache_status.get("cache_path", ""),
        "cache_error": cache_diag.get("cache_error", ""),
        "url": payload.get("url", ""),
        "candidate_matches": payload.get("candidate_matches", []),
        "suggested_team_names": payload.get("suggested_team_names", []),
        "api_key_present": payload.get("api_key_present", None),
    }


def _block_reasons(result: dict[str, object], source_status: dict[str, dict[str, object]], missing_data: dict[str, bool]) -> list[str]:
    reasons = []
    fixture = result.get("fixture_resolution_status")
    if fixture == "NOT_FOUND":
        reasons.append("fixture_not_found")
    if fixture == "AMBIGUOUS":
        reasons.append("ambiguous_fixture")
    if result.get("leakage_status") == "BLOCKED":
        reasons.append("leakage_blocked")
    if missing_data["table_form"]:
        reasons.append("missing_table_form")
    if missing_data["xg"]:
        reasons.append("missing_xg")
    if missing_data["odds"] and missing_data["xg"]:
        reasons.append("missing_odds")
    if result.get("source_quality_band") == "LOW":
        reasons.append("low_source_quality")
    if result.get("source_quality_band") == "BLOCKED":
        reasons.append("low_source_quality")
    if any(s["status"].startswith("UNSUPPORTED") for s in source_status.values()):
        reasons.append("unsupported_league")
    if not result.get("cache_used") and any(s.get("expected_cache_path") for s in source_status.values()):
        reasons.append("no_cache")
    if not result.get("network_calls_enabled") and any(s["status"] == "DISABLED_NETWORK" for s in source_status.values()):
        reasons.append("network_disabled")
    if missing_data["xg"] and any(s["status"] == "DISABLED_MISSING_KEY" for s in source_status.values()):
        reasons.append("api_key_missing")
    return list(dict.fromkeys(reasons))


def _reason(status: str, payload: dict[str, object]) -> str:
    if status == "CACHE_HIT":
        return "cache hit"
    if status in {"SUCCESS", "READY"}:
        return "source normalized successfully"
    if status == "DISABLED_NETWORK":
        return "network disabled and cache unavailable"
    if status == "DISABLED_MISSING_KEY":
        return "required API key is missing"
    if status.startswith("UNSUPPORTED"):
        return "league/source mapping is unsupported"
    if status in {"MATCH_NOT_FOUND", "FAILED_FETCH", "FAILED_PARSE", "FAILED"}:
        return "source fetch, parse or match resolution failed"
    if status == "DISABLED_BY_CONFIG":
        return "optional source disabled by config"
    return str(payload.get("warnings", "")) or status.lower()


def _recommended_fix(reason: str, source_status: dict[str, dict[str, object]]) -> str:
    if reason == "fixture_not_found":
        return "Check team names, match date, league mapping, and source cache contents."
    if reason == "missing_table_form":
        return "Repair football-data source/cache first; table/form is a core source."
    if reason == "missing_xg":
        return "Provide Understat cache/live payload or accept analyst lean/no-bet without xG."
    if reason == "missing_odds":
        return "Provide odds cache/API key or accept analyst lean/no-bet without odds."
    if reason == "api_key_missing":
        return "Set the required API key environment variable, or run with cache/mock data."
    if reason == "network_disabled":
        return "Use --enable-network manually or provide cache."
    if reason == "no_cache":
        paths = [str(v.get("expected_cache_path")) for v in source_status.values() if v.get("expected_cache_path")]
        return "Cache not used. Expected cache path: " + (paths[0] if paths else "unknown")
    return "Inspect source_status and missing_data; do not force a tip with incomplete core sources."


def _source_status_markdown(diagnostics: dict[str, object]) -> str:
    lines = ["# Source Status", ""]
    for provider, data in diagnostics["source_status"].items():
        lines.append(f"- {provider}: {data['status']} ({data['reason']}); url={data.get('url') or 'n/a'}; cache_used={str(data['cache_used']).lower()}; cache_written={str(data['cache_written']).lower()}; records={data['records_count']}; candidates={len(data.get('candidate_matches', []))}")
    lines.extend(["", f"main_block_reason: {diagnostics['main_block_reason'] or 'none'}", f"recommended_fix: {diagnostics['recommended_fix']}", ""])
    return "\n".join(lines)


def _cache_markdown(diagnostics: dict[str, object]) -> str:
    lines = ["# Cache Diagnostics", ""]
    for provider, data in diagnostics["source_status"].items():
        lines.append(f"- {provider}: cache_used={str(data['cache_used']).lower()} cache_written={str(data['cache_written']).lower()} expected_cache_path={data['expected_cache_path']} cache_error={data['cache_error']}")
    return "\n".join(lines) + "\n"
