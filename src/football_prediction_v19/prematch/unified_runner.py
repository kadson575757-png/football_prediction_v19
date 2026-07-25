"""Unified, production-like prematch runner for v2.16.0."""

from __future__ import annotations

import csv
import json
import tempfile
import unicodedata
from datetime import datetime, timezone
from difflib import get_close_matches
from pathlib import Path
from typing import Iterable

import pandas as pd

from football_prediction_v19.analysis.v2130_goal_distribution import load_local_goal_results
from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features, prepare_matches
from football_prediction_v19.analysis.v2130_score_matrix import build_score_matrix, derive_distribution
from football_prediction_v19.analysis.v2131_repaired_goal_models import repaired_lambdas
from football_prediction_v19.analysis.v21_winner_model_core import run_winner_model_core
from football_prediction_v19.models.model_registry import active_model_for_role, get_model_registry
from football_prediction_v19.prematch.explanation import build_explanations
from football_prediction_v19.prematch.input_schema import MatchInput, normalize_team_key
from football_prediction_v19.prematch.match_profile import build_match_profile
from football_prediction_v19.prematch.model_comparison import compare_models
from football_prediction_v19.prematch.output_schema import (
    RUNNER_VERSION,
    SCHEMA_VERSION,
    flatten_prediction,
    normalized_probabilities,
    validate_probability_distribution,
)
from football_prediction_v19.prematch.shadow_winner_adapter import compare_primary_shadow, predict_shadow


DEFAULT_OUTPUT_DIR = "outputs/unified_prematch_analysis"
GOAL_CONFIG = {
    "model_name": "DIXON_COLES_ON_BEST_BASE_S10_RHO_01",
    "family": "DIXON_COLES_ON_BEST_BASE",
    "shrinkage_weight": 10,
    "form_window": 0,
    "form_weight": 0.0,
    "rho": -0.10,
}
SAFETY = {
    "automatic_betting_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
    "model_blending_enabled": False,
    "productive_betting_enabled": False,
}


def match_slug(match: MatchInput) -> str:
    raw = f"{match.match_date}-{match.competition}-{match.home_team}-vs-{match.away_team}"
    return "-".join(filter(None, (normalize_team_key(part) for part in raw.split("-"))))


