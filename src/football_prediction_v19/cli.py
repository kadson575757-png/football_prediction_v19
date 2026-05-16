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
from .fixtures import prepare_fixtures_file
from .odds_import import merge_odds_file, prepare_odds_file
from .xg_import import merge_xg_file, prepare_xg_file
from .training import compare_models
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


def cmd_prepare_fixtures(args) -> None:
    try:
        summary = prepare_fixtures_file(
            args.input,
            args.output,
            input_format=args.format,
            default_season=args.default_season,
            default_league=args.default_league,
        )
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("Prepared upcoming fixtures")
    print(f"Input : {summary['input']}")
    print(f"Output: {summary['output']}")
    print(f"Rows in : {summary['rows_in']}")
    print(f"Rows out: {summary['rows_out']}")


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
    output = create_predictions_excel_report(
        args.predictions,
        args.output,
        model_comparison_csv=getattr(args, "model_comparison", None),
        model_metadata_json=getattr(args, "model_metadata", None),
        backtest_csv=getattr(args, "backtest_csv_in", None),
        backtest_report_md=getattr(args, "backtest_report_in", None),
    )
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


def cmd_prepare_odds(args) -> None:
    try:
        summary = prepare_odds_file(args.input, args.output, input_format=args.format)
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("Prepared odds file")
    print(f"Input   : {summary['input']}")
    print(f"Output  : {summary['output']}")
    print(f"Rows in : {summary['rows_in']}")
    print(f"Rows out: {summary['rows_out']}")


