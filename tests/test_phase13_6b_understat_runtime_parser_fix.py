from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.understat_fetch import (  # noqa: E402
    UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED,
    UNDERSTAT_FETCH_READY,
    UNDERSTAT_HTML_BLOCKED_ACCESS_DENIED,
    UNDERSTAT_HTML_BLOCKED_CLOUDFLARE,
    UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY,
    UNDERSTAT_HTML_HAS_EMBEDDED_DATES_DATA,
    build_understat_dates_endpoint_candidates,
    detect_understat_html_state,
    extract_understat_runtime_data_endpoints,
    fetch_understat_league_season,
    normalize_understat_matches_to_trusted_xg,
    parse_understat_matches_from_runtime_payload,
)
import audit_understat_fetch as fetch_audit  # noqa: E402


PYTHON = sys.executable


def _records() -> list[dict]:
    return [
        {
            "datetime": "2024-08-24 15:30:00",
            "h": {"title": "Bayern Munich"},
            "a": {"title": "Dortmund"},
            "xG": {"h": "2.01", "a": "0.77"},
        }
    ]


def _embedded_html() -> str:
    encoded = json.dumps(_records()).encode("unicode_escape").decode("ascii")
    return f"<script>var datesData = JSON.parse('{encoded}');</script>"


def _base_html() -> str:
    return """
    <html>
      <head><script>var BASE_URL = 'https://understat.com/';</script></head>
      <body>
        <script src="/js/app.js"></script>
        <script>fetch('/main/getLeagueDates?league=Bundesliga&season=2024')</script>
        <a href="https://evil.example.com/api">ignore</a>
      </body>
    </html>
    """


def _payload(records: list[dict] | None = None) -> str:
    return json.dumps({"response": records if records is not None else _records()})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_detect_html_with_embedded_dates_data():
    assert detect_understat_html_state(_embedded_html()) == UNDERSTAT_HTML_HAS_EMBEDDED_DATES_DATA


def test_detect_base_only_understat_page():
    assert detect_understat_html_state(_base_html()) == UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY


def test_detect_cloudflare_and_access_denied_pages():
    assert detect_understat_html_state("<html>Just a moment Cloudflare</html>") == UNDERSTAT_HTML_BLOCKED_CLOUDFLARE
    assert detect_understat_html_state("<html>Access denied</html>") == UNDERSTAT_HTML_BLOCKED_ACCESS_DENIED


def test_inspect_script_srcs_from_fixture_html(tmp_path):
    raw = tmp_path / "understat.html"
    raw.write_text(_base_html(), encoding="utf-8")
    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "inspect_understat_raw_fetch.py"), "--raw-path", str(raw)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "html_state=UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY" in result.stdout
    assert "script_src=/js/app.js" in result.stdout
    assert "candidate_runtime_endpoints_found=" in result.stdout


def test_endpoint_discovery_returns_only_same_domain_understat_candidates():
    endpoints = extract_understat_runtime_data_endpoints(_base_html(), base_url="https://understat.com/league/Bundesliga/2024")
    assert endpoints
    assert all("understat.com" in endpoint for endpoint in endpoints)
    assert not any("evil.example.com" in endpoint for endpoint in endpoints)


def test_deterministic_endpoint_candidates_are_tied_to_requested_league_season():
    endpoints = build_understat_dates_endpoint_candidates("Bundesliga", 2024, "https://understat.com/league/Bundesliga/2024")
    assert endpoints
    assert all("Bundesliga" in endpoint and "2024" in endpoint for endpoint in endpoints)


def test_fallback_parser_can_parse_runtime_json_payload_into_trusted_xg_rows():
    matches = parse_understat_matches_from_runtime_payload(_payload(), source_url="https://understat.com/main/getLeagueDates")
    out = normalize_understat_matches_to_trusted_xg(matches)
    assert len(out) == 1
    assert out.loc[0, "home_xg"] == 2.01


