"""Central registry for models allowed in the unified prematch runner."""

from __future__ import annotations

from copy import deepcopy


_MODELS = {
    "PRIMARY_WINNER_V21_RESULTS_CORE": {
        "name": "PRIMARY_WINNER_V21_RESULTS_CORE",
        "status": "ACTIVE",
        "role": "PRIMARY_WINNER",
        "version": "v2.1",
        "adapter": "football_prediction_v19.analysis.v21_winner_model_core.run_winner_model_core",
        "training_validation_status": "MULTI_SEASON_MULTI_LEAGUE_VALIDATED",
        "approved_role": "PRIMARY_WINNER",
        "replacement_interface": "run_winner_model_core(features, eligibility, output_dir)",
        "limitations": [
            "Results-based rolling features only when optional prematch sources are unavailable.",
            "Probabilities are the authoritative 1X2 output and must not be blended.",
        ],
    },
    "DIXON_COLES_ON_BEST_BASE_S10_RHO_01": {
        "name": "DIXON_COLES_ON_BEST_BASE_S10_RHO_01",
        "status": "ACTIVE_SUPPORTING",
        "role": "GOAL_DISTRIBUTION",
        "version": "v2.13.1",
        "adapter": "football_prediction_v19.analysis.v2131_repaired_goal_models.repaired_lambdas",
        "training_validation_status": "FAILED_ROBUST_GOAL_INTEGRATION_GATE",
        "approved_role": "GOAL_DISTRIBUTION",
        "replacement_interface": "repaired_lambdas(feature, frozen_config)",
        "limitations": [
            "Supporting goal and scoreline distribution only.",
            "Must never overwrite or blend PRIMARY_WINNER probabilities.",
        ],
    },
    "V2140_GRADIENT_BOOSTING_CHALLENGER": {
        "name": "V2140_GRADIENT_BOOSTING_CHALLENGER",
        "status": "REJECTED",
        "role": "EXCLUDED",
        "version": "v2.14.0",
        "adapter": None,
        "training_validation_status": "REJECTED",
        "approved_role": "NONE",
        "replacement_interface": None,
        "limitations": ["Rejected by the leakage-safe challenger evaluation."],
    },
    "V2150_ENRICHED_PREMATCH_CHALLENGER": {
        "name": "V2150_ENRICHED_PREMATCH_CHALLENGER",
        "status": "REJECTED",
        "role": "EXCLUDED",
        "version": "v2.15.0",
        "adapter": None,
        "training_validation_status": "REJECTED",
        "approved_role": "NONE",
        "replacement_interface": None,
        "limitations": ["Did not satisfy challenger acceptance criteria."],
    },
}


def get_model_registry() -> dict[str, dict]:
    return deepcopy(_MODELS)


def get_model(name: str) -> dict:
    try:
        return deepcopy(_MODELS[name])
    except KeyError as exc:
        raise KeyError(f"Unknown registered model: {name}") from exc


def active_model_for_role(role: str) -> dict:
    matches = [
        model
        for model in _MODELS.values()
        if model["role"] == role and model["status"] in {"ACTIVE", "ACTIVE_SUPPORTING"}
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one active model for role {role}, found {len(matches)}")
    return deepcopy(matches[0])


def rejected_model_names() -> tuple[str, ...]:
    return tuple(name for name, model in _MODELS.items() if model["status"] == "REJECTED")