def analyze_match(
    match: MatchInput,
    *,
    project_root: str | Path,
    output_base: str | Path | None = None,
    history: pd.DataFrame | None = None,
    enable_network: bool = False,
    strict_asof: bool = False,
    max_scoreline_goals: int = 10,
    include_shadow_challenger: bool = False,
    write_outputs: bool = True,
) -> dict:
    if max_scoreline_goals < 8:
        raise ValueError("max_scoreline_goals must be at least 8")
    project = Path(project_root).resolve()
    base = Path(output_base) if output_base else project / DEFAULT_OUTPUT_DIR
    out = base / match_slug(match)
    raw_history = load_local_goal_results(project) if history is None else prepare_matches(history)
    feature, source_audit, team_resolution_audit = _asof_feature(raw_history, match, project)
    if strict_asof and not bool(feature["asof_clean"]):
        raise RuntimeError("strict as-of validation failed")

    quality = _quality(feature)
    winner_features = _winner_features(feature, match, quality)
    with tempfile.TemporaryDirectory(prefix="v2160_winner_") as temp_dir:
        winner_raw = run_winner_model_core(
            winner_features,
            {"eligibility_class": "WINNER_MODEL_READY" if quality["minimum_team_history"] >= 5 else "WINNER_MODEL_PARTIAL"},
            temp_dir,
        )
    primary_probs = normalized_probabilities({
        "HOME": winner_raw["home_win_probability"],
        "DRAW": winner_raw["draw_probability"],
        "AWAY": winner_raw["away_win_probability"],
    })
    validate_probability_distribution(primary_probs)
    primary_rank = sorted(primary_probs, key=primary_probs.get, reverse=True)
    primary_edge = primary_probs[primary_rank[0]] - primary_probs[primary_rank[1]]

    lambdas = repaired_lambdas(feature, GOAL_CONFIG)
    matrix, residual_mass = build_score_matrix(
        lambdas["expected_home_goals"],
        lambdas["expected_away_goals"],
        max_goals=max_scoreline_goals,
        rho=GOAL_CONFIG["rho"],
    )
    distribution = derive_distribution(matrix)
    supporting_probs = normalized_probabilities({
        "HOME": distribution["home_win_probability"],
        "DRAW": distribution["draw_probability"],
        "AWAY": distribution["away_win_probability"],
    })
    scorelines = distribution["ranked_scorelines"]
    goal_output = {
        "model_name": active_model_for_role("GOAL_DISTRIBUTION")["name"],
        "model_role": "SUPPORTING_GOAL_DISTRIBUTION",
        "expected_home_goals": lambdas["expected_home_goals"],
        "expected_away_goals": lambdas["expected_away_goals"],
        "expected_total_goals": lambdas["expected_home_goals"] + lambdas["expected_away_goals"],
        "outcome_probabilities": supporting_probs,
        "most_likely_scoreline": distribution["top_scoreline"],
        "top_scorelines": scorelines[:10],
        "btts_yes_probability": distribution["btts_yes_probability"],
        "over_2_5_probability": distribution["over_2_5_probability"],
        "scoreline_max_goals": max_scoreline_goals,
        "score_matrix_residual_mass_before_normalization": residual_mass,
        "residual_mass_note": "Mass beyond the matrix boundary is reported here; the emitted finite matrix is normalized.",
        "home_goal_distribution": [
            {"goals": goals, "probability": float(matrix[goals, :].sum())}
            for goals in range(max_scoreline_goals + 1)
        ],
        "away_goal_distribution": [
            {"goals": goals, "probability": float(matrix[:, goals].sum())}
            for goals in range(max_scoreline_goals + 1)
        ],
        "fallback_reason": lambdas["fallback_reason"],
    }
    btts_output = {
        "yes_probability": distribution["btts_yes_probability"],
        "no_probability": distribution["btts_no_probability"],
        "top_outcome": "YES" if distribution["btts_yes_probability"] >= 0.5 else "NO",
    }
    totals_output = {
        "over_1_5_probability": distribution["over_1_5_probability"],
        "under_1_5_probability": distribution["under_1_5_probability"],
        "over_2_5_probability": distribution["over_2_5_probability"],
        "under_2_5_probability": distribution["under_2_5_probability"],
        "over_3_5_probability": distribution["over_3_5_probability"],
        "under_3_5_probability": distribution["under_3_5_probability"],
        "goals_0_1_probability": distribution["total_goals_0_1_probability"],
        "goals_2_3_probability": distribution["total_goals_2_3_probability"],
        "goals_4_plus_probability": distribution["total_goals_4_plus_probability"],
    }
    buckets = {
        "GOALS_0_1": totals_output["goals_0_1_probability"],
        "GOALS_2_3": totals_output["goals_2_3_probability"],
        "GOALS_4_PLUS": totals_output["goals_4_plus_probability"],
    }
    totals_output["most_likely_goal_bucket"] = max(buckets, key=buckets.get)
    scoreline_entries = [
        {
            "home_goals": int(row["scoreline"].split("-")[0]),
            "away_goals": int(row["scoreline"].split("-")[1]),
            "score": row["scoreline"],
            "probability": row["probability"],
            "result_type": (
                "HOME" if int(row["scoreline"].split("-")[0]) > int(row["scoreline"].split("-")[1])
                else "AWAY" if int(row["scoreline"].split("-")[1]) > int(row["scoreline"].split("-")[0])
                else "DRAW"
            ),
        }
        for row in scorelines
    ]
    scoreline_output = {
        "top_1": scoreline_entries[0],
        "top_3": scoreline_entries[:3],
        "top_5": scoreline_entries[:5],
        "score_matrix_limit": max_scoreline_goals,
        "remaining_probability_mass": residual_mass,
    }
    primary_output = {
        "model_name": active_model_for_role("PRIMARY_WINNER")["name"],
        "model_role": "PRIMARY_WINNER",
        "home_probability": primary_probs["HOME"],
        "draw_probability": primary_probs["DRAW"],
        "away_probability": primary_probs["AWAY"],
        "probabilities": primary_probs,
        "top_outcome": primary_rank[0],
        "top_probability": primary_probs[primary_rank[0]],
        "second_outcome": primary_rank[1],
        "top_outcome_edge": primary_edge,
        "probability_edge": primary_edge,
        "confidence": winner_raw["confidence"],
        "confidence_band": "VERY_LOW" if primary_edge < 0.03 else "LOW" if primary_edge < 0.07 else "MEDIUM" if primary_edge < 0.12 else "HIGH",
        "authoritative_for_1x2": True,
    }
    comparison = compare_models(primary_probs, supporting_probs)
    profile = build_match_profile(primary_probs, goal_output)
    feature_snapshot = _feature_snapshot(feature)
    quality.update({
        "history_status": feature["history_quality"],
        "home_history_count": quality["home_prior_matches_count"],
        "away_history_count": quality["away_prior_matches_count"],
        "venue_history_available": quality["venue_history_ready"],
        "maximum_source_date": feature["maximum_source_date"],
        "post_match_rows_used_count": int(feature["post_match_rows_used_count"]),
        "asof_clean": bool(feature["asof_clean"]),
        "quality_grade": quality["quality_tier"],
    })
    canonical_goal_output = {
        "expected_home_goals": goal_output["expected_home_goals"],
        "expected_away_goals": goal_output["expected_away_goals"],
        "expected_total_goals": goal_output["expected_total_goals"],
        "home_goal_distribution": goal_output["home_goal_distribution"],
        "away_goal_distribution": goal_output["away_goal_distribution"],
        "goal_model_home_probability": supporting_probs["HOME"],
        "goal_model_draw_probability": supporting_probs["DRAW"],
        "goal_model_away_probability": supporting_probs["AWAY"],
        "outcome_probabilities": supporting_probs,
        "most_likely_scoreline": goal_output["most_likely_scoreline"],
        "model_name": goal_output["model_name"],
        "model_role": "SUPPORTING_GOAL_COMPONENT",
        "remaining_probability_mass": residual_mass,
        "fallback_reason": goal_output["fallback_reason"],
    }
    explanations = build_explanations(feature_snapshot, canonical_goal_output, quality, primary_probs, comparison)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "analysis_version": RUNNER_VERSION,
        "runner_version": RUNNER_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match": match.as_dict(),
        "winner_prediction": primary_output,
        "goal_prediction": canonical_goal_output,
        "btts_prediction": btts_output,
        "totals_prediction": totals_output,
        "scoreline_prediction": scoreline_output,
        "model_comparison": comparison,
        "match_profile": profile,
        "explanation": explanations,
        "data_quality": quality,
        "asof_audit": {
            "target_match_date": feature["target_match_date"],
            "maximum_source_date": feature["maximum_source_date"],
            "post_match_rows_used_count": int(feature["post_match_rows_used_count"]),
            "asof_clean": bool(feature["asof_clean"]),
            "strict_asof_enabled": strict_asof,
        },
        "source_audit": source_audit,
        "team_resolution_audit": team_resolution_audit,
        "model_registry": get_model_registry(),
        "safety": {**SAFETY, "network_enabled": bool(enable_network)},
    }
    if include_shadow_challenger:
        shadow = predict_shadow(
            project_root=project,
            match=match,
            history=raw_history,
            primary_probabilities=primary_probs,
            data_quality=quality,
            canonical_home_team=str(feature["home_team"]),
            canonical_away_team=str(feature["away_team"]),
            canonical_competition=str(feature["competition"]),
            team_resolution_audit=team_resolution_audit,
        )
        payload["shadow_winner_prediction"] = shadow
        payload["shadow_comparison"] = compare_primary_shadow(primary_output, shadow)
    if write_outputs:
        _write_single_outputs(out, payload, matrix, feature_snapshot)
    payload["output_dir"] = str(out.resolve())
    return payload