def test_fallback_parser_rejects_incomplete_records():
    records = _records() + [{"datetime": "2024-08-25", "h": {"title": "A"}}]
    try:
        parse_understat_matches_from_runtime_payload(_payload(records))
    except ValueError as exc:
        assert "INCOMPLETE_RECORDS" in str(exc)
    else:
        raise AssertionError("incomplete records should reject")


def test_fallback_parser_rejects_missing_xg():
    records = _records()
    records[0]["xG"]["h"] = ""
    try:
        parse_understat_matches_from_runtime_payload(_payload(records))
    except ValueError as exc:
        assert "PARSE_FAILED" in str(exc)
    else:
        raise AssertionError("missing xG should reject")


def test_fallback_parser_rejects_non_numeric_xg():
    records = _records()
    records[0]["xG"]["a"] = "bad"
    try:
        parse_understat_matches_from_runtime_payload(_payload(records))
    except ValueError as exc:
        assert "PARSE_FAILED" in str(exc)
    else:
        raise AssertionError("non-numeric xG should reject")


def test_fallback_parser_rejects_negative_xg():
    records = _records()
    records[0]["xG"]["a"] = "-0.5"
    try:
        parse_understat_matches_from_runtime_payload(_payload(records))
    except ValueError as exc:
        assert "PARSE_FAILED" in str(exc)
    else:
        raise AssertionError("negative xG should reject")


def test_fetch_flow_uses_fallback_when_embedded_data_missing(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_base.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_base_html(), encoding="utf-8")
    payload = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_endpoint.payload"
    payload.write_text(_payload(), encoding="utf-8")
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_endpoint_json_or_html", lambda *_args, **_kwargs: payload)
    result = fetch_understat_league_season(
        league="Bundesliga",
        season=2024,
        output_name="understat_xg_bundesliga_2024.csv",
        output_dir=tmp_path / "data" / "trusted_xg_sources",
        raw_output_dir=raw.parent,
    )
    assert result.fetch_label == UNDERSTAT_FETCH_READY
    assert result.fallback_endpoints_checked > 0
    assert result.fallback_endpoint_used
    assert any("FALLBACK_RUNTIME_ENDPOINT_USED" in note for note in result.warning_notes)


def test_fetch_flow_remains_parse_failed_when_fallback_payload_has_no_valid_xg(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_base.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_base_html(), encoding="utf-8")
    payload = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_endpoint.payload"
    payload.write_text(json.dumps({"response": [{"foo": "bar"}]}), encoding="utf-8")
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_html", lambda *_args, **_kwargs: raw)
    monkeypatch.setattr("football_prediction_v19.importers.understat_fetch.fetch_understat_endpoint_json_or_html", lambda *_args, **_kwargs: payload)
    result = fetch_understat_league_season(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_output_dir=raw.parent)
    assert result.fetch_label == UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED
    assert "UNDERSTAT_RUNTIME_ENDPOINT_PARSE_FAILED" in result.validation_errors


def test_debug_inspect_script_prints_html_state_and_candidates(tmp_path):
    raw = tmp_path / "understat.html"
    raw.write_text(_base_html(), encoding="utf-8")
    result = subprocess.run(
        [PYTHON, str(ROOT / "scripts" / "inspect_understat_raw_fetch.py"), "--raw-path", str(raw)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "html_state=UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY" in result.stdout
    assert "candidate_endpoint=" in result.stdout


def test_audit_understat_fetch_reports_raw_html_exists_but_no_normalized_source(tmp_path):
    raw = tmp_path / "data" / "trusted_xg_sources" / "raw" / "understat_league_Bundesliga_2024.html"
    raw.parent.mkdir(parents=True)
    raw.write_text(_base_html(), encoding="utf-8")
    table, markdown, rec = fetch_audit.run(root=tmp_path, output_dir=tmp_path / "out")
    assert not table.empty
    assert rec == "FIX_UNDERSTAT_FETCH_PARSE"
    assert "Raw Understat HTML exists but no parseable xG match payload was found." in markdown
    assert "UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY" in markdown


def test_protected_model_probability_market_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    parse_understat_matches_from_runtime_payload(_payload())
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
