# -*- coding: utf-8 -*-
"""User-facing German-style real match report preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY = "USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY"
USER_FACING_REAL_MATCH_REPORT_BLOCKED_MISSING_INPUT = "USER_FACING_REAL_MATCH_REPORT_BLOCKED_MISSING_INPUT"
USER_FACING_REAL_MATCH_REPORT_NO_BETTING_OUTPUT_BY_DESIGN = "USER_FACING_REAL_MATCH_REPORT_NO_BETTING_OUTPUT_BY_DESIGN"


@dataclass(frozen=True)
class UserFacingRealMatchReportConfig:
    human_24_block_report_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/user_facing_real_match_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class UserFacingRealMatchReportResult:
    user_facing_real_match_report_status: str
    sections_rendered: int
    required_sections_rendered: int
    missing_optional_fields_visible: bool
    no_bet_section_rendered: bool
    final_betting_tips_rendered: bool
    stake_units_rendered: bool
    roi_rendered: bool
    super_a_promotion_rendered: bool
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str


class UserFacingRealMatchReportBuilder:
    def __init__(self, config: UserFacingRealMatchReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> UserFacingRealMatchReportResult:
        source = _resolve(self.config.human_24_block_report_path, self.base) or self.base / "outputs" / "analysis_preview" / "human_24_block_report" / "human_24_block_match_report_preview.md"
        if not source.exists():
            return self._blocked(USER_FACING_REAL_MATCH_REPORT_BLOCKED_MISSING_INPUT)
        text = source.read_text(encoding="utf-8")
        sections = _sections(text)
        out = _safe_output(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        output = out / "user_facing_real_match_report.md"
        summary = out / "user_facing_real_match_report_summary.md"
        manifest = out / "user_facing_real_match_report_manifest.csv"
        body = _render(sections)
        output.write_text(body, encoding="utf-8")
        lower = body.lower()
        result = UserFacingRealMatchReportResult(
            USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY,
            len(sections), len(sections),
            "missing" in lower or "not provided" in lower or "not executed" in lower,
            "no-bet" in lower or "keine finale wettempfehlung" in lower,
            "final betting tip" in lower,
            "stake size" in lower or "unit stake" in lower,
            "roi:" in lower,
            "promote to super_a" in lower or "super_a_tier activated" in lower,
            str(output.resolve()), str(summary.resolve()), str(manifest.resolve()),
            USER_FACING_REAL_MATCH_REPORT_PREVIEW_READY,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest, index=False)
        summary.write_text("\n".join([
            "# User-Facing Real Match Report Preview", "",
            f"- user_facing_real_match_report_status: {result.user_facing_real_match_report_status}",
            f"- sections_rendered: {result.sections_rendered}",
            "- Keine finale Wettempfehlung - Preview/Diagnostic only", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str) -> UserFacingRealMatchReportResult:
        return UserFacingRealMatchReportResult(status, 0, 0, False, False, False, False, False, False, "", "", "", status)


def _sections(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    current = ""
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                result[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current:
            buf.append(line)
    if current:
        result[current] = "\n".join(buf).strip()
    return result


def _render(sections: dict[str, str]) -> str:
    lines = [
        "# Real Match Analyse Preview",
        "",
        "**Keine finale Wettempfehlung - Preview/Diagnostic only.**",
        "",
        "Diese Vorschau zeigt Datenqualitaet, Markt-, Availability-, Player/Form- und Tactical-Evidenz. Fehlende optionale Werte bleiben sichtbar und werden nicht gefuellt.",
        "",
    ]
    for idx, (name, body) in enumerate(sections.items(), start=1):
        lines.extend([f"## {idx:02d}. {name}", "", body or "not provided", ""])
    lines.extend([
        "## Safety / No-Bet",
        "",
        "Keine finale Wettempfehlung - Preview/Diagnostic only. Kein Stake, keine Units, kein ROI, keine SUPER_A Promotion.",
        "",
    ])
    return "\n".join(lines)


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safe_output(output_dir: str | Path, base: Path) -> Path:
    out = Path(output_dir)
    return (base / out).resolve() if not out.is_absolute() else out.resolve()
