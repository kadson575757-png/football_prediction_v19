# -*- coding: utf-8 -*-
"""Audit accepted trusted xG artifacts under data/trusted_xg_sources/accepted."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402

OUTPUT_CSV = "accepted_trusted_xg_artifacts_summary.csv"
OUTPUT_MD = "accepted_trusted_xg_artifacts_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-dir", default=str(ROOT / "data" / "trusted_xg_sources" / "accepted"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def _target_for_artifact(path: Path) -> Path | None:
    name = path.name.lower()
    if "bundesliga" in name and "2024" in name:
        target = ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"
        return target if target.exists() else None
    return None


def build_table(accepted_dir: str | Path) -> pd.DataFrame:
    root = Path(accepted_dir)
    if not root.is_absolute():
        root = ROOT / root
    rows = []
    for artifact in sorted(root.glob("*.csv")) if root.exists() else []:
        target = _target_for_artifact(artifact)
        try:
            df = pd.read_csv(artifact, low_memory=False)
            if target is not None:
                acceptance = run_manual_xg_acceptance_gate(
                    artifact,
                    target_path=target,
                    output_dir=ROOT / "outputs" / "xg_acceptance_preview",
                    min_join_coverage=100.0,
                    write_preview=True,
                )
                label = acceptance.acceptance_label
                coverage = acceptance.join_coverage_pct
                rows_valid = acceptance.rows_valid
            else:
                required = {"date", "home_team", "away_team", "home_xg", "away_xg"}
                label = "MANUAL_XG_ACCEPTED" if required.issubset(df.columns) and df[["home_xg", "away_xg"]].notna().all().all() else "INVALID_SCHEMA"
                coverage = 0.0
                rows_valid = len(df) if label == "MANUAL_XG_ACCEPTED" else 0
            status = "READY" if label == "MANUAL_XG_ACCEPTED" else "BLOCKED"
        except Exception as exc:
            df = pd.DataFrame()
            target = target or Path("")
            label = str(exc)
            coverage = 0.0
            rows_valid = 0
            status = "BLOCKED"
        rows.append({
            "artifact_path": artifact.relative_to(ROOT).as_posix() if artifact.is_relative_to(ROOT) else artifact.name,
            "target_path": target.relative_to(ROOT).as_posix() if target and target.exists() and target.is_relative_to(ROOT) else "",
            "rows": int(len(df)),
            "rows_valid": int(rows_valid),
            "join_coverage_pct": float(coverage),
            "validation_label": label,
            "artifact_status": status,
        })
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "ADD_ACCEPTED_TRUSTED_XG_ARTIFACT"
    if table["artifact_status"].eq("BLOCKED").any():
        return "FIX_ACCEPTED_TRUSTED_XG_ARTIFACT"
    return "ACCEPTED_TRUSTED_XG_ARTIFACTS_READY"


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Accepted Trusted xG Artifacts Audit",
        "",
        "Phase 13.12 is diagnostic/foundation only. xG remains inactive in model features.",
        "",
        "## Summary",
    ]
    if table.empty:
        lines.append("No accepted artifacts found.")
    else:
        cols = list(table.columns)
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for _idx, row in table.iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    lines += ["", "## Recommendation", rec, ""]
    return "\n".join(lines)


def run(accepted_dir: str | Path | None = None, output_dir: str | Path | None = None) -> tuple[pd.DataFrame, str, str]:
    table = build_table(accepted_dir or (ROOT / "data" / "trusted_xg_sources" / "accepted"))
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    out = Path(output_dir or (ROOT / "outputs" / "diagnostics"))
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(args.accepted_dir, args.output_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
