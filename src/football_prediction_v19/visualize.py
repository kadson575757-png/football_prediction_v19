from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_probability_bar(prediction: dict, output: str | Path | None = None):
    probs = prediction["probabilities"]
    labels = ["Home", "Draw", "Away"]
    values = [probs["home"], probs["draw"], probs["away"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Probability")
    ax.set_title("1X2 Model Probability")
    for i, v in enumerate(values):
        ax.text(i, v + 0.02, f"{v:.1%}", ha="center")
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=160, bbox_inches="tight")
    return fig, ax


def plot_xg_flow_from_shots(shots: pd.DataFrame, output: str | Path | None = None):
    """Simple xG flow for event data with columns: team, minute, xg.

    This is intentionally generic. You can map StatsBomb/Understat/FotMob event data into
    this shape and reuse the function.
    """
    required = {"team", "minute", "xg"}
    missing = required - set(shots.columns)
    if missing:
        raise ValueError(f"Missing columns for xG flow: {missing}")
    data = shots.sort_values(["minute"]).copy()
    data["cum_xg"] = data.groupby("team")["xg"].cumsum()
    fig, ax = plt.subplots(figsize=(9, 4))
    for team, g in data.groupby("team"):
        ax.step(g["minute"], g["cum_xg"], where="post", label=team)
    ax.set_xlabel("Minute")
    ax.set_ylabel("Cumulative xG")
    ax.legend()
    ax.set_title("xG Flow")
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=160, bbox_inches="tight")
    return fig, ax
