from __future__ import annotations

import hashlib
import io
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.trusted_xg_source_import import (  # noqa: E402
    TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT,
    TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED,
    TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES,
    TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
    TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND,
    TRUSTED_XG_IMPORT_READY,
    fetch_explicit_trusted_xg_source_url,
    import_trusted_xg_source,
)
import audit_trusted_xg_source_import as import_audit  # noqa: E402


PYTHON = sys.executable


def _pair(**overrides) -> pd.DataFrame:
    data = {
        "date": ["2024-01-01", "2024-01-02"],
        "home_team": ["Home A", "Home B"],
        "away_team": ["Away A", "Away B"],
        "home_xg": [1.2, 1.5],
        "away_xg": [0.7, 0.8],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def _import(source: Path, out_dir: Path, **kwargs):
    return import_trusted_xg_source(
        source,
        output_name=kwargs.pop("output_name", "trusted_xg.csv"),
        output_dir=out_dir,
        raw_output_dir=out_dir / "raw",
        **kwargs,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_local_match_pair_csv_imports_successfully(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair().to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_READY
    assert result.rows_normalized == 2
    assert Path(result.output_path).parent == out_dir


def test_local_match_pair_aliases_xg_home_xg_away_import_successfully(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    pd.DataFrame({
        "Date": ["2024-01-01"],
        "HomeTeam": ["Home A"],
        "AwayTeam": ["Away A"],
        "xG_home": [1.1],
        "xG_away": [0.6],
    }).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_READY


def test_local_hxg_axg_imports_successfully(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    pd.DataFrame({
        "date": ["2024-01-01"],
        "home_team": ["Home A"],
        "away_team": ["Away A"],
        "hxg": [1.1],
        "axg": [0.6],
    }).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_READY


def test_local_understat_pair_csv_imports_successfully(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    pd.DataFrame({
        "date": ["2024-01-01"],
        "home_team": ["Home A"],
        "away_team": ["Away A"],
        "home_xG": [1.1],
        "away_xG": [0.6],
    }).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_READY
    assert result.detected_schema == "UNDERSTAT_PAIR_XG_SOURCE"


def test_fbref_long_safe_pairing_imports_successfully(tmp_path):
    source = tmp_path / "fbref.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-01"],
        "Squad": ["Home A", "Away A"],
        "Opponent": ["Away A", "Home A"],
        "xG": [1.3, 0.4],
        "xGA": [0.4, 1.3],
        "Venue": ["Home", "Away"],
    }).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_READY
    assert result.rows_normalized == 1


def test_ambiguous_fbref_long_pairing_rejects(tmp_path):
    source = tmp_path / "fbref.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-01"],
        "Squad": ["Home A", "Home A"],
        "Opponent": ["Away A", "Away A"],
        "xG": [1.3, 1.4],
        "xGA": [0.4, 0.5],
        "Venue": ["Home", "Home"],
    }).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT


def test_non_numeric_xg_rejects(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair(home_xg=["bad", "1.2"]).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES


def test_negative_xg_rejects(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair(away_xg=[-0.1, 0.8]).to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES


def test_missing_source_path_returns_source_not_found_label(tmp_path):
    result = import_trusted_xg_source(tmp_path / "missing.csv", output_dir=tmp_path / "out")
    assert result.import_label == TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND


def test_url_with_no_fetch_does_not_fetch_and_is_blocked():
    result = import_trusted_xg_source("https://example.com/xg.csv", no_fetch=True)
    assert result.import_label == TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED
    assert "NO_FETCH_REQUESTED" in result.validation_errors


def test_output_writes_only_under_data_trusted_xg_sources(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair().to_csv(source, index=False)
    result = _import(source, out_dir)
    assert out_dir.resolve() in Path(result.output_path).resolve().parents


def test_raw_fetched_files_write_only_under_raw_dir(tmp_path, monkeypatch):
    raw_dir = tmp_path / "data" / "trusted_xg_sources" / "raw"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"date,home_team,away_team,home_xg,away_xg\n2024-01-01,H,A,1.0,0.5\n"

    monkeypatch.setattr("football_prediction_v19.importers.trusted_xg_source_import.urlopen", lambda *_args, **_kwargs: Response())
    output = fetch_explicit_trusted_xg_source_url("https://example.com/xg.csv", output_dir=raw_dir)
    assert raw_dir.resolve() in output.resolve().parents


def test_existing_output_is_not_overwritten_without_overwrite(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair().to_csv(source, index=False)
    first = _import(source, out_dir)
    before = _sha(Path(first.output_path))
    second = _import(source, out_dir)
    assert second.import_label == TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS
    assert _sha(Path(first.output_path)) == before


def test_audit_trusted_xg_source_import_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "outputs" / "diagnostics"
    table, markdown, rec = import_audit.run(root=tmp_path, output_dir=output_dir)
    assert table.empty
    assert rec == "ADD_TRUSTED_XG_SOURCE_FILE"
    assert (output_dir / "trusted_xg_source_import_summary.csv").exists()
    assert (output_dir / "trusted_xg_source_import_summary.md").exists()
    assert "Phase 13.4 is diagnostic/foundation only" in markdown


def test_audit_recommends_add_trusted_xg_source_file_when_no_source_exists(tmp_path):
    table, _markdown, rec = import_audit.run(root=tmp_path, output_dir=tmp_path / "out")
    assert table.empty
    assert rec == "ADD_TRUSTED_XG_SOURCE_FILE"


def test_cli_local_import_prints_ready_without_network(tmp_path):
    source = tmp_path / "source.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _pair().to_csv(source, index=False)
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "import_trusted_xg_source.py"),
            "--source",
            str(source),
            "--output-dir",
            str(out_dir),
            "--output-name",
            "trusted_xg.csv",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "import_label=TRUSTED_XG_IMPORT_READY" in result.stdout


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source = tmp_path / "source.csv"
    _pair().to_csv(source, index=False)
    import_trusted_xg_source(source, output_name="trusted.csv", output_dir=tmp_path / "data" / "trusted_xg_sources")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
