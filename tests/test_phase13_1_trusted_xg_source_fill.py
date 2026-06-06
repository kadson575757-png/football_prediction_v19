# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.manual_xg_acceptance import evaluate_manual_xg_acceptance
from football_prediction_v19.importers.trusted_xg_source import (
    FBREF_LONG_SCHEMA,
    MATCH_PAIR_SCHEMA,
    UNDERSTAT_PAIR_SCHEMA,
    build_filled_manual_xg_preview,
    join_trusted_xg_to_manual_template,
    normalize_trusted_xg_source,
)


ROOT = Path(__file__).resolve().parents[1]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "home_team": ["Team A", "Team C"],
        "away_team": ["Team B", "Team D"],
        "home_xg": [1.2, 0.7],
        "away_xg": [0.8, 1.4],
    })


def _template(rows: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2026-01-{day:02d}" for day in range(1, rows + 1)],
        "home_team": ["Team A", "Team C", "Team X"][:rows],
        "away_team": ["Team B", "Team D", "Team Y"][:rows],
        "home_xg": [pd.NA] * rows,
        "away_xg": [pd.NA] * rows,
        "xg_entry_status": ["NEEDS_MANUAL_ENTRY"] * rows,
    })


def test_match_pair_source_normalizes():
    out = normalize_trusted_xg_source(_source(), source_path="trusted.csv")

    assert out["xg_source_schema"].iloc[0] == MATCH_PAIR_SCHEMA
    assert list(out.columns) == ["date", "home_team", "away_team", "home_xg", "away_xg", "xg_source_file", "xg_source_schema"]


def test_fbref_long_source_normalizes_only_when_pairing_is_safe():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-01"],
        "Squad": ["Team A", "Team B"],
        "Opponent": ["Team B", "Team A"],
        "xG": [1.2, 0.8],
        "xGA": [0.8, 1.2],
        "Venue": ["Home", "Away"],
    })

    out = normalize_trusted_xg_source(df, source_path="fbref.csv")

    assert len(out) == 1
    assert out["xg_source_schema"].iloc[0] == FBREF_LONG_SCHEMA
    assert out.loc[0, "home_team"] == "Team A"


def test_fbref_long_duplicate_home_rows_reject_as_ambiguous():
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-01"],
        "Squad": ["Team A", "Team A"],
        "Opponent": ["Team B", "Team B"],
        "xG": [1.2, 1.3],
        "xGA": [0.8, 0.7],
        "Venue": ["Home", "Home"],
    })

    try:
        normalize_trusted_xg_source(df)
    except ValueError as exc:
        assert "AMBIGUOUS" in str(exc)
    else:
        raise AssertionError("expected ambiguous FBref source to fail")


def test_understat_pair_source_normalizes():
    df = pd.DataFrame({
        "date": ["2026-01-01"],
        "home_team": ["A"],
        "away_team": ["B"],
        "home_xG": [1.1],
        "away_xG": [0.9],
    })

    out = normalize_trusted_xg_source(df)

    assert out["xg_source_schema"].iloc[0] == UNDERSTAT_PAIR_SCHEMA


def test_non_numeric_xg_rejects():
    df = _source()
    df["home_xg"] = df["home_xg"].astype(object)
    df.loc[0, "home_xg"] = "abc"

    try:
        normalize_trusted_xg_source(df)
    except ValueError as exc:
        assert "NON_NUMERIC_XG_VALUES" in str(exc)
    else:
        raise AssertionError("expected non-numeric xG to fail")


def test_negative_xg_rejects():
    df = _source()
    df.loc[0, "away_xg"] = -0.1

    try:
        normalize_trusted_xg_source(df)
    except ValueError as exc:
        assert "NEGATIVE_XG_VALUES" in str(exc)
    else:
        raise AssertionError("expected negative xG to fail")


def test_exact_date_home_away_join_fills_template():
    filled = join_trusted_xg_to_manual_template(normalize_trusted_xg_source(_source()), _template())

    assert filled["home_xg"].tolist() == [1.2, 0.7]
    assert filled.attrs["rows_filled"] == 2
    assert filled.attrs["join_coverage_pct"] == 100.0


def test_missing_source_rows_remain_blank_and_are_counted():
    filled = join_trusted_xg_to_manual_template(normalize_trusted_xg_source(_source( )[:1]), _template(2))

    assert filled.attrs["rows_filled"] == 1
    assert filled.attrs["rows_missing_xg"] == 1
    assert pd.isna(filled.loc[1, "home_xg"])


def test_output_writes_only_under_xg_fill_preview(tmp_path):
    source = tmp_path / "trusted.csv"
    template = tmp_path / "manual_template.csv"
    _source().to_csv(source, index=False)
    _template().to_csv(template, index=False)
    output_dir = tmp_path / "outputs" / "xg_fill_preview"

    _preview, summary = build_filled_manual_xg_preview(source, template, output_dir=output_dir)

    output = Path(summary["output_path"])
    assert output.exists()
    assert output_dir.resolve() in output.resolve().parents


def test_source_and_template_never_overwritten(tmp_path):
    source = tmp_path / "trusted.csv"
    template = tmp_path / "manual_template.csv"
    _source().to_csv(source, index=False)
    _template().to_csv(template, index=False)
    before = {_hash(source), _hash(template)}

    build_filled_manual_xg_preview(source, template, output_dir=tmp_path / "outputs" / "xg_fill_preview")

    assert before == {_hash(source), _hash(template)}


def test_acceptance_gate_can_be_run_on_filled_preview(tmp_path):
    source = tmp_path / "trusted.csv"
    template = tmp_path / "manual_template.csv"
    target = _template()[["date", "home_team", "away_team"]]
    _source().to_csv(source, index=False)
    _template().to_csv(template, index=False)
    preview, _summary = build_filled_manual_xg_preview(source, template, write_preview=False)

    _joined, result = evaluate_manual_xg_acceptance(preview, target_df=target)

    assert result.acceptance_label == "MANUAL_XG_ACCEPTED"


def test_cli_no_write_does_not_write_output(tmp_path):
    source = tmp_path / "trusted.csv"
    template = tmp_path / "manual_template.csv"
    output_dir = tmp_path / "outputs" / "xg_fill_preview"
    _source().to_csv(source, index=False)
    _template().to_csv(template, index=False)

    result = subprocess.run([
        sys.executable,
        str(ROOT / "scripts" / "fill_manual_xg_from_trusted_source.py"),
        "--source",
        str(source),
        "--template",
        str(template),
        "--output-dir",
        str(output_dir),
        "--no-write",
    ], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert "rows_filled=2" in result.stdout
    assert not output_dir.exists()


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    source = tmp_path / "trusted.csv"
    template = tmp_path / "manual_template.csv"
    _source().to_csv(source, index=False)
    _template().to_csv(template, index=False)

    build_filled_manual_xg_preview(source, template, output_dir=tmp_path / "outputs" / "xg_fill_preview")

    assert {path: _hash(path) for path in protected} == before
