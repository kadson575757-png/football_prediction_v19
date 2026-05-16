from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from .data import load_matches
from .features import build_features
from .model import CLASS_ORDER, _align_proba, _log_loss_multiclass, train_from_feature_table
from .rules_v19 import assess_prediction


def run_backtest(matches: pd.DataFrame, test_season: int, tune: bool = False) -> dict[str, Any]:
    table = build_features(matches)
    model, metrics, cols = train_from_feature_table(table, test_season=test_season, tune=tune)
    test = table[table["season_start"] == test_season].copy()
    if test.empty:
        raise ValueError(f"No test rows for season_start={test_season}")

    X = test[cols]
    y = test["result"]
    pred = model.predict(X)
    proba = _align_proba(model, model.predict_proba(X))
    test["pred"] = pred
    test["prob_home"] = proba["H"].to_numpy()
    test["prob_draw"] = proba["D"].to_numpy()
    test["prob_away"] = proba["A"].to_numpy()

    rule_rows = []
    for idx, row in test.iterrows():
        probs = {"H": row["prob_home"], "D": row["prob_draw"], "A": row["prob_away"]}
        assessment = assess_prediction(row, probs)
        primary = assessment["recommendations"][0] if assessment["recommendations"] else None
        rule_rows.append({
            "index": idx,
            "control_model_score": assessment["control_model_score"],
            "chaos_score": assessment["chaos_score"],
            "primary_market": primary["market"] if primary else None,
            "primary_selection": primary["selection"] if primary else None,
            "no_bet_count": len(assessment["no_bets"]),
        })
    rules_df = pd.DataFrame(rule_rows).set_index("index")
    test = test.join(rules_df)

    out: dict[str, Any] = dict(metrics)
    out["test_accuracy_checked"] = float(accuracy_score(y, pred))
    out["test_log_loss_checked"] = _log_loss_multiclass(y, proba[CLASS_ORDER].to_numpy(), CLASS_ORDER)
    out["avg_control_score"] = float(test["control_model_score"].mean())
    out["avg_chaos_score"] = float(test["chaos_score"].mean())
    out["recommended_rows"] = int(test["primary_market"].notna().sum())
    out["no_bet_rows"] = int(test["primary_market"].isna().sum())

    # Optional simple value ROI for 1X2 if odds are provided.
    if {"odds_home", "odds_draw", "odds_away"}.issubset(test.columns):
        stakes = []
        returns = []
        for _, row in test.iterrows():
            if row.get("primary_market") != "1X2":
                continue
            sel = row.get("primary_selection")
            label = {"Home": "H", "Draw": "D", "Away": "A"}.get(sel)
            if label is None:
                continue
            odds_col = {"H": "odds_home", "D": "odds_draw", "A": "odds_away"}[label]
            odds = row.get(odds_col, np.nan)
            if pd.isna(odds):
                continue
            stakes.append(1.0)
            returns.append(float(odds) if row["result"] == label else 0.0)
        if stakes:
            profit = sum(returns) - sum(stakes)
            out["one_x_two_value_bets"] = int(len(stakes))
            out["one_x_two_roi"] = float(profit / sum(stakes))
    return out
