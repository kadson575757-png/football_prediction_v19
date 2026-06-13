# -*- coding: utf-8 -*-
"""Inspect a saved Understat raw fetch without fetching network data."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_fetch import (  # noqa: E402
    detect_understat_html_state,
    extract_understat_runtime_data_endpoints,
)


def script_srcs(html: str) -> list[str]:
    return re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_path = Path(args.raw_path)
    html = raw_path.read_text(encoding="utf-8", errors="replace")
    endpoints = extract_understat_runtime_data_endpoints(html)
    srcs = script_srcs(html)
    print(f"file_size={raw_path.stat().st_size}")
    print(f"html_state={detect_understat_html_state(html)}")
    print(f"has_datesData={'datesData' in html}")
    print(f"has_teamsData={'teamsData' in html}")
    print(f"has_matchesData={'matchesData' in html}")
    print(f"script_srcs_found={len(srcs)}")
    for src in srcs[:20]:
        print(f"script_src={src}")
    print(f"candidate_runtime_endpoints_found={len(endpoints)}")
    for endpoint in endpoints[:5]:
        print(f"candidate_endpoint={endpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