def run_batch(
    rows: Iterable[MatchInput | tuple[int, Exception]],
    *,
    project_root: str | Path,
    output_base: str | Path | None = None,
    history: pd.DataFrame | None = None,
    enable_network: bool = False,
    strict_asof: bool = False,
    max_scoreline_goals: int = 10,
    include_shadow_challenger: bool = False,
) -> dict:
    project = Path(project_root).resolve()
    base = Path(output_base) if output_base else project / DEFAULT_OUTPUT_DIR
    stamp = datetime.now(timezone.utc).strftime("batch_%Y%m%dT%H%M%SZ")
    out = base / stamp
    predictions: list[dict] = []
    failures: list[dict] = []
    for position, item in enumerate(rows, start=1):
        if isinstance(item, tuple):
            failures.append({"row_number": item[0], "error": str(item[1])})
            continue
        try:
            predictions.append(analyze_match(
                item,
                project_root=project,
                output_base=out / "matches",
                history=history,
                enable_network=enable_network,
                strict_asof=strict_asof,
                max_scoreline_goals=max_scoreline_goals,
                include_shadow_challenger=include_shadow_challenger,
            ))
        except Exception as exc:
            failures.append({"row_number": position, **item.as_dict(), "error": str(exc)})
    out.mkdir(parents=True, exist_ok=True)
    flat = [flatten_prediction(payload) for payload in predictions]
    pd.DataFrame(flat).to_csv(out / "unified_predictions.csv", index=False)
    with (out / "unified_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for payload in predictions:
            handle.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")
    pd.DataFrame(failures).to_csv(out / "failed_rows.csv", index=False)
    report = [
        "# Unified Prematch Batch Report",
        "",
        f"- Runner: {RUNNER_VERSION}",
        f"- Successful rows: {len(predictions)}",
        f"- Failed rows: {len(failures)}",
        "- Network enabled: " + str(bool(enable_network)).lower(),
        "- Automatic betting enabled: false",
    ]
    (out / "unified_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {
        "status": "READY" if predictions else "FAILED",
        "successful_count": len(predictions),
        "failed_count": len(failures),
        "predictions": predictions,
        "failures": failures,
        "output_dir": str(out.resolve()),
    }


def _asof_feature(history: pd.DataFrame, match: MatchInput, project_root: Path) -> tuple[dict, list[dict], list[dict]]:
    frame = prepare_matches(history) if len(history) else history.copy()
    target_date = pd.Timestamp(match.match_date)
    resolved_competition = _resolve_competition(match.competition, frame)
    if len(frame):
        frame = frame[
            (frame["competition"].astype(str).str.casefold() == resolved_competition.casefold())
            & (frame["match_date"] < target_date)
        ].copy()
    home_audit = _resolve_team(match.home_team, frame, project_root)
    away_audit = _resolve_team(match.away_team, frame, project_root)
    home, away = home_audit["matched_history_team_name"] or match.home_team, away_audit["matched_history_team_name"] or match.away_team
    target = pd.DataFrame([{
        "match_date": target_date,
        "competition": resolved_competition,
        "season": match.season,
        "home_team": home,
        "away_team": away,
        "actual_home_goals": 0,
        "actual_away_goals": 0,
    }])
    combined = pd.concat([frame, target], ignore_index=True)
    features = build_rolling_goal_features(combined)
    selected = features[
        (features["match_date"] == target_date)
        & (features["home_team"] == home)
        & (features["away_team"] == away)
    ].iloc[-1].to_dict()
    source_audit = [{
        "source_name": "local_fixture_catalogs",
        "source_type": "LOCAL_RESULTS",
        "rows_available_before_target": int(len(frame)),
        "maximum_source_date": selected["maximum_source_date"],
        "target_match_date": selected["target_match_date"],
        "post_match_rows_used_count": int(selected["post_match_rows_used_count"]),
        "network_used": False,
        "source_date": selected["maximum_source_date"],
        "rows_used": int(len(frame)),
        "asof_clean": bool(selected["asof_clean"]),
    }]
    return selected, source_audit, [home_audit, away_audit]


def _canonical_team(requested: str, history: pd.DataFrame) -> str:
    if not len(history):
        return requested
    teams = sorted(set(history["home_team"].astype(str)) | set(history["away_team"].astype(str)))
    lookup = {normalize_team_key(team): team for team in teams}
    key = normalize_team_key(requested)
    if key in lookup:
        return lookup[key]
    candidates = get_close_matches(key, list(lookup), n=1, cutoff=0.86)
    return lookup[candidates[0]] if candidates else requested


def _resolve_competition(requested: str, history: pd.DataFrame) -> str:
    if not len(history):
        return requested
    values = sorted(history["competition"].astype(str).unique())
    requested_key = normalize_team_key(requested)
    exact = {normalize_team_key(value): value for value in values}
    if requested_key in exact:
        return exact[requested_key]
    contained = [value for key, value in exact.items() if key in requested_key or requested_key in key]
    return contained[0] if len(contained) == 1 else requested


def _resolve_team(requested: str, history: pd.DataFrame, project_root: Path) -> dict:
    teams = sorted(set(history["home_team"].astype(str)) | set(history["away_team"].astype(str))) if len(history) else []
    normalized = _accent_key(requested)
    exact = {_accent_key(team): team for team in teams}
    matched, method, alias_used = "", "UNRESOLVED", False
    if normalized in exact:
        matched = exact[normalized]
        method = "EXACT" if requested == matched else "NORMALIZED_EXACT"
    else:
        alias_path = project_root / "config/team_aliases.json"
        aliases = json.loads(alias_path.read_text(encoding="utf-8")) if alias_path.exists() else {}
        for canonical, alternatives in aliases.items():
            keys = {_accent_key(canonical), *(_accent_key(value) for value in alternatives)}
            if normalized in keys:
                candidates = [team for team in teams if _accent_key(team) in keys]
                if len(candidates) == 1:
                    matched, method, alias_used = candidates[0], "ALIAS", True
                break
        if not matched:
            contained = [team for team in teams if normalized.endswith(_accent_key(team)) or _accent_key(team).endswith(normalized)]
            if len(contained) == 1 and min(len(normalized), len(_accent_key(contained[0]))) >= 5:
                matched, method, alias_used = contained[0], "ALIAS", True
    count = int(
        (history["home_team"].astype(str).eq(matched) | history["away_team"].astype(str).eq(matched)).sum()
    ) if matched and len(history) else 0
    return {
        "requested_team_name": requested,
        "normalized_team_name": normalized,
        "matched_history_team_name": matched,
        "match_method": method,
        "alias_used": alias_used,
        "history_count": count,
        "rating_source": "PRIOR_COMPETITION_HISTORY" if count else "LEAGUE_AVERAGE_FALLBACK",
        "initial_rating": 1500.0,
        "final_prematch_rating": None,
        "fallback_used": count == 0,
        "fallback_reason": "" if count else ("TEAM_NAME_UNRESOLVED" if not matched else "NO_PRIOR_MATCHES"),
    }


def _accent_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if character.isascii() and character.isalnum())


