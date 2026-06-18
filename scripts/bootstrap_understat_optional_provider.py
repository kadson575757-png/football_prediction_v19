# -*- coding: utf-8 -*-
"""Print or explicitly run optional soccerdata Understat provider install."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements-understat-optional.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-install-command", action="store_true", default=True)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    return parser


def install_command(python_executable: str) -> list[str]:
    return [python_executable, "-m", "pip", "install", "-r", str(REQ)]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = install_command(args.python)
    print("This installs optional dependencies only. It does not change model behavior.")
    print("install_command=" + " ".join(f'"{part}"' if " " in part else part for part in command))
    if args.install:
        completed = subprocess.run(command, cwd=ROOT, check=False)
        return int(completed.returncode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
