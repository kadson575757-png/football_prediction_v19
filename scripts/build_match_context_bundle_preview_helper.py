# -*- coding: utf-8 -*-
"""Build and audit preview-only Understat + FBref match context bundle."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_match_context_bundle_preview import run as run_audit  # noqa: E402
from build_fbref_match_finder_preview_helper import run_workflow as run_fbref_match_finder  # noqa: E402
from build_fbref_provider_pull_preview import build_fbref_provider_pull_preview  # noqa: E402
from build_match_context_bundle_preview import build_match_context_bundle_preview  # noqa: E402
from build_understat_real_snapshot_smoke_preview_helper import run_workflow as run_understat_smoke  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def run_workflow(base_dir: str | Path = ROOT) -> dict[str, object]:
    base = Path(base_dir).resolve()
    understat = run_understat_smoke(base)
    fbref = build_fbref_provider_pull_preview(local_input=ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json", output_dir=base / "outputs" / "provider_pull_preview" / "fbref", base_dir=base)
    fbref_finder = run_fbref_match_finder(base)
    bundle = build_match_context_bundle_preview(
        understat_normalized_input=understat.get("normalized_output_path"),
        fbref_normalized_input=fbref.get("normalized_output_path"),
        cross_provider_match_key="u-bundesliga-2024-001",
        output_dir=base / "outputs" / "analysis_preview" / "match_context_bundle",
        base_dir=base,
        build_missing=False,
    )
    _table, _markdown, rec = run_audit(manifest=bundle.get("manifest_path") or None, output_dir=base / "outputs" / "diagnostics", base_dir=base)
    return {
        **bundle,
        "understat_status": understat.get("understat_real_snapshot_smoke_status", understat.get("real_snapshot_status", "")),
        "fbref_provider_pull_status": fbref.get("fbref_provider_pull_status", ""),
        "fbref_match_finder_status": fbref_finder.get("fbref_match_finder_status", ""),
        "recommendation": rec,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.base_dir)
    for key in ["match_context_bundle_status", "understat_status", "fbref_provider_pull_status", "fbref_match_finder_status", "rows_joined", "candidates_matched", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        actual_key = "context_bundle_status" if key == "match_context_bundle_status" else key
        value = summary.get(actual_key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
