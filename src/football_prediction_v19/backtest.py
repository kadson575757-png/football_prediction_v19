from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from .data import load_matches
from .features import build_features
from .model import CLASS_ORDER, _align_proba, _brier_multiclass, _log_loss_multiclass, predict_feature_rows, train_from_feature_table
from .odds import grade_flat_stake_bet, value_recommendation
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


BET_BACKTEST_COLUMNS = [
    "date",
    "league",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result",
    "prob_home",
    "prob_draw",
    "prob_away",
    "odds_home",
    "odds_draw",
    "odds_away",
    "fair_home",
    "fair_draw",
    "fair_away",
    "edge_home",
    "edge_draw",
    "edge_away",
    "value_pick",
    "value_edge",
    "bet_recommendation",
    "no_bet_reasons",
    "stake",
    "profit",
    "cumulative_profit",
]


def _bet_odds(row: pd.Series, value_pick: str) -> float | None:
    col = {"Home": "odds_home", "Draw": "odds_draw", "Away": "odds_away"}.get(value_pick)
    if col is None:
        return None
    odds = row.get(col)
    if pd.isna(odds):
        return None
    return float(odds)


def _format_money(value: float) -> str:
    return f"{value:.2f}"


def _performance_table(df: pd.DataFrame, group_col: str) -> str:
    bet_rows = df[df["stake"] > 0]
    if bet_rows.empty or group_col not in bet_rows.columns:
        return "No bets placed."
    lines = ["| Group | Bets | Profit | ROI | Hit Rate |", "|---|---:|---:|---:|---:|"]
    for group, part in bet_rows.groupby(group_col, dropna=False):
        bets = int(len(part))
        profit = float(part["profit"].sum())
        roi = profit / float(part["stake"].sum()) if part["stake"].sum() else 0.0
        hit_rate = float((part["profit"] > 0).mean()) if bets else 0.0
        lines.append(f"| {group} | {bets} | {_format_money(profit)} | {roi:.2%} | {hit_rate:.2%} |")
    return "\n".join(lines)


def _top_bets(df: pd.DataFrame, largest: bool) -> str:
    bet_rows = df[df["stake"] > 0].sort_values("profit", ascending=not largest).head(5)
    if bet_rows.empty:
        return "No bets placed."
    lines = ["| Date | Match | Pick | Odds | Profit |", "|---|---|---|---:|---:|"]
    for _, row in bet_rows.iterrows():
        odds = _bet_odds(row, row["value_pick"])
        match = f"{row['home_team']} vs {row['away_team']}"
        lines.append(f"| {row['date']} | {match} | {row['value_pick']} | {odds:.2f} | {_format_money(row['profit'])} |")
    return "\n".join(lines)


def _common_no_bets(df: pd.DataFrame) -> str:
    reasons: dict[str, int] = {}
    for text in df["no_bet_reasons"].fillna(""):
        for reason in str(text).split(" | "):
            reason = reason.strip()
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
    if not reasons:
        return "No no-bet reasons recorded."
    lines = ["| Reason | Count |", "|---|---:|"]
    for reason, count in sorted(reasons.items(), key=lambda item: item[1], reverse=True)[:10]:
        lines.append(f"| {reason} | {count} |")
    return "\n".join(lines)


def _calibration_metrics(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "brier_score": float("nan"),
            "log_loss": float("nan"),
            "avg_winning_pick_probability": float("nan"),
            "overconfidence_warning": "No rows to evaluate.",
        }
    proba = df[["prob_home", "prob_draw", "prob_away"]].to_numpy()
    brier = _brier_multiclass(df["result"], proba, CLASS_ORDER)
    log_loss = _log_loss_multiclass(df["result"], proba, CLASS_ORDER)
    winning_probs = []
    for _, row in df.iterrows():
        key = {"H": "prob_home", "D": "prob_draw", "A": "prob_away"}[row["result"]]
        winning_probs.append(float(row[key]))
    avg_winner = float(np.mean(winning_probs)) if winning_probs else float("nan")
    high_conf = df[["prob_home", "prob_draw", "prob_away"]].max(axis=1) >= 0.60
    high_conf_rows = df[high_conf]
    warning = "No overconfidence warning."
    if not high_conf_rows.empty:
        predicted = high_conf_rows[["prob_home", "prob_draw", "prob_away"]].idxmax(axis=1).map({
            "prob_home": "H",
            "prob_draw": "D",
            "prob_away": "A",
        })
        accuracy = float((predicted.to_numpy() == high_conf_rows["result"].to_numpy()).mean())
        avg_conf = float(high_conf_rows[["prob_home", "prob_draw", "prob_away"]].max(axis=1).mean())
        if avg_conf - accuracy > 0.10:
            warning = f"Warning: high-confidence picks look overconfident. Avg confidence {avg_conf:.2%}, hit rate {accuracy:.2%}."
    return {
        "brier_score": brier,
        "log_loss": log_loss,
        "avg_winning_pick_probability": avg_winner,
        "overconfidence_warning": warning,
    }