def cmd_merge_odds_fixtures(args) -> None:
    try:
        summary = merge_odds_file(
            args.fixtures,
            args.odds,
            args.output,
            allow_date_window=args.allow_date_window,
            prefer_bookmaker=args.prefer,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("Merged odds into fixtures")
    print(f"Output          : {summary['output']}")
    print(f"Total fixtures  : {summary['fixtures_total']}")
    print(f"Fixtures updated: {summary['matched']}")
    print(f"Still no odds   : {summary['still_missing_odds']}")


def cmd_prepare_xg(args) -> None:
    try:
        summary = prepare_xg_file(args.input, args.output, input_format=args.format)
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("Prepared xG file")
    print(f"Input   : {summary['input']}")
    print(f"Output  : {summary['output']}")
    print(f"Rows in : {summary['rows_in']}")
    print(f"Rows out: {summary['rows_out']}")


def cmd_merge_xg_history(args) -> None:
    try:
        summary = merge_xg_file(
            args.history,
            args.xg,
            args.output,
            allow_date_window=args.allow_date_window,
            prefer_source=args.prefer_source,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("Merged xG into historical data")
    print(f"Output            : {summary['output']}")
    print(f"Total history rows: {summary['history_total']}")
    print(f"Matches updated   : {summary['matched']}")
    print(f"Still missing xG  : {summary['still_missing_xg']}")


def cmd_compare_models(args) -> None:
    try:
        summary = compare_models(
            input_path=args.input,
            output_dir=args.output_dir,
            test_season=args.test_season,
            target=args.target,
            random_state=args.random_state,
        )
    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print("\nModel comparison complete")
    print(f"Output dir      : {summary['output_dir']}")
    print(f"Best model      : {summary['best_model']} (calibrated={summary['best_calibrated']})")
    print(f"Models evaluated: {summary['models_evaluated']}")
    print(f"Comparison CSV  : {summary['comparison_csv']}")
    print(f"Best model file : {summary['best_model_path']}")


def _pipeline_step(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def cmd_run_pipeline(args) -> None:
    combine_output = Path(args.combine_output)
    fixtures_output = Path(args.fixtures_output)
    model_path = args.model
    predictions_path = Path(args.predictions)
    excel_path = Path(args.excel)

    # Create output directories up front
    for p in [combine_output, fixtures_output, predictions_path, excel_path]:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)

    historical_rows: int | None = None
    fixture_count: int | None = None
    value_bet_count: int | None = None
    no_bet_count: int | None = None
    backtest_csv_path: str | None = None
    backtest_report_path: str | None = None

    # ---- Step A: Download + prepare historical data -------------------------
    if args.skip_download:
        _pipeline_step("Step A: Skipping download (--skip-download)")
        if not combine_output.exists():
            raise SystemExit(
                f"Error: --combine-output '{combine_output}' does not exist.\n"
                "Either run without --skip-download to download fresh data, "
                "or point --combine-output at an existing processed CSV."
            )
        print(f"  Using existing combined dataset: {combine_output}")
    else:
        if not args.leagues:
            raise SystemExit("Error: --leagues is required when not using --skip-download.")
        if not args.seasons:
            raise SystemExit("Error: --seasons is required when not using --skip-download.")
        _pipeline_step("Step A: Downloading and preparing historical football-data.co.uk CSVs")
        dl_args = [
            "download-prepare-football-data",
            "--leagues", *args.leagues,
            "--seasons", *[str(s) for s in args.seasons],
            "--raw-dir", args.raw_dir,
            "--processed-dir", args.processed_dir,
            "--combine-output", str(combine_output),
        ]
        main(dl_args)

    # ---- Step B: Count historical rows ------------------------------------
    try:
        hist_df = pd.read_csv(combine_output)
        historical_rows = len(hist_df)
        print(f"\n  Historical rows available: {historical_rows}")
    except Exception:
        pass

    # ---- Step C: Prepare upcoming fixtures ----------------------------------
    if args.use_existing_fixtures:
        _pipeline_step("Step C: Skipping fixture preparation (--use-existing-fixtures)")
        if not fixtures_output.exists():
            raise SystemExit(
                f"Error: --fixtures-output '{fixtures_output}' does not exist.\n"
                "Either provide a prepared fixtures file or run without --use-existing-fixtures."
            )
        print(f"  Using existing fixtures: {fixtures_output}")
    else:
        _pipeline_step("Step C: Preparing upcoming fixtures")
        if not args.fixtures_raw:
            raise SystemExit(
                "Error: --fixtures-raw is required unless --use-existing-fixtures is set.\n"
                "Provide the path to your raw upcoming fixtures CSV."
            )
        if not Path(args.fixtures_raw).exists():
            raise SystemExit(
                f"Error: Fixtures raw file '{args.fixtures_raw}' not found.\n"
                "Check the path or use --use-existing-fixtures if a prepared file already exists."
            )
        fix_args = [
            "prepare-fixtures",
            "--input", args.fixtures_raw,
            "--output", str(fixtures_output),
            "--format", args.fixtures_format,
        ]
        if args.default_season:
            fix_args += ["--default-season", args.default_season]
        if args.default_league:
            fix_args += ["--default-league", args.default_league]
        main(fix_args)

    # Count fixtures
    try:
        fx_df = pd.read_csv(fixtures_output)
        fixture_count = len(fx_df)
        print(f"  Fixtures ready: {fixture_count}")
    except Exception:
        pass

    # ---- Step C2: Prepare and merge odds (optional) -------------------------
    predict_fixtures_path = fixtures_output  # default: use prepared fixtures
    if getattr(args, "odds_raw", None):
        _pipeline_step("Step C2: Preparing and merging odds")
        odds_clean = Path(args.odds_clean)
        odds_clean.parent.mkdir(parents=True, exist_ok=True)
        try:
            prepare_odds_file(args.odds_raw, str(odds_clean))
        except ValueError as exc:
            raise SystemExit(f"Error preparing odds: {exc}") from exc
        print(f"  Odds prepared: {odds_clean}")

        fx_with_odds = Path(args.fixtures_with_odds)
        fx_with_odds.parent.mkdir(parents=True, exist_ok=True)
        try:
            summary = merge_odds_file(str(fixtures_output), str(odds_clean), str(fx_with_odds))
        except ValueError as exc:
            raise SystemExit(f"Error merging odds: {exc}") from exc
        print(f"  Odds merged  : {fx_with_odds}")
        print(f"  Fixtures updated with odds: {summary['matched']}/{summary['fixtures_total']}")
        predict_fixtures_path = fx_with_odds

    # ---- Step C3: Prepare and merge xG into history (optional) --------------
    training_history_path = combine_output  # default: use combined dataset as-is
    if getattr(args, "xg_raw", None):
        _pipeline_step("Step C3: Preparing and merging xG into historical data")
        xg_clean = Path(args.xg_clean)
        xg_clean.parent.mkdir(parents=True, exist_ok=True)
        try:
            prepare_xg_file(args.xg_raw, str(xg_clean))
        except ValueError as exc:
            raise SystemExit(f"Error preparing xG: {exc}") from exc
        print(f"  xG prepared: {xg_clean}")

        hist_with_xg = Path(args.history_with_xg)
        hist_with_xg.parent.mkdir(parents=True, exist_ok=True)
        try:
            xg_summary = merge_xg_file(str(combine_output), str(xg_clean), str(hist_with_xg))
        except ValueError as exc:
            raise SystemExit(f"Error merging xG: {exc}") from exc
        print(f"  xG merged   : {hist_with_xg}")
        print(f"  History rows updated with xG: {xg_summary['matched']}/{xg_summary['history_total']}")
        print(f"  Still missing xG: {xg_summary['still_missing_xg']}")
        training_history_path = hist_with_xg

    # ---- Step D: Train model -----------------------------------------------
    if getattr(args, "compare_models_flag", False):
        _pipeline_step("Step D: Comparing models and selecting best (--compare-models)")
        if not args.test_season:
            raise SystemExit(
                "Error: --test-season is required when using --compare-models.\n"
                "Provide a season year to use as the held-out test set."
            )
        cmp_dir = Path(getattr(args, "compare_models_dir", "outputs/model_comparison"))
        cmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            cmp_summary = compare_models(
                input_path=str(training_history_path),
                output_dir=str(cmp_dir),
                test_season=args.test_season,
            )
        except ValueError as exc:
            raise SystemExit(f"Error during model comparison: {exc}") from exc
        # Copy best model to the requested model path
        import shutil
        shutil.copy2(cmp_summary["best_model_path"], model_path)
        print(f"  Best model saved to: {model_path}")
    else:
        _pipeline_step("Step D: Training the model")
        train_args = [
            "train",
            "--input", str(training_history_path),
            "--model", model_path,
        ]
        if args.test_season:
            train_args += ["--test-season", str(args.test_season)]
        main(train_args)

    # ---- Step E: Predict upcoming fixtures ----------------------------------
    _pipeline_step("Step E: Predicting upcoming fixtures")
    main([
        "predict-fixtures",
        "--history", str(training_history_path),
        "--fixtures", str(predict_fixtures_path),
        "--model", model_path,
        "--output", str(predictions_path),
        "--min-edge", str(args.min_edge),
        "--max-chaos", str(args.max_chaos),
        "--min-control", str(args.min_control),
    ])
    if not predictions_path.exists():
        raise SystemExit(f"Error: Predictions file was not created at '{predictions_path}'.")

    # Collect value/no-bet counts
    try:
        preds_df = pd.read_csv(predictions_path)
        value_bet_count = int((preds_df["bet_recommendation"] != "No bet").sum())
        no_bet_count = int((preds_df["bet_recommendation"] == "No bet").sum())
    except Exception:
        pass

    # ---- Step F: Export Excel -----------------------------------------------
    _pipeline_step("Step F: Exporting predictions to Excel")
    excel_args = ["export-excel", "--predictions", str(predictions_path), "--output", str(excel_path)]

    # Attach model comparison sheets if compare-models was used
    if getattr(args, "compare_models_flag", False):
        cmp_dir = Path(getattr(args, "compare_models_dir", "outputs/model_comparison"))
        cmp_csv = cmp_dir / "model_comparison.csv"
        cmp_meta = cmp_dir / "best_model_metadata.json"
        if cmp_csv.exists():
            excel_args += ["--model-comparison", str(cmp_csv)]
        if cmp_meta.exists():
            excel_args += ["--model-metadata", str(cmp_meta)]

    # Attach backtest sheets if backtest was run and output exists
    if not args.skip_backtest:
        bt_csv_path = Path(args.backtest_csv)
        if bt_csv_path.exists():
            excel_args += ["--backtest-csv", str(bt_csv_path)]

    main(excel_args)
    if not excel_path.exists():
        raise SystemExit(f"Error: Excel report was not created at '{excel_path}'.")

    # ---- Step G: Backtest ---------------------------------------------------
    if args.skip_backtest:
        _pipeline_step("Step G: Skipping backtest (--skip-backtest)")
    else:
        _pipeline_step("Step G: Running betting backtest")
        bt_csv = Path(args.backtest_csv)
        bt_report = Path(args.backtest_report)
        bt_csv.parent.mkdir(parents=True, exist_ok=True)
        bt_report.parent.mkdir(parents=True, exist_ok=True)
        main([
            "backtest-bets",
            "--history", str(training_history_path),
            "--model", model_path,
            "--output", str(bt_csv),
            "--report", str(bt_report),
            "--min-edge", str(args.min_edge),
            "--max-chaos", str(args.max_chaos),
            "--min-control", str(args.min_control),
        ])
        backtest_csv_path = str(bt_csv)
        backtest_report_path = str(bt_report)

    # ---- Summary -----------------------------------------------------------
    print(f"\n{'='*60}")
    print("  Pipeline complete — summary")
    print(f"{'='*60}")
    print(f"  Combined historical data : {combine_output}")
    if historical_rows is not None:
        print(f"  Historical rows          : {historical_rows}")
    print(f"  Fixtures file            : {fixtures_output}")
    if fixture_count is not None:
        print(f"  Fixtures prepared        : {fixture_count}")
    print(f"  Model                    : {model_path}")
    print(f"  Predictions CSV          : {predictions_path}")
    if value_bet_count is not None:
        print(f"  Value bets               : {value_bet_count}")
    if no_bet_count is not None:
        print(f"  No-bets                  : {no_bet_count}")
    print(f"  Excel report             : {excel_path}")
    if backtest_csv_path:
        print(f"  Backtest CSV             : {backtest_csv_path}")
    if backtest_report_path:
        print(f"  Backtest report          : {backtest_report_path}")


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

    p = sub.add_parser(
        "prepare-fixtures",
        help="Prepare a raw upcoming fixtures CSV into prediction-ready format",
    )
    p.add_argument("--input", required=True, help="Path to the raw fixtures CSV file.")
    p.add_argument("--output", required=True, help="Path where the prepared fixtures CSV is saved.")
    p.add_argument(
        "--format",
        default="auto",
        choices=["auto", "native", "football-data"],
        help="Input format: auto (default), native, or football-data.",
    )
    p.add_argument(
        "--default-season",
        default=None,
        metavar="SEASON",
        help="Season value used when the season column is missing or empty (e.g. 2024).",
    )
    p.add_argument(
        "--default-league",
        default=None,
        metavar="LEAGUE",
        help="League value used when the league column is missing or empty (e.g. Bundesliga).",
    )
    p.set_defaults(func=cmd_prepare_fixtures)

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

    p = sub.add_parser("prepare-odds", help="Prepare a raw odds CSV into a clean normalized format")
    p.add_argument("--input", required=True, help="Path to the raw odds CSV file.")
    p.add_argument("--output", required=True, help="Path where the cleaned odds CSV is saved.")
    p.add_argument("--format", default="auto", choices=["auto", "native"],
                   help="Input format (default: auto).")
    p.set_defaults(func=cmd_prepare_odds)

    p = sub.add_parser("merge-odds-fixtures",
                       help="Merge bookmaker odds into a prepared fixtures CSV")
    p.add_argument("--fixtures", required=True, help="Path to the prepared fixtures CSV.")
    p.add_argument("--odds", required=True, help="Path to the cleaned odds CSV.")
    p.add_argument("--output", required=True, help="Path where the merged fixtures CSV is saved.")
    p.add_argument("--allow-date-window", type=int, default=0, metavar="N",
                   help="Match odds within ±N days of fixture date (default: 0 = exact).")
    p.add_argument("--prefer", default=None, metavar="BOOKMAKER",
                   help="Prefer odds rows where bookmaker equals this value.")
    p.set_defaults(func=cmd_merge_odds_fixtures)

    p = sub.add_parser("prepare-xg", help="Prepare a raw xG CSV into a clean normalized format")
    p.add_argument("--input", required=True, help="Path to the raw xG CSV.")
    p.add_argument("--output", required=True, help="Path where the cleaned xG CSV is saved.")
    p.add_argument("--format", default="auto",
                   choices=["auto", "native", "fbref", "understat"],
                   help="Input format (default: auto).")
    p.set_defaults(func=cmd_prepare_xg)

    p = sub.add_parser("merge-xg-history",
                       help="Merge xG data into a historical matches CSV")
    p.add_argument("--history", required=True, help="Path to the historical matches CSV.")
    p.add_argument("--xg", required=True, help="Path to the cleaned xG CSV.")
    p.add_argument("--output", required=True, help="Path where the enriched history CSV is saved.")
    p.add_argument("--allow-date-window", type=int, default=0, metavar="N",
                   help="Match xG within ±N days of match date (default: 0 = exact).")
    p.add_argument("--prefer-source", default=None, metavar="SOURCE",
                   help="Prefer xG rows where source equals this value.")
    p.set_defaults(func=cmd_merge_xg_history)

    p = sub.add_parser(
        "compare-models",
        help="Train and compare multiple model types; save the best model automatically",
    )
    p.add_argument("--input", required=True, metavar="FILE",
                   help="Path to the processed historical matches CSV.")
    p.add_argument("--output-dir", required=True, metavar="DIR",
                   help="Directory where comparison results and best model are saved.")
    p.add_argument("--test-season", required=True, type=int, metavar="YEAR",
                   help="Season year to hold out for evaluation (e.g. 2023).")
    p.add_argument("--target", default="result", metavar="COLUMN",
                   help="Target column name (default: result).")
    p.add_argument("--random-state", type=int, default=42, metavar="N",
                   help="Random seed for reproducibility (default: 42).")
    p.set_defaults(func=cmd_compare_models)

    p = sub.add_parser("export-excel", help="Create an Excel report from prediction CSV output")
    p.add_argument("--predictions", required=True, metavar="FILE",
                   help="Path to the predictions CSV.")
    p.add_argument("--output", required=True, metavar="FILE",
                   help="Path where the Excel file is saved.")
    p.add_argument("--model-comparison", default=None, dest="model_comparison", metavar="FILE",
                   help="Optional path to model_comparison.csv for dashboard sheets.")
    p.add_argument("--model-metadata", default=None, dest="model_metadata", metavar="FILE",
                   help="Optional path to best_model_metadata.json for Best Model / Feature sheets.")
    p.add_argument("--backtest-csv", default=None, dest="backtest_csv_in", metavar="FILE",
                   help="Optional path to backtest_bets.csv for Backtest sheets.")
    p.add_argument("--backtest-report", default=None, dest="backtest_report_in", metavar="FILE",
                   help="Optional path to backtest_report.md (reserved for future use).")
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

    p = sub.add_parser(
        "run-pipeline",
        help="Run the full end-to-end pipeline: download → prepare → train → predict → Excel → backtest",
    )
    p.add_argument("--leagues", nargs="+", default=None, metavar="CODE",
                   help="League codes for download (not required with --skip-download).")
    p.add_argument("--seasons", nargs="+", type=int, default=None, metavar="YEAR",
                   help="Season start years for download (not required with --skip-download).")
    p.add_argument("--raw-dir", default="data/raw", metavar="DIR",
                   help="Directory for raw downloaded CSVs (default: data/raw).")
    p.add_argument("--processed-dir", default="data/processed", metavar="DIR",
                   help="Directory for processed CSVs (default: data/processed).")
    p.add_argument("--combine-output", required=True, metavar="FILE",
                   help="Path to the combined processed training CSV.")
    p.add_argument("--fixtures-raw", default=None, metavar="FILE",
                   help="Path to the raw upcoming fixtures CSV (not required with --use-existing-fixtures).")
    p.add_argument("--fixtures-output", required=True, metavar="FILE",
                   help="Path where the prepared fixtures CSV is saved/read.")
    p.add_argument("--fixtures-format", default="auto",
                   choices=["auto", "native", "football-data"],
                   help="Fixture input format (default: auto).")
    p.add_argument("--default-season", default=None, metavar="SEASON",
                   help="Default season value for fixtures (e.g. 2024).")
    p.add_argument("--default-league", default=None, metavar="LEAGUE",
                   help="Default league value for fixtures.")
    p.add_argument("--model", required=True, metavar="FILE",
                   help="Path where the trained model is saved.")
    p.add_argument("--predictions", required=True, metavar="FILE",
                   help="Path where the predictions CSV is saved.")
    p.add_argument("--excel", required=True, metavar="FILE",
                   help="Path where the Excel report is saved.")
    p.add_argument("--backtest-csv", default="outputs/backtest_bets.csv", metavar="FILE",
                   help="Path where the backtest CSV is saved (default: outputs/backtest_bets.csv).")
    p.add_argument("--backtest-report", default="outputs/backtest_report.md", metavar="FILE",
                   help="Path where the backtest report is saved (default: outputs/backtest_report.md).")
    p.add_argument("--test-season", type=int, default=None,
                   help="Season year to hold out for model evaluation.")
    p.add_argument("--min-edge", type=float, default=0.03,
                   help="Minimum edge for value bet recommendation (default: 0.03).")
    p.add_argument("--max-chaos", type=float, default=7.0,
                   help="Maximum chaos score to allow a bet (default: 7.0).")
    p.add_argument("--min-control", type=float, default=7.0,
                   help="Minimum control score to allow a bet (default: 7.0).")
    p.add_argument("--skip-download", action="store_true",
                   help="Skip downloading historical data; assume --combine-output already exists.")
    p.add_argument("--skip-backtest", action="store_true",
                   help="Skip the betting backtest step.")
    p.add_argument("--use-existing-fixtures", action="store_true",
                   help="Skip prepare-fixtures; assume --fixtures-output already exists.")
    p.add_argument("--odds-raw", default=None, metavar="FILE",
                   help="Optional path to a raw odds CSV. If provided, odds are prepared and merged into fixtures.")
    p.add_argument("--odds-clean", default="data/processed/odds_clean.csv", metavar="FILE",
                   help="Path where the cleaned odds CSV is saved (default: data/processed/odds_clean.csv).")
    p.add_argument("--fixtures-with-odds", default="data/upcoming_fixtures_with_odds.csv", metavar="FILE",
                   help="Path where fixtures merged with odds are saved.")
    p.add_argument("--xg-raw", default=None, metavar="FILE",
                   help="Optional path to a raw xG CSV. If provided, xG is prepared and merged into history before training.")
    p.add_argument("--xg-clean", default="data/processed/xg_clean.csv", metavar="FILE",
                   help="Path where the cleaned xG CSV is saved (default: data/processed/xg_clean.csv).")
    p.add_argument("--history-with-xg", default="data/processed/combined_football_data_with_xg.csv", metavar="FILE",
                   help="Path where history enriched with xG is saved.")
    p.add_argument("--compare-models", dest="compare_models_flag", action="store_true",
                   help="Run model comparison instead of single-model training. Requires --test-season.")
    p.add_argument("--compare-models-dir", dest="compare_models_dir",
                   default="outputs/model_comparison", metavar="DIR",
                   help="Directory where model comparison outputs are saved (default: outputs/model_comparison).")
    p.set_defaults(func=cmd_run_pipeline)

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
