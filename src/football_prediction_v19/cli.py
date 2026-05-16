from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import build_betting_report, run_bet_backtest, run_backtest
from .data import load_matches, prepare_real_matches_file
from .excel_report import create_predictions_excel_report
from .fbref_scraper import fetch_and_save
from .features import build_fixture_features
from .importers.fbref import normalize_fbref_csv
from .importers.football_data import (
    LEAGUE_CODES,
    bulk_download,
    download_and_prepare,
    download_season,
    normalize_football_data_csv,
)
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
    summary = prepare_real_matches_file(args.input, args.output, input_format=args.format)
    _print_prepare_summary(summary)


def _print_prepare_summary(summary: dict[str, object]) -> None:
    print("Prepared real match data")
    print(f"Input: {summary['input']}")
    print(f"Output: {summary['output']}")
    print(f"Detected format: {summary['format']}")
    print(f"Rows read: {summary['rows_read']}")
    print(f"Rows written: {summary['rows_written']}")
    print(f"Rows dropped because they were incomplete historical matches: {summary['rows_dropped']}")
    print(f"Optional advanced columns found: {summary['optional_found']}")
    print(f"Optional advanced columns missing: {summary['optional_missing']}")


def cmd_import_football_data(args) -> None:
    summary = normalize_football_data_csv(args.input, args.output)
    _print_prepare_summary(summary)


def cmd_import_fbref(args) -> None:
    summary = normalize_fbref_csv(args.input, args.output)
    _print_prepare_summary(summary)


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


def cmd_export_excel(args) -> None:
    output = create_predictions_excel_report(args.predictions, args.output)
    print(f"Saved Excel report: {output}")


def cmd_download_prepare_football_data(args) -> None:
    import requests

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    if not args.leagues:
        raise SystemExit("Error: --leagues is required and must not be empty.")
    if not args.seasons:
        raise SystemExit("Error: --seasons is required and must not be empty.")

    processed_paths: list[Path] = []
    total_written = 0

    for league in args.leagues:
        for season in args.seasons:
            print(f"\nProcessing {league} season {season}/{season + 1}...")
            try:
                result = download_and_prepare(league, season, raw_dir, processed_dir)
            except ValueError as exc:
                raise SystemExit(f"Error: {exc}") from exc
            except requests.HTTPError as exc:
                raise SystemExit(
                    f"Download failed for {league} {season}: {exc}\n"
                    "Check that the league code and season are correct."
                ) from exc

            processed_paths.append(Path(result["processed_path"]))
            total_written += result["rows_written"]
            print(f"  Raw file    : {result['raw_path']}")
            print(f"  Processed   : {result['processed_path']}")
            print(f"  Rows read   : {result['rows_read']}")
            print(f"  Rows written: {result['rows_written']}")
            print(f"  Rows dropped: {result['rows_dropped']} (incomplete historical rows)")
            if result.get("optional_found"):
                print(f"  Advanced columns found: {result['optional_found']}")

    print(f"\nDone. {total_written} total rows written across {len(processed_paths)} file(s).")

    if args.combine_output:
        import pandas as pd

        combine_path = Path(args.combine_output)
        combine_path.parent.mkdir(parents=True, exist_ok=True)
        frames = [pd.read_csv(p) for p in processed_paths if p.exists()]
        if not frames:
            raise SystemExit("Error: No processed files to combine.")
        combined = pd.concat(frames, ignore_index=True)
        combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
        combined = combined.sort_values("date").reset_index(drop=True)
        combined.to_csv(combine_path, index=False)
        print(f"Combined output: {combine_path} ({len(combined)} rows)")


def cmd_download_football_data(args) -> None:
    leagues = args.leagues
    seasons = args.seasons
    output_dir = args.output_dir
    if len(leagues) == 1 and len(seasons) == 1:
        path = download_season(leagues[0], seasons[0], output_dir)
        print(f"Downloaded: {path}")
    else:
        paths = bulk_download(leagues, seasons, output_dir)
        for path in paths:
            print(f"Downloaded: {path}")
        print(f"Total: {len(paths)} file(s)")


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
    p.add_argument("--format", default="auto", choices=["auto", "native", "fbref", "football-data"])
    p.set_defaults(func=cmd_prepare_data)

    p = sub.add_parser("import-football-data", help="Normalize a football-data.co.uk CSV into project format")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_import_football_data)

    p = sub.add_parser("import-fbref", help="Normalize a FBref-style CSV into project format")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_import_fbref)

    p = sub.add_parser("import-and-prepare", help="Auto-detect and prepare a real match CSV")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--format", default="auto", choices=["auto", "native", "fbref", "football-data"])
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

    p = sub.add_parser("export-excel", help="Create an Excel report from prediction CSV output")
    p.add_argument("--predictions", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_export_excel)

    p = sub.add_parser(
        "download-prepare-football-data",
        help="Download and prepare football-data.co.uk CSVs into training-ready files",
    )
    p.add_argument(
        "--leagues",
        nargs="+",
        required=True,
        metavar="CODE",
        help=(
            "One or more league codes (e.g. E0 D1) or friendly names "
            f"(e.g. premier-league bundesliga). Available names: {', '.join(sorted(LEAGUE_CODES))}."
        ),
    )
    p.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        required=True,
        metavar="YEAR",
        help="One or more season start years (e.g. 2023 for the 2023-24 season).",
    )
    p.add_argument(
        "--raw-dir",
        required=True,
        metavar="DIR",
        help="Directory where raw downloaded CSV files are saved.",
    )
    p.add_argument(
        "--processed-dir",
        required=True,
        metavar="DIR",
        help="Directory where cleaned training-ready CSV files are saved.",
    )
    p.add_argument(
        "--combine-output",
        default=None,
        metavar="FILE",
        help="Optional path to a combined CSV of all processed files, sorted by date.",
    )
    p.set_defaults(func=cmd_download_prepare_football_data)

    p = sub.add_parser(
        "download-football-data",
        help="Download CSV(s) from football-data.co.uk automatically",
    )
    p.add_argument(
        "--leagues",
        nargs="+",
        required=True,
        metavar="CODE",
        help=(
            "One or more league codes (e.g. E0 D1) or friendly names "
            f"(e.g. premier-league bundesliga). Available names: {', '.join(sorted(LEAGUE_CODES))}."
        ),
    )
    p.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        required=True,
        metavar="YEAR",
        help="One or more season start years (e.g. 2022 2023 for 2022-23 and 2023-24).",
    )
    p.add_argument(
        "--output-dir",
        required=True,
        metavar="DIR",
        help="Directory where downloaded CSV files will be saved.",
    )
    p.set_defaults(func=cmd_download_football_data)

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
