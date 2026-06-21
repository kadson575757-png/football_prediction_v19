# -*- coding: utf-8 -*-
"""Build and audit offline FBref provider pull preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_fbref_provider_pull_preview import run as run_audit  # noqa: E402
from build_fbref_provider_pull_preview import build_fbref_provider_pull_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "fbref"))
    return parser


def run_workflow(output_dir: str | Path) -> dict[str, object]:
    base_dir = _base_from_output_dir(output_dir)
    fixture = ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json"
    summary = build_fbref_provider_pull_preview(competition="Bundesliga", season="2024", local_input=fixture, output_dir=output_dir, allow_network=False, write_preview=True, base_dir=base_dir)
    _table, _markdown, rec = run_audit(manifest=summary.get("manifest_path") or None, output_dir=base_dir / "outputs" / "diagnostics", base_dir=base_dir)
    return {**summary, "recommendation": rec}


def _base_from_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    parts = path.parts
    if "outputs" in parts:
        idx = parts.index("outputs")
        return Path(*parts[:idx]) if idx > 0 else Path(".").resolve()
    return ROOT


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.output_dir)
    for key in ["fbref_provider_pull_status", "provider", "competition", "season", "rows_normalized", "network_calls_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
