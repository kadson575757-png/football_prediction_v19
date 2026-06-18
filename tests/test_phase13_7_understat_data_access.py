from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers import understat_data_access as uda  # noqa: E402
from football_prediction_v19.importers.understat_data_access import (  # noqa: E402
    UNDERSTAT_ACCESS_BLOCKED_NO_INPUT,
    UNDERSTAT_ACCESS_BLOCKED_OPTIONAL_PROVIDER_UNAVAILABLE,
    UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS,
    UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED,
    UNDERSTAT_ACCESS_READY,
    parse_local_understat_source,
    parse_raw_understat_payload_or_html,
    resolve_understat_trusted_xg_source,
    validate_understat_normalized_xg,
    write_understat_data_access_csv,
)
import audit_understat_data_access as access_audit  # noqa: E402


def _matches() -> list[dict]:
    return [
        {
            "datetime": "2024-08-24 15:30:00",
            "h": {"title": "Bayern Munich"},
            "a": {"title": "Dortmund"},
            "xG": {"h": "2.01", "a": "0.77"},
        }
    ]


def _embedded_html(records: list[dict] | None = None) -> str:
    encoded = json.dumps(records if records is not None else _matches()).encode("unicode_escape").decode("ascii")
    return f"<html><script>var datesData = JSON.parse('{encoded}');</script></html>"


def _payload(records: list[dict] | None = None) -> str:
    return json.dumps({"response": records if records is not None else _matches()})


def _normalized() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-08-24",
                "home_team": "Bayern Munich",
                "away_team": "Dortmund",
                "home_xg": 2.01,
                "away_xg": 0.77,
                "xg_source_name": "understat_test",
                "xg_source_url": "",
                "xg_import_type": "LOCAL_FILE",
            }
        ]
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_resolver_returns_no_input_when_no_league_source_or_mode_can_resolve(tmp_path):
    result = resolve_understat_trusted_xg_source(
        output_dir=tmp_path / "data" / "trusted_xg_sources",
        raw_dir=tmp_path / "data" / "trusted_xg_sources" / "raw",
    )
    assert result.access_label == UNDERSTAT_ACCESS_BLOCKED_NO_INPUT


def test_resolver_discovers_existing_normalized_understat_source(tmp_path):
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    out_dir.mkdir(parents=True)
    existing = out_dir / "understat_xg_bundesliga_2024.csv"
    _normalized().to_csv(existing, index=False)

    result = resolve_understat_trusted_xg_source(league="Bundesliga", season=2024, output_dir=out_dir)

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert result.successful_mode == "existing"
    assert result.output_path == str(existing)
    assert result.rows_normalized == 1


def test_resolver_parses_local_understat_pair_export(tmp_path):
    source = tmp_path / "understat_pair.csv"
    pd.DataFrame(
        [{"date": "2024-08-24", "home_team": "A", "away_team": "B", "home_xG": 1.2, "away_xG": 0.4}]
    ).to_csv(source, index=False)

    df = parse_local_understat_source(source)

    assert len(df) == 1
    assert df.loc[0, "home_xg"] == 1.2


def test_resolver_parses_local_understat_hxg_axg_export(tmp_path):
    source = tmp_path / "understat_alias.csv"
    pd.DataFrame([{"date": "2024-08-24", "home": "A", "away": "B", "hxg": 1.2, "axg": 0.4}]).to_csv(source, index=False)

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        source=source,
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=tmp_path / "out",
    )

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert result.successful_mode == "local"
    assert Path(result.output_path).exists()


def test_resolver_parses_raw_fixture_payload_or_html_with_embedded_data(tmp_path):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_bundesliga_2024.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_embedded_html(), encoding="utf-8")

    df = parse_raw_understat_payload_or_html(raw, league="Bundesliga", season=2024)

    assert len(df) == 1
    assert df.loc[0, "away_xg"] == 0.77


def test_resolver_parses_raw_runtime_payload(tmp_path):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_bundesliga_2024.payload"
    raw.parent.mkdir(parents=True)
    raw.write_text(_payload(), encoding="utf-8")

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=tmp_path / "out",
        raw_dir=raw.parent,
        modes=["raw"],
    )

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert result.successful_mode == "raw"


def test_resolver_rejects_raw_base_only_html_with_no_xg_data(tmp_path):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_bundesliga_2024.html"
    raw.parent.mkdir(parents=True)
    raw.write_text("<html><script>var BASE_URL='https://understat.com/';</script></html>", encoding="utf-8")

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        raw_dir=raw.parent,
        modes=["raw"],
    )

    assert result.access_label == UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED
    assert "UNDERSTAT_MATCH_DATA_NOT_FOUND" in " | ".join(result.validation_errors)


def test_optional_provider_unavailable_returns_graceful_blocked_label(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "soccerdata", None)

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        modes=["optional_provider"],
        allow_optional_provider=True,
    )

    assert result.access_label == UNDERSTAT_ACCESS_BLOCKED_OPTIONAL_PROVIDER_UNAVAILABLE
    assert result.warning_notes


def test_optional_provider_mocked_success_writes_normalized_trusted_xg_csv(tmp_path, monkeypatch):
    class Provider:
        def __init__(self, leagues, seasons):
            self.leagues = leagues
            self.seasons = seasons

        def read_schedule(self):
            return pd.DataFrame([{"date": "2024-08-24", "home_team": "A", "away_team": "B", "home_xg": 1.2, "away_xg": 0.4}])

    monkeypatch.setitem(sys.modules, "soccerdata", types.SimpleNamespace(Understat=Provider))

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=tmp_path / "out",
        modes=["optional_provider"],
        allow_optional_provider=True,
    )

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert result.successful_mode == "optional_provider"
    assert Path(result.output_path).exists()


