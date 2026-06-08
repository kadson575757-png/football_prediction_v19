from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.understat_trusted_xg import (  # noqa: E402
    UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED,
    UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA,
    UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES,
    UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
    UNDERSTAT_XG_IMPORT_READY,
    fetch_explicit_understat_source_url,
    import_understat_trusted_xg_source,
    normalize_understat_long_export,
    normalize_understat_pair_export,
)
import audit_understat_xg_source as understat_audit  # noqa: E402


PYTHON = sys.executable


def _understat_pair() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "home_team": ["Home A", "Home B"],
        "away_team": ["Away A", "Away B"],
        "home_xG": [1.2, 1.4],
        "away_xG": [0.7, 0.9],
    })


def _understat_long() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-01"],
        "team": ["Home A", "Away A"],
        "opponent": ["Away A", "Home A"],
        "xG": [1.2, 0.7],
        "xGA": [0.7, 1.2],
        "venue": ["home", "away"],
    })


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import(source: Path, out_dir: Path, **kwargs):
    return import_understat_trusted_xg_source(
        source,
        output_name=kwargs.pop("output_name", "understat_xg.csv"),
        output_dir=out_dir,
        raw_output_dir=out_dir / "raw",
        **kwargs,
    )


def test_understat_pair_export_normalizes_successfully():
    out = normalize_understat_pair_export(_understat_pair(), source_path="understat.csv")
    assert list(out.columns) == [
        "date",
        "home_team",
        "away_team",
        "home_xg",
        "away_xg",
        "xg_source_name",
        "xg_source_url",
        "xg_import_type",
    ]
    assert len(out) == 2


def test_understat_hxg_axg_alias_export_normalizes_successfully():
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "home": ["Home A"],
        "away": ["Away A"],
        "hxg": [1.2],
        "axg": [0.7],
    })
    out = normalize_understat_pair_export(df)
    assert out.loc[0, "home_xg"] == 1.2
    assert out.loc[0, "away_xg"] == 0.7


def test_understat_long_export_normalizes_only_when_safely_pairable():
    out = normalize_understat_long_export(_understat_long())
    assert len(out) == 1
    assert out.loc[0, "home_team"] == "Home A"


def test_ambiguous_long_export_rejects():
    df = _understat_long()
    df.loc[1, "opponent"] = "Other"
    try:
        normalize_understat_long_export(df)
    except ValueError as exc:
        assert "PAIRING_AMBIGUOUS" in str(exc)
    else:
        raise AssertionError("ambiguous long export should reject")


def test_missing_xg_rejects(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = _understat_pair()
    df.loc[0, "home_xG"] = None
    df.to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES


def test_non_numeric_xg_rejects(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = _understat_pair()
    df["away_xG"] = df["away_xG"].astype(object)
    df.loc[0, "away_xG"] = "bad"
    df.to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES


def test_negative_xg_rejects(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    df = _understat_pair()
    df.loc[0, "away_xG"] = -0.1
    df.to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES


def test_output_writes_only_under_data_trusted_xg_sources(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _understat_pair().to_csv(source, index=False)
    result = _import(source, out_dir)
    assert result.import_label == UNDERSTAT_XG_IMPORT_READY
    assert out_dir.resolve() in Path(result.output_path).resolve().parents


def test_raw_fetched_files_write_only_under_raw_dir(tmp_path, monkeypatch):
    raw_dir = tmp_path / "data" / "trusted_xg_sources" / "raw"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"date,home_team,away_team,home_xG,away_xG\n2024-01-01,H,A,1.0,0.5\n"

    monkeypatch.setattr("football_prediction_v19.importers.understat_trusted_xg.urlopen", lambda *_args, **_kwargs: Response())
    output = fetch_explicit_understat_source_url("https://example.com/understat.csv", output_dir=raw_dir)
    assert raw_dir.resolve() in output.resolve().parents


def test_existing_output_is_not_overwritten_without_overwrite(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _understat_pair().to_csv(source, index=False)
    first = _import(source, out_dir)
    before = _sha(Path(first.output_path))
    second = _import(source, out_dir)
    assert second.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS
    assert _sha(Path(first.output_path)) == before


def test_url_with_no_fetch_is_blocked_and_does_not_fetch():
    result = import_understat_trusted_xg_source("https://example.com/understat.csv", no_fetch=True)
    assert result.import_label == UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED
    assert "NO_FETCH_REQUESTED" in result.validation_errors


def test_audit_understat_xg_source_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "outputs" / "diagnostics"
    table, markdown, rec = understat_audit.run(root=tmp_path, output_dir=output_dir)
    assert table.empty
    assert rec == "ADD_UNDERSTAT_XG_SOURCE_FILE"
    assert (output_dir / "understat_xg_source_audit_summary.csv").exists()
    assert (output_dir / "understat_xg_source_audit_summary.md").exists()
    assert "Phase 13.5 is diagnostic/foundation only" in markdown


def test_generic_import_trusted_xg_source_routes_understat_source(tmp_path):
    source = tmp_path / "understat_export.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _understat_pair().to_csv(source, index=False)
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "import_trusted_xg_source.py"),
            "--source",
            str(source),
            "--output-dir",
            str(out_dir),
            "--output-name",
            "understat_export.csv",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "import_label=UNDERSTAT_XG_IMPORT_READY" in result.stdout


def test_cli_import_understat_xg_source_prints_ready_without_network(tmp_path):
    source = tmp_path / "understat.csv"
    out_dir = tmp_path / "data" / "trusted_xg_sources"
    _understat_pair().to_csv(source, index=False)
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "import_understat_xg_source.py"),
            "--source",
            str(source),
            "--output-dir",
            str(out_dir),
            "--output-name",
            "understat.csv",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "import_label=UNDERSTAT_XG_IMPORT_READY" in result.stdout


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    source = tmp_path / "understat.csv"
    _understat_pair().to_csv(source, index=False)
    import_understat_trusted_xg_source(source, output_name="understat.csv", output_dir=tmp_path / "data" / "trusted_xg_sources")
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
