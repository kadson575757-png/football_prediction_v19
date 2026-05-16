from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import build_betting_report, run_bet_backtest, run_backtest
from .data import load_matches, prepare_real_matches_file
from .fbref_scraper import fetch_and_save
from .features import build_fixture_features
from .model import load_model, predict_feature_rows, save_model, train_from_matches
from .odds import value_recommendation
from .rules_v19 import assess_prediction


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str, ensure_ascii=False))


REQUIRED_FIXTURE_COLUMNS = [
    "date",
    "season",
    "league",
    "home_team",
    "away_team",
    "venue",
    "referee",
    "odds_home",
    "odds_draw",
    "odds_away",
    "formation_home_xg90",
    "formation_away_xg90",
    "fatigue_home",
    "fatigue_away",
]


def _serialize_reasons(values: list[str]) -> str:
    return " | ".join(values)


def _value_recommendation(
    pred: pd.Series,
    probs: dict[str, float],
    assessment: dict,
    min_edge: float,
    max_chaos: float,
    min_control: float,
) -> dict[str, object]:
    return value_recommendation(
        pred.get("odds_home"),
        pred.get("odds_draw"),
        pred.get("odds_away"),
        probs,
        assessment,
        min_edge,
        max_chaos,
        min_control,
    )


def _fixture_extra(row: pd.Series) -> dict[str, float]:
    extra: dict[str, float] = {}
    for key in ["formation_home_xg90", "formation_away_xg90", "fatigue_home", "fatigue_away"]:
        value = row.get(key)
        if pd.notna(value):
            extra[key] = float(value)
    return extra


def _predict_assessment_row(
    history: pd.DataFrame,
    bundle: dict,
    row: pd.Series,
    min_edge: float,
    max_chaos: float,
    min_control: float,
) -> dict[str, object]:
    fixture = build_fixture_features(
        history,
        home_team=row["home_team"],
        away_team=row["away_team"],
        match_date=row["date"],
        venue=row.get("venue", "Unknown"),
        referee=row.get("referee", "Unknown"),
        odds_home=row.get("odds_home"),
        odds_draw=row.get("odds_draw"),
        odds_away=row.get("odds_away"),
        extra=_fixture_extra(row),
    )
    pred = predict_feature_rows(bundle, fixture).iloc[0]
    probs = {"H": pred["prob_home"], "D": pred["prob_draw"], "A": pred["prob_away"]}
    assessment = assess_prediction(pred, probs)
    value = _value_recommendation(pred, probs, assessment, min_edge, max_chaos, min_control)
    top_pick = assessment["top_model_side"]
    confidence = max(assessment["probabilities"].values())
    return {
        "date": pd.to_datetime(row["date"]).date().isoformat(),
        "league": row["league"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "prob_home": round(float(pred["prob_home"]), 4),
        "prob_draw": round(float(pred["prob_draw"]), 4),
        "prob_away": round(float(pred["prob_away"]), 4),
        "top_pick": top_pick,
        "confidence": round(float(confidence), 4),
        "control_score": assessment["control_model_score"],
        "chaos_score": assessment["chaos_score"],
        "tdi_home": assessment["tdi"]["home"],
        "tdi_away": assessment["tdi"]["away"],
        "odds_home": value["odds_home"],
        "odds_draw": value["odds_draw"],
        "odds_away": value["odds_away"],
        "implied_home": value["implied_home"],
        "implied_draw": value["implied_draw"],
        "implied_away": value["implied_away"],
        "fair_home": value["fair_home"],
        "fair_draw": value["fair_draw"],
        "fair_away": value["fair_away"],
        "edge_home": value["edge_home"],
        "edge_draw": value["edge_draw"],
        "edge_away": value["edge_away"],
        "value_pick": value["value_pick"],
        "value_edge": value["value_edge"],
        "bet_recommendation": value["bet_recommendation"],
        "no_bet_reasons": _serialize_reasons(value["no_bet_reasons"]),
        "v19_flags": _serialize_reasons(assessment["locks"]),
    }


def _load_fixtures(path: str | Path) -> pd.DataFrame:
    fixtures = load_matches(path)
    missing = [col for col in REQUIRED_FIXTURE_COLUMNS if col not in fixtures.columns]
    if missing:
        raise ValueError(f"Missing required fixture columns: {missing}")
    fixtures = fixtures.copy()
    fixtures["date"] = pd.to_datetime(fixtures["date"], errors="coerce")
    if fixtures["date"].isna().any():
        raise ValueError("Fixture file contains invalid dates.")
    numeric_cols = [
        "odds_home",
        "odds_draw",
        "odds_away",
        "formation_home_xg90",
        "formation_away_xg90",
        "fatigue_home",
        "fatigue_away",
    ]
    for col in numeric_cols:
        fixtures[col] = pd.to_numeric(fixtures[col], errors="coerce")
    for col in ["league", "home_team", "away_team", "venue", "referee", "season"]:
        fixtures[col] = fixtures[col].fillna("Unknown").astype(str).str.strip()
    return fixtures


def cmd_train(args) -> None:
    matches = load_matches(args.input)
    model, table, metrics, cols = train_from_matches(
        matches,
        model_name=args.model_type,
        test_season=args.test_season,
        min_history=args.min_history,
        tune=args.tune,
    )
    save_model(args.model, model, cols, metrics)
    if args.features_out:
        Path(args.features_out).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.features_out, index=False)
    _print_json(metrics)
    print(f"Saved model: {args.model}")


