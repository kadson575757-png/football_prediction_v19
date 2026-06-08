from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.understat_fetch import (  # noqa: E402
    UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED,
    UNDERSTAT_FETCH_BLOCKED_NO_INPUT,
    UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND,
    UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS,
    UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED,
    UNDERSTAT_FETCH_BLOCKED_UNSUPPORTED_LEAGUE,
    UNDERSTAT_FETCH_BLOCKED_INVALID_XG_VALUES,
    UNDERSTAT_FETCH_READY,
    build_understat_league_url,
    fetch_understat_html,
    fetch_understat_league_season,
    normalize_understat_league_name,
    normalize_understat_matches_to_trusted_xg,
    parse_understat_matches_from_html,
    write_understat_fetch_trusted_xg_csv,
)
import audit_understat_fetch as fetch_audit  # noqa: E402
import audit_understat_xg_source as understat_audit  # noqa: E402
import audit_trusted_xg_intake as intake_audit  # noqa: E402


def _matches() -> list[dict]:
    return [
        {
            "datetime": "2024-08-24 15:30:00",
            "h": {"title": "Bayern Munich"},
            "a": {"title": "Borussia Dortmund"},
            "xG": {"h": "1.75", "a": "0.82"},
        },
        {
            "datetime": "2024-08-25 17:30:00",
            "h": {"title": "RB Leipzig"},
            "a": {"title": "Freiburg"},
            "xG": {"h": "1.21", "a": "1.03"},
        },
    ]


def _html(matches: list[dict] | None = None) -> str:
    encoded = json.dumps(matches if matches is not None else _matches()).encode("unicode_escape").decode("ascii")
    return f"<html><script>var datesData = JSON.parse('{encoded}');</script></html>"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_league_alias_normalization_works():
    assert normalize_understat_league_name("Bundesliga") == "Bundesliga"
    assert normalize_understat_league_name("D1") == "Bundesliga"
    assert normalize_understat_league_name("EPL") == "EPL"
    assert normalize_understat_league_name("La Liga") == "La_liga"
    assert normalize_understat_league_name("Serie A") == "Serie_A"
    assert normalize_understat_league_name("Ligue 1") == "Ligue_1"


def test_deterministic_url_builder_works():
    assert build_understat_league_url("Bundesliga", 2024) == "https://understat.com/league/Bundesliga/2024"
    assert build_understat_league_url("La Liga", "2024") == "https://understat.com/league/La_liga/2024"


def test_no_input_returns_blocked_no_input():
    result = fetch_understat_league_season(no_fetch=True)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_NO_INPUT


def test_unsupported_league_returns_blocked_unsupported():
    result = fetch_understat_league_season(league="Mars League", season=2024, no_fetch=True)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_UNSUPPORTED_LEAGUE


def test_no_fetch_blocks_url_and_league_season_fetch():
    url_result = fetch_understat_league_season(url="https://understat.com/league/Bundesliga/2024", no_fetch=True)
    league_result = fetch_understat_league_season(league="Bundesliga", season=2024, no_fetch=True)
    assert url_result.fetch_label == UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED
    assert league_result.fetch_label == UNDERSTAT_FETCH_BLOCKED_FETCH_FAILED


def test_parse_fixture_understat_html_with_embedded_match_data_successfully():
    matches = parse_understat_matches_from_html(_html())
    assert len(matches) == 2
    out = normalize_understat_matches_to_trusted_xg(matches, source_url="https://understat.com/league/Bundesliga/2024")
    assert len(out) == 2
    assert out.loc[0, "home_xg"] == 1.75


