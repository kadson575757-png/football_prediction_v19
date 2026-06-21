# -*- coding: utf-8 -*-
"""Build and audit offline FBref match finder preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_fbref_match_finder_preview import run as run_audit  # noqa: E402
from build_fbref_provider_pull_preview import build_fbref_provider_pull_preview  # noqa: E402
from find_fbref_match_preview import find_fbref_match_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir)
    provider = build_fbref_provider_pull_preview(
        base_dir=base,
        local_input=ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json",
        output_dir=base / "outputs" / "provider_pull_preview" / "fbref",
    )
    finder = find_fbref_match_preview(
        provider_match_id="fbref-bundesliga-2024-001",
        base_dir=base,
        normalized_input=provider.get("normalized_output_path"),
        output_dir=base / "outputs" / "provider_pull_preview" / "fbref" / "match_finder",
    )
    _table, _markdown, rec = run_audit(manifest=finder.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {**provider, **finder, "recommendation": rec}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in ["fbref_provider_pull_status", "fbref_match_finder_status", "provider", "competition", "season", "rows_normalized", "candidates_matched", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
