# -*- coding: utf-8 -*-
"""Materialize an accepted trusted xG artifact after validation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402

ACCEPTED_TRUSTED_XG_ARTIFACT_READY = "ACCEPTED_TRUSTED_XG_ARTIFACT_READY"
ACCEPTED_TRUSTED_XG_ARTIFACT_WRITTEN = "ACCEPTED_TRUSTED_XG_ARTIFACT_WRITTEN"
ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_MISSING_XG = "ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_MISSING_XG"
ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_LOW_COVERAGE = "ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_LOW_COVERAGE"
ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_UNSAFE_PATH = "ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_UNSAFE_PATH"
ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA = "ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filled-preview", required=True)
    parser.add_argument("--accepted-output", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--source-name", default=None)
    parser.add_argument("--min-join-coverage", type=float, default=100.0)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def _repo_relative(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("ACCEPTED_OUTPUT_OUTSIDE_REPO") from exc


def _safe_accepted_output(path: str | Path) -> tuple[Path, str]:
    rel = _repo_relative(path)
    normalized = rel.replace("\\", "/")
    if normalized.startswith("outputs/") or normalized == "outputs":
        raise ValueError("ACCEPTED_OUTPUT_UNDER_OUTPUTS")
    prefix = "data/trusted_xg_sources/accepted/"
    if not normalized.startswith(prefix) or not normalized.lower().endswith(".csv"):
        raise ValueError("ACCEPTED_OUTPUT_MUST_BE_UNDER_DATA_TRUSTED_XG_SOURCES_ACCEPTED")
    return (ROOT / normalized).resolve(), normalized


def _xg_validation_status(df: pd.DataFrame) -> str | None:
    required = {"date", "home_team", "away_team", "home_xg", "away_xg"}
    if not required.issubset(df.columns):
        return ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA
    raw = df[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    if missing.any().any():
        return ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_MISSING_XG
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or (numeric < 0).any().any():
        return ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA
    return None


def materialize_accepted_trusted_xg_artifact(
    filled_preview: str | Path,
    accepted_output: str | Path,
    target: str | Path,
    *,
    league: str | None = None,
    season: str | None = None,
    source_name: str | None = None,
    min_join_coverage: float = 100.0,
    write: bool = False,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
) -> dict[str, Any]:
    try:
        accepted_path, accepted_rel = _safe_accepted_output(accepted_output)
    except ValueError as exc:
        summary = {
            "materialization_status": ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_UNSAFE_PATH,
            "rows_written": 0,
            "accepted_output_path": "",
            "join_coverage_pct": 0.0,
            "validation_label": "",
            "blocking_reasons": str(exc),
        }
        _write_diagnostics(summary, output_dir)
        return summary

    try:
        df = pd.read_csv(filled_preview, low_memory=False)
    except Exception as exc:
        summary = {
            "materialization_status": ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA,
            "rows_written": 0,
            "accepted_output_path": accepted_rel,
            "join_coverage_pct": 0.0,
            "validation_label": "",
            "blocking_reasons": str(exc),
        }
        _write_diagnostics(summary, output_dir)
        return summary

    status = _xg_validation_status(df)
    acceptance = run_manual_xg_acceptance_gate(
        filled_preview,
        target_path=target,
        output_dir=Path(output_dir) / "accepted_artifact_acceptance_preview",
        min_join_coverage=min_join_coverage,
        write_preview=True,
    )
    if status is None and acceptance.join_coverage_pct < min_join_coverage:
        status = ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_LOW_COVERAGE
    if status is None and acceptance.acceptance_label != "MANUAL_XG_ACCEPTED":
        status = ACCEPTED_TRUSTED_XG_ARTIFACT_BLOCKED_INVALID_SCHEMA
    rows_written = 0
    if status is None:
        status = ACCEPTED_TRUSTED_XG_ARTIFACT_WRITTEN if write else ACCEPTED_TRUSTED_XG_ARTIFACT_READY
        if write:
            accepted_path.parent.mkdir(parents=True, exist_ok=True)
            out = df.copy()
            if "league" in out.columns and league is not None:
                out["league"] = league
            if "season" in out.columns and season is not None:
                out["season"] = season
            if "source_name" in out.columns and source_name is not None:
                out["source_name"] = source_name
            out.to_csv(accepted_path, index=False)
            rows_written = int(len(out))
    summary = {
        "materialization_status": status,
        "rows_written": rows_written,
        "accepted_output_path": accepted_rel,
        "join_coverage_pct": float(acceptance.join_coverage_pct),
        "validation_label": acceptance.acceptance_label,
        "blocking_reasons": " | ".join(acceptance.blocking_reasons),
    }
    _write_diagnostics(summary, output_dir)
    return summary


def _write_diagnostics(summary: dict[str, Any], output_dir: str | Path) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(root / "accepted_trusted_xg_artifact_materialization_summary.csv", index=False)
    lines = [
        "# Accepted Trusted xG Artifact Materialization",
        "",
        "Phase 13.12 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    (root / "accepted_trusted_xg_artifact_materialization_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = materialize_accepted_trusted_xg_artifact(
        args.filled_preview,
        args.accepted_output,
        args.target,
        league=args.league,
        season=args.season,
        source_name=args.source_name,
        min_join_coverage=args.min_join_coverage,
        write=args.write,
        output_dir=args.output_dir,
    )
    print(f"materialization_status={summary['materialization_status']}")
    print(f"rows_written={summary['rows_written']}")
    print(f"accepted_output_path={summary['accepted_output_path']}")
    print(f"join_coverage_pct={summary['join_coverage_pct']}")
    print(f"validation_label={summary['validation_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