def cmd_predict(args) -> None:
    history = load_matches(args.history)
    bundle = load_model(args.model)
    extra = {}
    for key in ["formation_home_xg90", "formation_away_xg90", "fatigue_home", "fatigue_away"]:
        value = getattr(args, key)
        if value is not None:
            extra[key] = value
    fixture = build_fixture_features(
        history,
        home_team=args.home,
        away_team=args.away,
        match_date=args.date,
        venue=args.venue,
        referee=args.referee,
        matchweek=args.matchweek,
        odds_home=args.odds_home,
        odds_draw=args.odds_draw,
        odds_away=args.odds_away,
        extra=extra,
    )
    pred = predict_feature_rows(bundle, fixture).iloc[0]
    probs = {"H": pred["prob_home"], "D": pred["prob_draw"], "A": pred["prob_away"]}
    assessment = assess_prediction(pred, probs)
    assessment["match"] = {
        "home": args.home,
        "away": args.away,
        "date": args.date,
        "venue": args.venue,
        "referee": args.referee,
    }
    value = _value_recommendation(pred, probs, assessment, args.min_edge, args.max_chaos, args.min_control)
    assessment["odds_value"] = value
    _print_json(assessment)


def cmd_predict_fixtures(args) -> None:
    history = load_matches(args.history)
    bundle = load_model(args.model)
    fixtures = _load_fixtures(args.fixtures)
    rows = [
        _predict_assessment_row(history, bundle, row, args.min_edge, args.max_chaos, args.min_control)
        for _, row in fixtures.iterrows()
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Saved predictions: {output}")


def cmd_prepare_data(args) -> None:
    summary = prepare_real_matches_file(args.input, args.output)
    print("Prepared real match data")
    print(f"Input: {summary['input']}")
    print(f"Output: {summary['output']}")
    print(f"Rows read: {summary['rows_read']}")
    print(f"Rows written: {summary['rows_written']}")
    print(f"Rows dropped because they were incomplete historical matches: {summary['rows_dropped']}")
    print(f"Optional advanced columns found: {summary['optional_found']}")
    print(f"Optional advanced columns missing: {summary['optional_missing']}")


def cmd_backtest(args) -> None:
    matches = load_matches(args.input)
    metrics = run_backtest(matches, test_season=args.test_season, tune=args.tune)
    _print_json(metrics)


def cmd_backtest_bets(args) -> None:
    matches = load_matches(args.history)
    bundle = load_model(args.model)
    results = run_bet_backtest(
        matches,
        bundle,
        min_edge=args.min_edge,
        max_chaos=args.max_chaos,
        min_control=args.min_control,
    )
    output = Path(args.output)
    report = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)
    report.write_text(build_betting_report(results), encoding="utf-8")
    print(f"Saved betting backtest: {output}")
    print(f"Saved betting report: {report}")


def cmd_gather_fbref(args) -> None:
    output = fetch_and_save(args.output, args.start_year, args.end_year, args.comp_ids)
    print(f"Saved: {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Football Prediction v1.9")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("train", help="Train a match prediction model")
    p.add_argument("--input", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--model-type", default="random_forest", choices=["random_forest", "logistic_regression", "gradient_boosting"])
    p.add_argument("--test-season", type=int, default=None)
    p.add_argument("--min-history", type=int, default=1)
    p.add_argument("--tune", action="store_true")
    p.add_argument("--features-out", default=None)
    p.set_defaults(func=cmd_train)

    p = sub.add_parser("predict", help="Predict a single match")
    p.add_argument("--history", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--home", required=True)
    p.add_argument("--away", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--venue", default="Unknown")
    p.add_argument("--referee", default="Unknown")
    p.add_argument("--matchweek", type=float, default=None)
    p.add_argument("--odds-home", type=float, default=None)
    p.add_argument("--odds-draw", type=float, default=None)
    p.add_argument("--odds-away", type=float, default=None)
    p.add_argument("--formation-home-xg90", type=float, default=None)
    p.add_argument("--formation-away-xg90", type=float, default=None)
    p.add_argument("--fatigue-home", type=float, default=None)
    p.add_argument("--fatigue-away", type=float, default=None)
    p.add_argument("--min-edge", type=float, default=0.03)
    p.add_argument("--max-chaos", type=float, default=7.0)
    p.add_argument("--min-control", type=float, default=7.0)
    p.set_defaults(func=cmd_predict)

    p = sub.add_parser("predict-fixtures", help="Predict a list of upcoming fixtures from CSV")
    p.add_argument("--history", required=True)
    p.add_argument("--fixtures", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--min-edge", type=float, default=0.03)
    p.add_argument("--max-chaos", type=float, default=7.0)
    p.add_argument("--min-control", type=float, default=7.0)
    p.set_defaults(func=cmd_predict_fixtures)

    p = sub.add_parser("prepare-data", help="Clean real historical match data for training")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_prepare_data)

    p = sub.add_parser("backtest", help="Run a season split backtest")
    p.add_argument("--input", required=True)
    p.add_argument("--test-season", type=int, required=True)
    p.add_argument("--tune", action="store_true")
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("backtest-bets", help="Backtest value betting recommendations on historical matches")
    p.add_argument("--history", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--min-edge", type=float, default=0.03)
    p.add_argument("--max-chaos", type=float, default=7.0)
    p.add_argument("--min-control", type=float, default=7.0)
    p.set_defaults(func=cmd_backtest_bets)

    p = sub.add_parser("gather-fbref", help="Fetch FBref schedules with pandas.read_html")
    p.add_argument("--output", required=True)
    p.add_argument("--start-year", type=int, required=True)
    p.add_argument("--end-year", type=int, required=True)
    p.add_argument("--comp-ids", type=int, nargs="+", default=[9, 12])
    p.set_defaults(func=cmd_gather_fbref)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
