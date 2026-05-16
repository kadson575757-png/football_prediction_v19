from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .data import load_matches
from .fbref_scraper import fetch_and_save
from .features import build_fixture_features
from .model import load_model, predict_feature_rows, save_model, train_from_matches
from .rules_v19 import assess_prediction


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str, ensure_ascii=False))


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
    _print_json(assessment)


def cmd_backtest(args) -> None:
    matches = load_matches(args.input)
    metrics = run_backtest(matches, test_season=args.test_season, tune=args.tune)
    _print_json(metrics)


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
    p.set_defaults(func=cmd_predict)

    p = sub.add_parser("backtest", help="Run a season split backtest")
    p.add_argument("--input", required=True)
    p.add_argument("--test-season", type=int, required=True)
    p.add_argument("--tune", action="store_true")
    p.set_defaults(func=cmd_backtest)

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