def test_parse_failure_returns_parse_failed_label(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_bad.html"
    raw.parent.mkdir(parents=True)
    raw.write_text("<html>no embedded data</html>", encoding="utf-8")
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    result = fetch_understat_league_season(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_output_dir=raw.parent)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED


def test_no_matches_returns_no_matches_label(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_empty.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_html([]), encoding="utf-8")
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    result = fetch_understat_league_season(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_output_dir=raw.parent)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_NO_MATCHES_FOUND


def test_missing_xg_rejects():
    matches = _matches()
    matches[0]["xG"]["h"] = ""
    try:
        normalize_understat_matches_to_trusted_xg(matches)
    except ValueError as exc:
        assert "MISSING_XG_VALUES" in str(exc)
    else:
        raise AssertionError("missing xG should reject")


def test_non_numeric_xg_rejects():
    matches = _matches()
    matches[0]["xG"]["a"] = "bad"
    try:
        normalize_understat_matches_to_trusted_xg(matches)
    except ValueError as exc:
        assert "NON_NUMERIC_XG_VALUES" in str(exc)
    else:
        raise AssertionError("non-numeric xG should reject")


def test_negative_xg_rejects():
    matches = _matches()
    matches[0]["xG"]["a"] = "-0.1"
    try:
        normalize_understat_matches_to_trusted_xg(matches)
    except ValueError as exc:
        assert "NEGATIVE_XG_VALUES" in str(exc)
    else:
        raise AssertionError("negative xG should reject")


def test_raw_html_writes_only_under_raw_dir(tmp_path, monkeypatch):
    raw_dir = tmp_path / "data" / "trusted_xg_sources" / "raw"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return _html().encode("utf-8")

    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.urlopen", lambda *_args, **_kwargs: Response())
    output = fetch_understat_html("https://understat.com/league/Bundesliga/2024", raw_output_dir=raw_dir)
    assert raw_dir.resolve() in output.resolve().parents


def test_normalized_csv_writes_only_under_trusted_sources(tmp_path):
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = normalize_understat_matches_to_trusted_xg(_matches())
    output = write_understat_fetch_trusted_xg_csv(df, "understat_xg.csv", output_dir=out_dir)
    assert out_dir.resolve() in output.resolve().parents


def test_existing_output_is_not_overwritten_without_overwrite(tmp_path):
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = normalize_understat_matches_to_trusted_xg(_matches())
    output = write_understat_fetch_trusted_xg_csv(df, "understat_xg.csv", output_dir=out_dir)
    before = _sha(output)
    try:
        write_understat_fetch_trusted_xg_csv(df, "understat_xg.csv", output_dir=out_dir)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing output should block")
    assert _sha(output) == before


def test_fetch_existing_output_label_without_overwrite(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_html(), encoding="utf-8")
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = normalize_understat_matches_to_trusted_xg(_matches())
    write_understat_fetch_trusted_xg_csv(df, "understat_xg.csv", output_dir=out_dir)
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    result = fetch_understat_league_season(league="Bundesliga", season=2024, output_name="understat_xg.csv", output_dir=out_dir, raw_output_dir=raw.parent)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_OUTPUT_EXISTS


def test_invalid_xg_label_from_fetch(tmp_path, monkeypatch):
    matches = _matches()
    matches[0]["xG"]["h"] = "bad"
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_bad_xg.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_html(matches), encoding="utf-8")
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    result = fetch_understat_league_season(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_output_dir=raw.parent)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_INVALID_XG_VALUES


def test_audit_understat_fetch_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "outputs" / "diagnostics"
    table, markdown, rec = fetch_audit.run(root=tmp_path, output_dir=output_dir)
    assert table.empty
    assert rec == "FETCH_UNDERSTAT_LEAGUE_SEASON"
    assert (output_dir / "understat_fetch_audit_summary.csv").exists()
    assert (output_dir / "understat_fetch_audit_summary.md").exists()
    assert "Phase 13.6 is diagnostic/foundation only" in markdown


def test_integration_with_understat_and_intake_audits_when_normalized_source_exists(tmp_path):
    source_dir = tmp_path / "data" / "trusted_xg_sources"
    df = normalize_understat_matches_to_trusted_xg(_matches())
    write_understat_fetch_trusted_xg_csv(df, "understat_xg_bundesliga_2024.csv", output_dir=source_dir)
    understat_table, _md, understat_rec = understat_audit.run(root=tmp_path, output_dir=tmp_path / "out_understat")
    intake_table, _intake_md, intake_rec = intake_audit.run(source_dir, tmp_path / "out_intake")
    assert understat_rec == "READY_FOR_TRUSTED_XG_INTAKE"
    assert not understat_table.empty
    assert intake_rec in {"FIX_TRUSTED_XG_TARGET_MATCHING", "READY_FOR_TRUSTED_XG_PROMOTION_PREVIEW", "FILL_MISSING_XG_FROM_TRUSTED_SOURCE"}
    assert not intake_table.empty


def test_protected_model_probability_market_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    df = normalize_understat_matches_to_trusted_xg(_matches())
    write_understat_fetch_trusted_xg_csv(df, "understat_xg.csv", output_dir=tmp_path / "data" / "trusted_xg_sources")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
