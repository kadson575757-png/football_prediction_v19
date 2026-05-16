"""Model comparison and probability calibration workflow.

Trains multiple scikit-learn classifiers, optionally calibrates their probabilities,
evaluates them on a time-based test split, and saves the best model along with a
comparison report.
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, log_loss
from sklearn.pipeline import Pipeline

from .data import load_matches
from .features import build_features
from .model import (
    CLASS_ORDER,
    _align_proba,
    _brier_multiclass,
    _log_loss_multiclass,
    build_pipeline,
    feature_columns,
)

_MODEL_NAMES = ["logistic_regression", "random_forest", "gradient_boosting"]

_OVERCONFIDENCE_THRESHOLD = 0.75  # warn if avg confidence exceeds this


def _brier_score_binary(y_true: pd.Series, proba: np.ndarray, classes: list[str]) -> float:
    """Mean per-class binary Brier score (equivalent to multiclass Brier / n_classes)."""
    return _brier_multiclass(y_true, proba, classes)


def _avg_confidence(proba: np.ndarray) -> float:
    return float(np.mean(np.max(proba, axis=1)))


def _avg_correct_confidence(y_true: pd.Series, proba: np.ndarray, classes: list[str]) -> float:
    idx = {c: i for i, c in enumerate(classes)}
    scores = []
    for r, label in enumerate(y_true):
        if label in idx:
            scores.append(proba[r, idx[label]])
    return float(np.mean(scores)) if scores else float("nan")


def _try_calibrate(
    unfitted_model: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> Pipeline | None:
    """Try to calibrate a model using cross-validated isotonic calibration.

    Uses cv=3 (or fewer if data is small) so calibration is independent of the
    fitted model we evaluated. Returns None if calibration is not possible.
    """
    n_classes = len(np.unique(y_train))
    n_samples = len(y_train)

    if n_samples < 30 or n_classes < 2:
        warnings.warn(
            f"Calibration skipped: too few samples ({n_samples}) or classes ({n_classes}).",
            stacklevel=2,
        )
        return None

    cv = min(3, n_samples // 10) if n_samples < 150 else 3
    if cv < 2:
        warnings.warn(
            f"Calibration skipped: cv={cv} is too small (need at least 2).",
            stacklevel=2,
        )
        return None

    try:
        calibrated = CalibratedClassifierCV(unfitted_model, cv=cv, method="isotonic")
        calibrated.fit(X_train, y_train)
        return calibrated  # type: ignore[return-value]
    except Exception as exc:
        warnings.warn(f"Calibration failed: {exc}", stacklevel=2)
        return None


def _evaluate_model(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    cols: list[str],
    classes: list[str],
) -> dict[str, Any]:
    """Compute all evaluation metrics for a fitted model."""
    X = X_test.reindex(columns=cols)
    pred = model.predict(X)
    raw_proba = model.predict_proba(X)

    # Align probability columns to CLASS_ORDER
    try:
        # For Pipeline with named 'classifier' step
        clf_classes = list(model.named_steps["classifier"].classes_)
    except (AttributeError, KeyError):
        try:
            # For CalibratedClassifierCV wrapping a Pipeline
            clf_classes = list(model.classes_)
        except AttributeError:
            clf_classes = classes

    proba_df = pd.DataFrame(raw_proba, columns=clf_classes)
    for c in CLASS_ORDER:
        if c not in proba_df.columns:
            proba_df[c] = 0.0
    proba = proba_df[CLASS_ORDER].to_numpy()

    acc = float(accuracy_score(y_test, pred))
    try:
        bal_acc = float(balanced_accuracy_score(y_test, pred))
    except Exception:
        bal_acc = float("nan")

    ll = _log_loss_multiclass(y_test, proba, CLASS_ORDER)
    brier = _brier_multiclass(y_test, proba, CLASS_ORDER)
    avg_conf = _avg_confidence(proba)
    avg_correct = _avg_correct_confidence(y_test, proba, CLASS_ORDER)

    model_warnings: list[str] = []
    if avg_conf > _OVERCONFIDENCE_THRESHOLD:
        model_warnings.append(
            f"Overconfident: avg confidence {avg_conf:.2f} > {_OVERCONFIDENCE_THRESHOLD:.2f}"
        )

    return {
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "log_loss": ll,
        "brier_score": brier,
        "avg_confidence": avg_conf,
        "avg_correct_confidence": avg_correct,
        "warnings": "; ".join(model_warnings) if model_warnings else "",
    }


def compare_models(
    input_path: str,
    output_dir: str,
    test_season: int | str,
    target: str = "result",
    random_state: int = 42,
) -> dict[str, Any]:
    """Train, calibrate, and compare multiple classifier families.

    Args:
        input_path: Path to the processed historical matches CSV.
        output_dir: Directory where all output files are saved.
        test_season: Season year to hold out for evaluation. Must exist in the data.
        target: Target column name (default: "result").
        random_state: Random seed for reproducibility.

    Returns:
        Summary dict with path info and best model name.

    Raises:
        ValueError: If the input file is missing, empty, or test_season is not in the data.
    """
    p = Path(input_path)
    if not p.exists():
        raise ValueError(
            f"Input file '{input_path}' not found. "
            "Check the path and try again."
        )

    matches = load_matches(p)
    if matches.empty:
        raise ValueError("Input file is empty. Add historical match data before running compare-models.")

    table = build_features(matches, min_history=1)
    table = table.dropna(subset=[target]).copy()

    test_season = int(test_season)
    available_seasons = sorted(table["season_start"].dropna().unique())

    if test_season not in available_seasons:
        raise ValueError(
            f"Test season {test_season} not found in the data. "
            f"Available seasons: {[int(s) for s in available_seasons]}. "
            "Make sure your training data covers this season."
        )

    train_table = table[table["season_start"] < test_season]
    test_table = table[table["season_start"] == test_season]

    if train_table.empty:
        raise ValueError(
            f"No training data found before season {test_season}. "
            "Use an earlier test season or add more historical data."
        )
    if test_table.empty:
        raise ValueError(
            f"No test data found for season {test_season}. "
            "The test season must have at least one match in the data."
        )

    cols = [c for c in feature_columns(table) if not table[c].isna().all()]
    X_train = train_table[cols]
    y_train = train_table[target]
    X_test = test_table[cols]
    y_test = test_table[target]

    classes = sorted(table[target].unique().tolist())
    train_rows = len(train_table)
    test_rows = len(test_table)
    feature_count = len(cols)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    all_models: list[tuple[str, bool, Any, dict[str, Any]]] = []

    for model_name in _MODEL_NAMES:
        print(f"  Training {model_name}...")
        pipeline = build_pipeline(model_name=model_name, random_state=random_state)
        pipeline.fit(X_train, y_train)

        # Uncalibrated evaluation
        metrics_unc = _evaluate_model(pipeline, X_test, y_test, cols, classes)
        row_unc: dict[str, Any] = {
            "model_name": model_name,
            "calibrated": False,
            "train_rows": train_rows,
            "test_rows": test_rows,
            "feature_count": feature_count,
            "selected_as_best": False,
            **metrics_unc,
        }
        rows.append(row_unc)
        all_models.append((model_name, False, pipeline, metrics_unc))

        # Calibrated evaluation — use a fresh unfitted pipeline so cv-calibration
        # doesn't leak information from the fitted model into the calibration folds.
        print(f"  Calibrating {model_name}...")
        fresh_pipeline = build_pipeline(model_name=model_name, random_state=random_state)
        calibrated_model = _try_calibrate(fresh_pipeline, X_train, y_train)
        if calibrated_model is not None:
            metrics_cal = _evaluate_model(calibrated_model, X_test, y_test, cols, classes)
            row_cal: dict[str, Any] = {
                "model_name": model_name,
                "calibrated": True,
                "train_rows": train_rows,
                "test_rows": test_rows,
                "feature_count": feature_count,
                "selected_as_best": False,
                **metrics_cal,
            }
            rows.append(row_cal)
            all_models.append((model_name, True, calibrated_model, metrics_cal))

    # Select best model: lowest log_loss, then lowest brier_score
    best_idx = min(
        range(len(all_models)),
        key=lambda i: (
            all_models[i][3].get("log_loss", float("inf")),
            all_models[i][3].get("brier_score", float("inf")),
        ),
    )
    best_name, best_calibrated, best_model, best_metrics = all_models[best_idx]

    # Mark best in comparison table
    rows[best_idx]["selected_as_best"] = True

    # Save comparison CSV
    comparison_df = pd.DataFrame(rows, columns=[
        "model_name", "calibrated", "accuracy", "balanced_accuracy",
        "log_loss", "brier_score", "avg_confidence", "avg_correct_confidence",
        "train_rows", "test_rows", "feature_count", "selected_as_best", "warnings",
    ])
    csv_path = out_dir / "model_comparison.csv"
    comparison_df.to_csv(csv_path, index=False)

    # Save comparison report
    report_path = out_dir / "model_comparison_report.md"
    _write_report(comparison_df, report_path, test_season, best_name, best_calibrated)

    # Save best model
    best_model_path = out_dir / "best_model.joblib"
    # Wrap into the standard bundle format used by predict_feature_rows / load_model
    joblib.dump({
        "model": best_model,
        "feature_cols": cols,
        "metrics": best_metrics,
    }, best_model_path)

    # Save feature columns
    feature_json_path = out_dir / "feature_columns.json"
    feature_json_path.write_text(json.dumps(cols, indent=2, ensure_ascii=False))

    # Save metadata
    metadata: dict[str, Any] = {
        "model_name": best_name,
        "calibrated": best_calibrated,
        "test_season": test_season,
        "selected_metric": "log_loss",
        "accuracy": best_metrics.get("accuracy"),
        "log_loss": best_metrics.get("log_loss"),
        "brier_score": best_metrics.get("brier_score"),
        "feature_columns": cols,
        "training_rows": train_rows,
        "test_rows": test_rows,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = out_dir / "best_model_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str))

    print(f"\n  Best model: {best_name} (calibrated={best_calibrated})")
    print(f"  Log loss  : {best_metrics.get('log_loss', 'n/a'):.4f}")
    print(f"  Accuracy  : {best_metrics.get('accuracy', 'n/a'):.4f}")

    return {
        "output_dir": str(out_dir),
        "best_model": best_name,
        "best_calibrated": best_calibrated,
        "best_model_path": str(best_model_path),
        "comparison_csv": str(csv_path),
        "comparison_report": str(report_path),
        "feature_json": str(feature_json_path),
        "metadata_json": str(meta_path),
        "models_evaluated": len(all_models),
    }


def _write_report(
    df: pd.DataFrame,
    path: Path,
    test_season: int,
    best_name: str,
    best_calibrated: bool,
) -> None:
    lines = [
        "# Model Comparison Report",
        "",
        f"Test season: {test_season}",
        f"Best model: {best_name} (calibrated={best_calibrated})",
        "",
        "**Note:** Better backtest metrics do not guarantee future betting profit. "
        "This report shows historical model performance only.",
        "",
        "## Results",
        "",
    ]
    lines.append("| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |")
    lines.append("|---|---|---|---|---|---|---|")
    for _, row in df.iterrows():
        mark = "✓" if row["selected_as_best"] else ""
        ll = f"{row['log_loss']:.4f}" if pd.notna(row["log_loss"]) else "n/a"
        bs = f"{row['brier_score']:.4f}" if pd.notna(row["brier_score"]) else "n/a"
        acc = f"{row['accuracy']:.4f}" if pd.notna(row["accuracy"]) else "n/a"
        conf = f"{row['avg_confidence']:.4f}" if pd.notna(row["avg_confidence"]) else "n/a"
        lines.append(
            f"| {row['model_name']} | {row['calibrated']} | {acc} | {ll} | {bs} | {conf} | {mark} |"
        )

    warnings_rows = df[df["warnings"].str.len() > 0]
    if not warnings_rows.empty:
        lines += ["", "## Warnings", ""]
        for _, row in warnings_rows.iterrows():
            lines.append(f"- **{row['model_name']}** (calibrated={row['calibrated']}): {row['warnings']}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