def build_betting_report(df: pd.DataFrame) -> str:
    total_matches = int(len(df))
    total_bets = int((df["stake"] > 0).sum())
    no_bet_count = int(total_matches - total_bets)
    total_staked = float(df["stake"].sum())
    total_profit = float(df["profit"].sum())
    hit_rate = float((df.loc[df["stake"] > 0, "profit"] > 0).mean()) if total_bets else 0.0
    roi = total_profit / total_staked if total_staked else 0.0
    avg_edge = float(df.loc[df["stake"] > 0, "value_edge"].mean()) if total_bets else 0.0
    calibration = _calibration_metrics(df)
    lines = [
        "# Betting Backtest Report",
        "",
        "## Summary",
        "",
        f"- Total matches: {total_matches}",
        f"- Total bets: {total_bets}",
        f"- No-bet count: {no_bet_count}",
        f"- Hit rate: {hit_rate:.2%}",
        f"- Total profit: {_format_money(total_profit)} units",
        f"- ROI: {roi:.2%}",
        f"- Yield: {roi:.2%}",
        f"- Average edge: {avg_edge:.2%}",
        "",
        "## Calibration",
        "",
        f"- Brier score: {calibration['brier_score']:.4f}",
        f"- Log loss: {calibration['log_loss']:.4f}",
        f"- Average predicted probability for winning picks: {calibration['avg_winning_pick_probability']:.2%}",
        f"- {calibration['overconfidence_warning']}",
        "",
        "## Performance By Pick Type",
        "",
        _performance_table(df, "value_pick"),
        "",
        "## Performance By League",
        "",
        _performance_table(df, "league"),
        "",
        "## Biggest Winning Bets",
        "",
        _top_bets(df, largest=True),
        "",
        "## Biggest Losing Bets",
        "",
        _top_bets(df, largest=False),
        "",
        "## Most Common No-Bet Reasons",
        "",
        _common_no_bets(df),
        "",
        "> Backtests are diagnostics, not guarantees. Future matches can behave differently.",
    ]
    return "\n".join(lines)


def run_bet_backtest(
    matches: pd.DataFrame,
    model_bundle: dict[str, Any],
    min_edge: float = 0.03,
    max_chaos: float = 7.0,
    min_control: float = 7.0,
) -> pd.DataFrame:
    table = build_features(matches).sort_values("date").reset_index(drop=True)
    if table.empty:
        raise ValueError("No historical feature rows available for betting backtest.")

    pred_rows = predict_feature_rows(model_bundle, table)
    rows = []
    cumulative_profit = 0.0
    for _, row in pred_rows.iterrows():
        probs = {"H": row["prob_home"], "D": row["prob_draw"], "A": row["prob_away"]}
        assessment = assess_prediction(row, probs)
        value = value_recommendation(
            row.get("odds_home"),
            row.get("odds_draw"),
            row.get("odds_away"),
            probs,
            assessment,
            min_edge,
            max_chaos,
            min_control,
        )
        odds = _bet_odds(row, value["value_pick"])
        stake, profit = grade_flat_stake_bet(str(value["value_pick"]), str(row["result"]), odds)
        cumulative_profit = round(cumulative_profit + profit, 4)
        rows.append({
            "date": pd.to_datetime(row["date"]).date().isoformat(),
            "league": row.get("league", "Unknown"),
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_goals": row["home_goals"],
            "away_goals": row["away_goals"],
            "result": row["result"],
            "prob_home": round(float(row["prob_home"]), 4),
            "prob_draw": round(float(row["prob_draw"]), 4),
            "prob_away": round(float(row["prob_away"]), 4),
            "odds_home": value["odds_home"],
            "odds_draw": value["odds_draw"],
            "odds_away": value["odds_away"],
            "fair_home": value["fair_home"],
            "fair_draw": value["fair_draw"],
            "fair_away": value["fair_away"],
            "edge_home": value["edge_home"],
            "edge_draw": value["edge_draw"],
            "edge_away": value["edge_away"],
            "value_pick": value["value_pick"],
            "value_edge": value["value_edge"],
            "bet_recommendation": value["bet_recommendation"],
            "no_bet_reasons": " | ".join(value["no_bet_reasons"]),
            "stake": stake,
            "profit": profit,
            "cumulative_profit": cumulative_profit,
        })
    return pd.DataFrame(rows, columns=BET_BACKTEST_COLUMNS)