def test_explicit_fetch_is_not_called_unless_allow_network_true(tmp_path, monkeypatch):
    called = {"value": False}

    def fail_if_called(*_args, **_kwargs):
        called["value"] = True
        raise AssertionError("explicit fetch should not be called")

    monkeypatch.setattr(uda, "fetch_understat_league_season", fail_if_called)
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        modes=["explicit_fetch"],
        allow_network=False,
    )

    assert result.access_label == UNDERSTAT_ACCESS_BLOCKED_NO_INPUT
    assert called["value"] is False


def test_explicit_fetch_mocked_success_writes_normalized_trusted_xg_csv(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"

    def fake_fetch(*_args, **kwargs):
        path = write_understat_data_access_csv(_normalized(), kwargs["output_name"], output_dir=kwargs["output_dir"], overwrite=True)
        return types.SimpleNamespace(
            fetch_label="UNDERSTAT_FETCH_READY",
            output_path=str(path),
            source_url="https://understat.com/league/Bundesliga/2024",
            validation_errors=[],
            warning_notes=[],
        )

    monkeypatch.setattr(uda, "fetch_understat_league_season", fake_fetch)
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=out_dir,
        modes=["explicit_fetch"],
        allow_network=True,
    )

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert result.successful_mode == "explicit_fetch"
    assert Path(result.output_path).exists()


def test_output_is_not_overwritten_without_overwrite(tmp_path):
    out_dir = tmp_path / "out"
    output = write_understat_data_access_csv(_normalized(), "understat_xg_bundesliga_2024.csv", output_dir=out_dir)
    before = _sha(output)

    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        source=tmp_path / "missing.csv",
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=out_dir,
        modes=["existing"],
    )

    assert result.access_label == UNDERSTAT_ACCESS_READY
    assert _sha(output) == before

    try:
        write_understat_data_access_csv(_normalized(), "understat_xg_bundesliga_2024.csv", output_dir=out_dir)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing output should not be overwritten")
    assert _sha(output) == before


def test_local_mode_blocks_output_exists_without_overwrite(tmp_path):
    source = tmp_path / "understat_alias.csv"
    pd.DataFrame([{"date": "2024-08-24", "home": "A", "away": "B", "hxg": 1.2, "axg": 0.4}]).to_csv(source, index=False)
    out_dir = tmp_path / "out"
    write_understat_data_access_csv(_normalized(), "understat_xg.csv", output_dir=out_dir)

    result = resolve_understat_trusted_xg_source(source=source, output_name="understat_xg.csv", output_dir=out_dir, modes=["local"])

    assert result.access_label == UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS


def test_xg_validation_rejects_missing_xg():
    df = _normalized()
    df.loc[0, "home_xg"] = ""
    assert "MISSING_XG_VALUES" in validate_understat_normalized_xg(df)


def test_xg_validation_rejects_non_numeric_xg():
    df = _normalized()
    df.loc[0, "home_xg"] = "bad"
    assert "NON_NUMERIC_XG_VALUES" in validate_understat_normalized_xg(df)


def test_xg_validation_rejects_negative_xg():
    df = _normalized()
    df.loc[0, "home_xg"] = -0.1
    assert "NEGATIVE_XG_VALUES" in validate_understat_normalized_xg(df)


def test_audit_understat_data_access_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "outputs" / "diagnostics"
    table, markdown, rec = access_audit.run(root=tmp_path, output_dir=output_dir)

    assert table.empty
    assert rec in {"TRY_UNDERSTAT_OPTIONAL_PROVIDER_BOOTSTRAP", "TRY_UNDERSTAT_OPTIONAL_PROVIDER"}
    assert (output_dir / "understat_data_access_summary.csv").exists()
    assert (output_dir / "understat_data_access_summary.md").exists()
    assert "Phase 13.7 is diagnostic/foundation only. No xG values were inferred or invented." in markdown


def test_audit_recommends_try_understat_local_export_when_no_sources_exist(tmp_path):
    table = access_audit.build_table(tmp_path)
    assert access_audit.recommendation(table, provider_available=False, fetch_available=True) == "TRY_UNDERSTAT_OPTIONAL_PROVIDER_BOOTSTRAP"


def test_gitignore_contains_raw_trusted_xg_and_diagnostics_outputs():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/trusted_xg_sources/raw/*" in text
    assert "outputs/diagnostics/*.csv" in text
    assert "outputs/diagnostics/*.md" in text
    assert "outputs/diagnostics/*.ps1" in text


def test_no_hidden_web_or_api_calls_in_tests(tmp_path, monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("network/fetch path should not be called")

    monkeypatch.setattr(uda, "fetch_understat_league_season", fail_if_called)
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        modes=["existing", "local", "raw"],
        allow_network=False,
    )
    assert result.access_label != UNDERSTAT_ACCESS_READY


def test_protected_model_probability_market_betting_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "recommended_market.py",
        ROOT / "src" / "football_prediction_v19" / "model.py",
        ROOT / "src" / "football_prediction_v19" / "rules_v19.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    write_understat_data_access_csv(_normalized(), "understat_xg.csv", output_dir=tmp_path / "out")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
