# -*- coding: utf-8 -*-
"""Check optional soccerdata Understat provider availability."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_optional_provider import (  # noqa: E402
    check_understat_optional_provider,
    get_understat_optional_provider_install_command,
    get_understat_optional_provider_usage_notes,
)


def main() -> int:
    status = check_understat_optional_provider()
    print(f"installed={status.installed}")
    print(f"provider_label={status.provider_label}")
    print(f"version={status.version}")
    print(f"import_error={status.import_error}")
    print(f"available_classes={' | '.join(status.available_classes)}")
    print(f"install_command={get_understat_optional_provider_install_command()}")
    print(f"usage_notes={' | '.join(get_understat_optional_provider_usage_notes())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
