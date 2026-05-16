from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

PREDICTION_COLUMNS = [
    "date",
    "league",
    "home_team",
    "away_team",
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
    "control_score",
    "chaos_score",
    "tdi_home",
    "tdi_away",
    "no_bet_reasons",
    "v19_flags",
]

PERCENT_COLUMNS = {
    "prob_home",
    "prob_draw",
    "prob_away",
    "fair_home",
    "fair_draw",
    "fair_away",
    "edge_home",
    "edge_draw",
    "edge_away",
    "value_edge",
}

ODDS_COLUMNS = {"odds_home", "odds_draw", "odds_away"}


def _ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[list(columns)]


def _split_reasons(series: pd.Series) -> list[str]:
    reasons: list[str] = []
    for text in series.fillna(""):
        for reason in str(text).split(" | "):
            reason = reason.strip()
            if reason:
                reasons.append(reason)
    return reasons


def _write_rows(ws, rows: list[list[object]]) -> None:
    for row in rows:
        ws.append(row)


def _format_sheet(ws, percent_columns: set[str] | None = None, odds_columns: set[str] | None = None) -> None:
    percent_columns = percent_columns or set()
    odds_columns = odds_columns or set()
    if ws.max_row == 0:
        return
    header_fill = PatternFill("solid", fgColor="1F4E79")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    headers = [cell.value for cell in ws[1]]
    for idx, header in enumerate(headers, start=1):
        letter = get_column_letter(idx)
        width = min(max(len(str(header or "")) + 2, 12), 38)
        for cell in ws[letter][1:]:
            width = min(max(width, len(str(cell.value or "")) + 2), 48)
        ws.column_dimensions[letter].width = width
        if header in percent_columns:
            for cell in ws[letter][1:]:
                cell.number_format = "0.0%"
        if header in odds_columns:
            for cell in ws[letter][1:]:
                cell.number_format = "0.00"


def _add_dataframe_sheet(wb: Workbook, name: str, df: pd.DataFrame) -> None:
    ws = wb.create_sheet(name)
    rows = [list(df.columns)] + df.where(pd.notna(df), None).values.tolist()
    _write_rows(ws, rows)
    _format_sheet(ws, PERCENT_COLUMNS, ODDS_COLUMNS)


def _summary_rows(df: pd.DataFrame) -> list[list[object]]:
    recommended = df[df["bet_recommendation"].fillna("").str.lower() != "no bet"]
    no_bets = df[df["bet_recommendation"].fillna("").str.lower() == "no bet"]
    avg_edge = recommended["value_edge"].mean() if not recommended.empty else 0
    rows: list[list[object]] = [
        ["Metric", "Value"],
        ["Total fixtures", len(df)],
        ["Recommended bets", len(recommended)],
        ["No-bets", len(no_bets)],
        ["Average edge", float(avg_edge) if pd.notna(avg_edge) else 0],
        ["Average control score", float(df["control_score"].mean()) if "control_score" in df else 0],
        ["Average chaos score", float(df["chaos_score"].mean()) if "chaos_score" in df else 0],
        [],
        ["Top 10 Value Picks", ""],
        ["Rank", "Match", "Pick", "Value Edge", "Recommendation"],
    ]
    top = recommended.sort_values("value_edge", ascending=False).head(10)
    for rank, (_, row) in enumerate(top.iterrows(), start=1):
        rows.append([
            rank,
            f"{row.get('home_team', '')} vs {row.get('away_team', '')}",
            row.get("value_pick", ""),
            row.get("value_edge", 0),
            row.get("bet_recommendation", ""),
        ])
    rows.extend([[], ["Most Common No-Bet Reasons", "Count"]])
    for reason, count in Counter(_split_reasons(df["no_bet_reasons"])).most_common(10):
        rows.append([reason, count])
    return rows


def create_predictions_excel_report(predictions_path: str | Path, output_path: str | Path) -> Path:
    predictions_path = Path(predictions_path)
    output_path = Path(output_path)
    df = pd.read_csv(predictions_path)
    data = _ensure_columns(df, PREDICTION_COLUMNS)

    wb = Workbook()
    summary = wb.active
    summary.title = "Summary"
    _write_rows(summary, _summary_rows(data))
    _format_sheet(summary, {"Value Edge", "Average edge"}, set())
    summary["A1"].font = Font(bold=True, color="FFFFFF")
    summary["B1"].font = Font(bold=True, color="FFFFFF")

    _add_dataframe_sheet(wb, "Predictions", data)
    value_bets = data[data["bet_recommendation"].fillna("").str.lower() != "no bet"].sort_values("value_edge", ascending=False)
    _add_dataframe_sheet(wb, "Value Bets", value_bets)
    no_bets = data[data["bet_recommendation"].fillna("").str.lower() == "no bet"]
    _add_dataframe_sheet(wb, "No Bets", no_bets)
    high_chaos = data.sort_values("chaos_score", ascending=False)
    _add_dataframe_sheet(wb, "High Chaos", high_chaos)
    flags = data[data["v19_flags"].fillna("").astype(str).str.len() > 0]
    _add_dataframe_sheet(wb, "v19 Flags", flags)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