def _winner_features(feature: dict, match: MatchInput, quality: dict) -> dict:
    return {
        "home_team": match.home_team,
        "away_team": match.away_team,
        "form_edge": float(feature["home_last5_points"]) - float(feature["away_last5_points"]),
        "goals_for_edge": float(feature["home_last5_goals_for"]) - float(feature["away_last5_goals_for"]),
        "goals_against_edge": float(feature["away_last5_goals_against"]) - float(feature["home_last5_goals_against"]),
        "xg_missing": True,
        "odds_missing": True,
        "market_available": False,
        "source_quality_score": 0.85 if quality["quality_tier"] == "HIGH" else 0.65 if quality["quality_tier"] == "MEDIUM" else 0.4,
        "league_prediction_tier": "TIER_2_RESULTS_ONLY",
        "early_season_risk": quality["minimum_team_history"] < 5,
    }


def _quality(feature: dict) -> dict:
    home_count = int(feature["home_prior_matches_count"])
    away_count = int(feature["away_prior_matches_count"])
    minimum = min(home_count, away_count)
    tier = "HIGH" if minimum >= 10 else "MEDIUM" if minimum >= 5 else "LOW"
    reasons = []
    if minimum < 5:
        reasons.append("One or both teams have fewer than five prior matches; league shrinkage is used.")
    if not feature["venue_history_ready"]:
        reasons.append("Venue-specific history is below the ready threshold.")
    return {
        "quality_tier": tier,
        "home_prior_matches_count": home_count,
        "away_prior_matches_count": away_count,
        "minimum_team_history": minimum,
        "venue_history_ready": bool(feature["venue_history_ready"]),
        "fallback_used": bool(feature["fallback_applied"]),
        "fallback_reasons": reasons,
        "feature_missing_rate": 0.0,
    }


