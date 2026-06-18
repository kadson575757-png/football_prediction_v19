from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.understat_data_access import (  # noqa: E402
    resolve_understat_trusted_xg_source,
)
from football_prediction_v19.importers.understat_optional_provider import (  # noqa: E402
    UNDERSTAT_OPTIONAL_PROVIDER_UNAVAILABLE,
    check_understat_optional_provider,
    get_understat_optional_provider_install_command,
)
import audit_understat_data_access as data_access_audit  # noqa: E402
import bootstrap_understat_optional_provider as bootstrap  # noqa: E402


PYTHON = sys.executable


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_provider_check_returns_unavailable_when_soccerdata_missing(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "soccerdata" else None)
    status = check_understat_optional_provider()
    assert status.installed is False
    assert status.provider_label == UNDERSTAT_OPTIONAL_PROVIDER_UNAVAILABLE


def test_provider_check_does_not_raise_when_soccerdata_missing(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    check_understat_optional_provider()


def test_install_command_uses_current_or_provided_python():
    assert sys.executable in get_understat_optional_provider_install_command()
    assert '"C:\\Python\\python.exe"' in get_understat_optional_provider_install_command("C:\\Python\\python.exe")


def test_bootstrap_print_command_does_not_install(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: called.append((args, kwargs)))
    rc = bootstrap.main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert "install_command=" in captured.out
    assert called == []


def test_bootstrap_install_uses_subprocess_with_optional_requirements(monkeypatch):
    calls = []

    class Completed:
        returncode = 0

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = bootstrap.main(["--install", "--python", "python"])
    assert rc == 0
    assert calls
    assert calls[0][0][:4] == ["python", "-m", "pip", "install"]
    assert "requirements-understat-optional.txt" in calls[0][0][-1]


def test_resolver_default_modes_remain_existing_local_raw_without_flags(tmp_path):
    result = resolve_understat_trusted_xg_source(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_dir=tmp_path / "raw")
    assert result.attempted_modes == ["existing", "local", "raw"]


def test_resolver_appends_optional_provider_when_allowed(tmp_path):
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        raw_dir=tmp_path / "raw",
        allow_optional_provider=True,
    )
    assert result.attempted_modes == ["existing", "local", "raw", "optional_provider"]


def test_resolver_appends_explicit_fetch_only_when_allow_network(tmp_path):
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        output_dir=tmp_path / "out",
        raw_dir=tmp_path / "raw",
        allow_optional_provider=True,
        allow_network=True,
    )
    assert result.attempted_modes == ["existing", "local", "raw", "optional_provider", "explicit_fetch"]
    no_network = resolve_understat_trusted_xg_source(league="Bundesliga", season=2024, output_dir=tmp_path / "out2", raw_dir=tmp_path / "raw2", allow_network=False)
    assert "explicit_fetch" not in no_network.attempted_modes


def test_explicit_modes_are_preserved_exactly(tmp_path):
    result = resolve_understat_trusted_xg_source(
        league="Bundesliga",
        season=2024,
        modes=["optional_provider"],
        output_dir=tmp_path / "out",
        raw_dir=tmp_path / "raw",
        allow_optional_provider=True,
        allow_network=True,
    )
    assert result.attempted_modes == ["optional_provider"]


def test_resolver_prints_install_command_when_optional_provider_unavailable():
    result = subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "resolve_understat_xg_source.py"),
            "--league",
            "Bundesliga",
            "--season",
            "2024",
            "--allow-optional-provider",
            "--output-dir",
            str(ROOT / "outputs" / "pytest_understat_optional"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "optional_provider_available=False" in result.stdout
    assert "install_command=" in result.stdout


def test_audit_understat_data_access_writes_optional_provider_status(tmp_path):
    table, markdown, rec = data_access_audit.run(root=tmp_path, output_dir=tmp_path / "out")
    assert table.empty
    assert "soccerdata installed:" in markdown
    assert "provider_label:" in markdown
    assert rec == "TRY_UNDERSTAT_OPTIONAL_PROVIDER_BOOTSTRAP"


def test_audit_can_recommend_try_understat_optional_provider_bootstrap(tmp_path):
    _table, _markdown, rec = data_access_audit.run(root=tmp_path, output_dir=tmp_path / "out")
    assert rec == "TRY_UNDERSTAT_OPTIONAL_PROVIDER_BOOTSTRAP"


def test_docs_mention_optional_understat_provider_bootstrap():
    text = (ROOT / "docs" / "manual_xg_workflow.md").read_text(encoding="utf-8")
    assert "Optional Understat Provider Bootstrap" in text
    assert "check_understat_optional_provider.py" in text


def test_requirements_txt_does_not_include_soccerdata():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "soccerdata" not in text
    optional = (ROOT / "requirements-understat-optional.txt").read_text(encoding="utf-8").lower()
    assert "soccerdata" in optional


def test_protected_model_probability_market_files_unchanged(tmp_path):
    protected = [
        ROOT / "src" / "football_prediction_v19" / "diagnostics" / "market_tier.py",
        ROOT / "src" / "football_prediction_v19" / "recommendation.py",
    ]
    before = {path: _sha(path) for path in protected if path.exists()}
    resolve_understat_trusted_xg_source(league="Bundesliga", season=2024, output_dir=tmp_path / "out", raw_dir=tmp_path / "raw", allow_optional_provider=True)
    after = {path: _sha(path) for path in protected if path.exists()}
    assert after == before