def _feature_snapshot(feature: dict) -> dict:
    allowed = [
        "league_prior_matches_count", "home_prior_matches_count", "away_prior_matches_count",
        "league_home_goals_mean", "league_away_goals_mean", "home_attack_strength",
        "home_defense_strength", "away_attack_strength", "away_defense_strength",
        "home_points_per_match", "away_points_per_match", "home_venue_points_per_match",
        "away_venue_points_per_match", "home_last5_goals_for", "home_last5_goals_against",
        "away_last5_goals_for", "away_last5_goals_against", "home_last5_points",
        "away_last5_points", "home_venue_history_count", "away_venue_history_count",
        "venue_history_ready", "history_quality", "fallback_applied",
    ]
    return {key: _json_default(feature.get(key)) for key in allowed}


def _write_single_outputs(out: Path, payload: dict, matrix, feature_snapshot: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "prediction.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame([flatten_prediction(payload)]).to_csv(out / "prediction.csv", index=False)
    matrix_rows = [
        {"home_goals": home, "away_goals": away, "probability": float(matrix[home, away])}
        for home in range(matrix.shape[0])
        for away in range(matrix.shape[1])
    ]
    pd.DataFrame(matrix_rows).to_csv(out / "score_matrix.csv", index=False)
    pd.DataFrame([feature_snapshot]).to_csv(out / "feature_snapshot.csv", index=False)
    pd.DataFrame(payload["source_audit"]).to_csv(out / "source_audit.csv", index=False)
    pd.DataFrame([payload["asof_audit"]]).to_csv(out / "asof_audit.csv", index=False)
    (out / "report.md").write_text(_markdown_report(payload), encoding="utf-8")


def _markdown_report(payload: dict) -> str:
    match = payload["match"]
    primary = payload["winner_prediction"]
    goal = payload["goal_prediction"]
    quality = payload["data_quality"]
    probs = primary["probabilities"]
    sections = [
        ("A. Match", f"{match['home_team']} vs {match['away_team']} — {match['match_date']} ({match['competition']}, {match['season']})"),
        ("B. Data quality", f"{quality['quality_tier']}; fallback used: {str(quality['fallback_used']).lower()}."),
        ("C. Primary winner prediction", f"**Primary model:** HOME {probs['HOME']:.2%}, DRAW {probs['DRAW']:.2%}, AWAY {probs['AWAY']:.2%}. Top: **{primary['top_outcome']}**; edge {primary['top_outcome_edge']:.2%}."),
        ("D. Goal outlook", f"{goal['expected_home_goals']:.2f}–{goal['expected_away_goals']:.2f} expected goals; most likely score {goal['most_likely_scoreline']}."),
        ("E. BTTS", f"Yes {payload['btts_prediction']['yes_probability']:.4f}; no {payload['btts_prediction']['no_probability']:.4f}."),
        ("F. Goal lines", f"Over 2.5 {payload['totals_prediction']['over_2_5_probability']:.4f}; under 2.5 {payload['totals_prediction']['under_2_5_probability']:.4f}."),
        ("G. Most likely scorelines", "\n".join(f"{i}. {row['score']} — {row['probability']:.4f}" for i, row in enumerate(payload["scoreline_prediction"]["top_5"], 1))),
        ("H. Expected match profile", payload["match_profile"]["main_profile"]),
        ("I. Key factors", _factor_lines(payload["explanation"]["top_home_factors"] + payload["explanation"]["top_away_factors"])),
        ("J. Model consensus", payload["model_comparison"]["interpretation"]),
        ("K. Quality and uncertainty", "Quality:\n" + _factor_lines(payload["explanation"]["quality_factors"]) + "\n\nUncertainty:\n" + (_factor_lines(payload["explanation"]["uncertainty_factors"]) or "- No material uncertainty factor was triggered.")),
        ("L. Technical information", f"Maximum source date: {payload['asof_audit']['maximum_source_date'] or 'none'}; as-of clean: {str(payload['asof_audit']['asof_clean']).lower()}. No betting, staking, ROI, or model blending logic is enabled."),
    ]
    lines = ["# Unified Prematch Analysis", ""]
    for heading, body in sections:
        lines.extend([f"## {heading}", "", body, ""])
    if "shadow_winner_prediction" in payload:
        shadow = payload["shadow_winner_prediction"]
        comparison = payload["shadow_comparison"]
        lines.extend([
            "## Shadow Challenger", "",
            "Primary Winner:",
            f"- HOME {probs['HOME']:.2%}",
            f"- DRAW {probs['DRAW']:.2%}",
            f"- AWAY {probs['AWAY']:.2%}", "",
            "Shadow Challenger:",
            f"- HOME {shadow['home_probability']:.2%}",
            f"- DRAW {shadow['draw_probability']:.2%}",
            f"- AWAY {shadow['away_probability']:.2%}", "",
            (
                "The models agree on the top outcome."
                if comparison["top_outcome_agreement"]
                else "The Shadow Challenger differs from the Primary Winner."
            ),
            "",
            "The Shadow Challenger is in prospective validation and does not overwrite the primary prediction.",
            "",
        ])
    return "\n".join(lines)


def _factor_lines(factors: list[dict]) -> str:
    return "\n".join(f"- {factor['human_readable_explanation']}" for factor in factors[:5])


def _json_default(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value
