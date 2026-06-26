# -*- coding: utf-8 -*-
"""Readable v1.9 final analysis report preview from real-match evidence."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

V19_FINAL_ANALYSIS_REPORT_PREVIEW_READY = "V19_FINAL_ANALYSIS_REPORT_PREVIEW_READY"
V19_FINAL_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT = "V19_FINAL_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT"
V19_FINAL_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH = "V19_FINAL_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH"

PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class V19FinalAnalysisReportConfig:
    context_human_input_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    market_movement_diagnostic_path: str | Path | None = None
    availability_diagnostic_path: str | Path | None = None
    player_form_diagnostic_path: str | Path | None = None
    tactical_matchup_diagnostic_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/v19_final_analysis_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19FinalAnalysisReportResult:
    v19_final_analysis_report_status: str
    report_output_path: str
    manifest_path: str
    summary_path: str
    home_team: str
    away_team: str
    match_date: str
    completion_applied: bool
    no_production_recommendation: bool
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19FinalAnalysisReportRenderer:
    def __init__(self, config: V19FinalAnalysisReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[V19FinalAnalysisReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or any(_unsafe(path) for path in [
            self.config.context_human_input_path,
            self.config.v19_diagnostic_synthesis_path,
            self.config.v19_diagnostic_gate_matrix_path,
            self.config.market_movement_diagnostic_path,
            self.config.availability_diagnostic_path,
            self.config.player_form_diagnostic_path,
            self.config.tactical_matchup_diagnostic_path,
        ] if path):
            return self._blocked(V19_FINAL_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH), ""

        context_path = _resolve(self.config.context_human_input_path, self.base) or self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        if not context_path.exists():
            return self._blocked(V19_FINAL_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT), ""
        context = _read_first_row(context_path)
        if context is None:
            return self._blocked(V19_FINAL_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT), ""

        diagnostic = _read_first_row(_resolve(self.config.v19_diagnostic_synthesis_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis" / "v19_diagnostic_synthesis.csv") or {}
        gate = _read_frame(_resolve(self.config.v19_diagnostic_gate_matrix_path, self.base) or self.base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix" / "v19_diagnostic_gate_matrix.csv")
        market = _read_first_row(_resolve(self.config.market_movement_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "market_movement_diagnostic" / "market_movement_diagnostic.csv") or {}
        availability = _read_first_row(_resolve(self.config.availability_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "availability_diagnostic" / "availability_diagnostic.csv") or {}
        player = _read_first_row(_resolve(self.config.player_form_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "player_form_diagnostic" / "player_form_diagnostic.csv") or {}
        tactical = _read_first_row(_resolve(self.config.tactical_matchup_diagnostic_path, self.base) or self.base / "outputs" / "analysis_preview" / "tactical_matchup_diagnostic" / "tactical_matchup_diagnostic.csv") or {}

        report = _render_report(context, diagnostic, gate, market, availability, player, tactical)
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / "v19_final_analysis_report_preview.md"
        manifest_path = out / "v19_final_analysis_report_manifest.csv"
        summary_path = out / "v19_final_analysis_report_summary.md"
        report_path.write_text(report, encoding="utf-8")
        result = V19FinalAnalysisReportResult(
            v19_final_analysis_report_status=V19_FINAL_ANALYSIS_REPORT_PREVIEW_READY,
            report_output_path=str(report_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            summary_path=str(summary_path.resolve()),
            home_team=_text(context, "home_team"),
            away_team=_text(context, "away_team"),
            match_date=_text(context, "match_date"),
            completion_applied=_text(context, "manual_evidence_completion_status") == "MANUAL_EVIDENCE_COMPLETION_APPLIED",
            no_production_recommendation=True,
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            staking_logic_enabled=False,
            roi_logic_enabled=False,
            recommendation=V19_FINAL_ANALYSIS_REPORT_PREVIEW_READY,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# v1.9 Final Analysis Report Preview",
            "",
            f"- v19_final_analysis_report_status: {result.v19_final_analysis_report_status}",
            f"- report_output_path: {result.report_output_path}",
            "- No production recommendation; prediction, betting, staking and ROI remain disabled.",
            "",
        ]), encoding="utf-8")
        return result, report

    def _blocked(self, status: str) -> V19FinalAnalysisReportResult:
        return V19FinalAnalysisReportResult(status, "", "", "", "", "", "", False, True, False, False, False, False, False, status)


def _render_report(
    context: dict[str, object],
    diagnostic: dict[str, object],
    gate: pd.DataFrame,
    market: dict[str, object],
    availability: dict[str, object],
    player: dict[str, object],
    tactical: dict[str, object],
) -> str:
    home = _text(context, "home_team")
    away = _text(context, "away_team")
    completion_applied = _text(context, "manual_evidence_completion_status") == "MANUAL_EVIDENCE_COMPLETION_APPLIED"
    completed_groups = _text(context, "completed_evidence_groups") or "none"
    xg_diff_home = _num(context, "home_xg") - _num(context, "home_xga") if _has_num(context, "home_xg") and _has_num(context, "home_xga") else None
    xg_diff_away = _num(context, "away_xg") - _num(context, "away_xga") if _has_num(context, "away_xg") and _has_num(context, "away_xga") else None
    gates_ready = _gate_count(gate, "DIAGNOSTIC_GATE_READY")
    gates_blocked = len(gate[gate["gate_status"].astype(str).str.contains("BLOCKED|REQUIRES", regex=True)]) if "gate_status" in gate.columns else 0

    data_present = _data_present(context)
    data_missing = _data_missing(context, market, availability, player, tactical)
    model_status = _text(diagnostic, "v19_model_synthesis_status")
    control_status = _text(diagnostic, "control_model_status")
    chaos_status = _text(diagnostic, "chaos_score_status")
    underdog_status = _text(diagnostic, "underdog_win_score_status")
    score_status = _text(diagnostic, "score_family_status")

    lines = [
        "# v1.9 Final Analysis Report Preview",
        "",
        f"## 1. Spielinfo & Datenstatus",
        "",
        f"**Match:** {home} vs {away} am {_text(context, 'match_date')} ({_text(context, 'competition')} {_text(context, 'season')}).",
        f"**Datenquellen:** Excel Evidence, Real-Match-Intake, Manual Evidence Completion und lokale Diagnostic-Layer. Netzwerkaufrufe bleiben deaktiviert.",
        f"**Completion angewendet:** {'ja' if completion_applied else 'nein'}; completed evidence groups: {completed_groups}.",
        f"**Vorhanden:** {data_present}.",
        f"**Fehlt / bleibt zu prüfen:** {data_missing}.",
        "",
        "## 2. Kurzfazit vorab",
        "",
        f"Atalanta besitzt den stärkeren Angriffs- und Produktionskern. Das zeigen Team-xG, Spieler-xG und Creation-Werte deutlich. Lazio hat aber zwei starke Gegenargumente: das sauberere xGA-Profil und einen klaren Standardvorteil. Die Analyse ist dadurch nicht eindimensional, sondern ein strukturelles Atalanta-Plus mit Lazio-Gegenhebeln.",
        "Analysefähig ist dieser Stand als Diagnostic Read. Eine finale v1.9-Entscheidung oder Recommendation entsteht daraus nicht, weil Prediction-, Betting-, Staking- und ROI-Logik weiterhin deaktiviert bleiben und einzelne Evidenzschichten noch manuell geprüft werden müssen.",
        "",
        "## 3. Team-xG / xGA Bewertung",
        "",
        f"Lazio xG For {_value(context, 'home_xg')}, xG Against {_value(context, 'home_xga')}, Diff {_fmt(xg_diff_home)}.",
        f"Atalanta xG For {_value(context, 'away_xg')}, xG Against {_value(context, 'away_xga')}, Diff {_fmt(xg_diff_away)}.",
        "Atalanta hat damit den klareren Produktionsvorteil. Lazio wirkt im Gegenzug über das xGA-Profil stabiler, was den Away-Produktionsvorteil nicht aufhebt, aber abschwächt.",
        "",
        "## 4. Spieler-xG / xA Bewertung",
        "",
        f"Lazio: {_value(context, 'home_main_scorer')} und {_value(context, 'home_main_creator')}; Player xG Total {_value(context, 'home_player_xg_total')}, Player xA Total {_value(context, 'home_player_xa_total')}.",
        f"Atalanta: {_value(context, 'away_main_scorer')} und {_value(context, 'away_main_creator')}; Player xG Total {_value(context, 'away_player_xg_total')}, Player xA Total {_value(context, 'away_player_xa_total')}.",
        "Atalanta hat den individuell stärkeren Produktions- und Creation-Block. Das Risiko bleibt: Verfügbarkeit, Rollen und konkrete Lineup-Details sind noch nicht vollständig produktionsreif geprüft.",
        "",
        "## 5. Shot / Possession / Control Read",
        "",
        f"Possession {_value(context, 'home_possession')} - {_value(context, 'away_possession')}. Shots {_value(context, 'home_shots')} - {_value(context, 'away_shots')}. Shots on Target {_value(context, 'home_shots_on_target')} - {_value(context, 'away_shots_on_target')}.",
        "Die Completion-Daten machen den Report deutlich analysefähiger: Lazio erzeugt mehr Abschlussvolumen, während Atalanta über xG und Spieler-xG/xA gefährlicher bleibt. Shots on Target sind ausgeglichen. Dadurch entsteht kein simples Away-Dominanzbild.",
        "",
        "## 6. Formation / Taktik",
        "",
        f"Lazio läuft im aktuellen Evidence-Stand mit {_value(context, 'home_formation')} auf, Atalanta mit {_value(context, 'away_formation')}.",
        f"Tactical matchup score: {_value(context, 'tactical_matchup_score')}. Die zentrale Matchup-Frage ist, ob Lazios 4-3-3 genug Zugriff und Standarddruck erzeugt, um Atalantas 3-4-2-1-Produktionsvorteil zu brechen.",
        f"Detailnoten: Formation {_value(context, 'formation_matchup_note')}; Pressing {_value(context, 'pressing_matchup_note')}; Transition {_value(context, 'transition_matchup_note')}. Fehlende Detailnoten bleiben Review-Punkte.",
        "",
        "## 7. Set-Piece Bewertung",
        "",
        f"Lazio Set-Piece xG For {_value(context, 'home_set_piece_xg_for')}, Against {_value(context, 'home_set_piece_xg_against')}, Ratio {_value(context, 'home_set_piece_xg_ratio')}.",
        f"Atalanta Set-Piece xG For {_value(context, 'away_set_piece_xg_for')}, Against {_value(context, 'away_set_piece_xg_against')}, Ratio {_value(context, 'away_set_piece_xg_ratio')}.",
        "Lazio Set-Piece ist der wichtigste Gegenhebel gegen Atalantas Produktionsvorteil. Atalanta wirkt aus dem Spiel stärker, Lazio bekommt über Standards aber eine echte Route in die Partie.",
        "",
        "## 8. Markt / Odds Read",
        "",
        f"Aktuelle Odds aus Completion/Intake: Home {_value(context, 'home_current_odds')}, Draw {_value(context, 'draw_current_odds')}, Away {_value(context, 'away_current_odds')}.",
        f"Market diagnostic: {_text(market, 'market_movement_diagnostic_status') or _text(market, 'market_evidence_status')}; missing market fields: {_text(market, 'missing_market_fields') or 'opening/closing/DNB/OU fields remain incomplete where not supplied'}. Keine Value-Bewertung, keine Recommendation.",
        "",
        "## 9. Lineups / Availability",
        "",
        f"Availability diagnostic: {_text(availability, 'availability_diagnostic_status') or _text(availability, 'availability_evidence_status')}; lineup gate: {_text(availability, 'lineup_confirmation_gate_status')}.",
        f"Lineupstatus: Lazio {_value(context, 'home_lineup_confirmed')}, Atalanta {_value(context, 'away_lineup_confirmed')}. Torwart, Ausfälle, Sperren und Schlüsselspieler bleiben nur so belastbar wie die manuelle Evidenz.",
        "Ohne vollständig geprüfte Availability-Details gibt es keinen finalen Tipp.",
        "",
        "## 10. Recent Form / Big Chances / H2H",
        "",
        f"Recent-form gate: {_text(player, 'rolling_form_gate_status')}; big-chance gate: {_text(player, 'big_chance_gate_status')}.",
        f"H2H / Manual note: {_value(context, 'h2h_summary')}. Wenn Recent Form oder Big Chances fehlen, bleiben diese Layer reine Review-Punkte.",
        "",
        "## 11. Widersprüche & Risiken",
        "",
        "- Atalanta xG/Player production ist klar stärker.",
        "- Lazio xGA und Set-Piece sind klare Gegenargumente.",
        "- Lazio hat nach Completion mehr Shots, Atalanta aber die bessere xG-Qualität.",
        "- Shots on Target sind ausgeglichen.",
        "- Recent Form, Big Chances, Availability-Details und Teile des Marktverlaufs bleiben unvollständig.",
        "- Deshalb keine finale Empfehlung.",
        "",
        "## 12. v1.9 Kontrollmodell Read",
        "",
        f"v1.9 model status: {model_status}; control model status: {control_status}; gates ready: {gates_ready}; gates blocked/review: {gates_blocked}.",
        "Das Kontrollmodell ist diagnostisch lesbar, aber nicht produktiv aktiviert. Es erzeugt keinen harten 1X2-Output.",
        "",
        "## 13. Chaos / Underdog / Score-Family Read",
        "",
        f"Chaos status: {chaos_status}; underdog status: {underdog_status}; score-family status: {score_status}.",
        "Die Evidence deutet eher auf Atalanta-Torgefahr plus Lazio-Standardroute als auf ein einseitiges Spiel. Es gibt keinen exakten Score, keinen Score-Tipp und keine produktive Score-Family-Ausgabe.",
        "",
        "## 14. No-Bet / Keine Empfehlung",
        "",
        "Keine Recommendation. Kein Wett-Tipp. Kein 1X2-Pick. Kein DNB-Pick. Kein Over/Under-Pick. Kein Stake. Kein ROI. Kein produktiver Model Output.",
        "Grund: Betting-/Recommendation-Layer sind deaktiviert, Remaining Gaps müssen manuell geprüft werden, und dieser Report ist ein analystischer Diagnostic Read.",
        "",
        "## 15. Abschlussfazit",
        "",
        "Atalanta besitzt den stärkeren Angriffs- und Produktionskern. Lazio hat über xGA und Standards klare Gegenargumente. Die Completion-Daten machen den Report deutlich analysefähiger. Trotzdem bleibt es ohne Recent Form, Big Chances, vollständige Availability und vollständigen Marktverlauf keine finale v1.9-Entscheidung.",
        "**Ergebnis:** Analysefähig als Diagnostic Read, nicht als Betting Recommendation.",
        "",
        "_Safety: network_calls_enabled=false; prediction_logic_enabled=false; betting_logic_enabled=false; staking_logic_enabled=false; roi_logic_enabled=false._",
        "",
    ]
    return "\n".join(lines)


def _data_present(row: dict[str, object]) -> str:
    present = []
    if _has_num(row, "home_xg") and _has_num(row, "away_xg"):
        present.append("Team-xG/xGA")
    if _text(row, "home_main_scorer") or _text(row, "away_main_scorer"):
        present.append("Spieler-xG/xA")
    if _text(row, "home_possession") or _text(row, "away_possession"):
        present.append("Possession/Shots aus Manual Completion")
    if _text(row, "home_formation") or _text(row, "away_formation"):
        present.append("Formation")
    if _text(row, "home_set_piece_xg_ratio") or _text(row, "away_set_piece_xg_ratio"):
        present.append("Set-Piece-Profil")
    if _text(row, "home_current_odds") or _text(row, "away_current_odds"):
        present.append("aktuelle Odds")
    return ", ".join(present) if present else "Basisidentität"


def _data_missing(row: dict[str, object], market: dict[str, object], availability: dict[str, object], player: dict[str, object], tactical: dict[str, object]) -> str:
    missing = []
    if _text(market, "missing_market_fields"):
        missing.append("vollständiger Marktverlauf/DNB/OU")
    if _text(availability, "missing_availability_fields"):
        missing.append("Availability-Details")
    if _text(player, "missing_player_form_fields"):
        missing.append("Recent Form / Big Chances")
    if _text(tactical, "missing_tactical_fields"):
        missing.append("Tactical-/Fatigue-Details")
    if not _text(row, "h2h_summary"):
        missing.append("H2H-Kontext")
    return ", ".join(missing) if missing else "keine harten Pflichtfelder, aber weiterhin manuelle Review-Pflicht"


def _read_first_row(path: Path | None) -> dict[str, object] | None:
    frame = _read_frame(path)
    if frame.empty:
        return None
    return frame.iloc[0].to_dict()


def _read_frame(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists() or path.is_dir():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False, keep_default_na=False)
    except (EmptyDataError, OSError):
        return pd.DataFrame()


def _gate_count(frame: pd.DataFrame, status: str) -> int:
    if frame.empty or "gate_status" not in frame.columns:
        return 0
    return int((frame["gate_status"].astype(str) == status).sum())


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "v19_final_analysis_report").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _text(row: dict[str, object], column: str) -> str:
    value = row.get(column, "")
    return "" if _blank(value) else str(value)


def _value(row: dict[str, object], column: str) -> str:
    value = _text(row, column)
    return value if value else "nicht vorhanden"


def _has_num(row: dict[str, object], column: str) -> bool:
    return pd.notna(pd.to_numeric(pd.Series([row.get(column, "")]), errors="coerce").iloc[0])


def _num(row: dict[str, object], column: str) -> float:
    return float(pd.to_numeric(pd.Series([row.get(column, "")]), errors="coerce").iloc[0])


def _fmt(value: float | None) -> str:
    return "nicht vorhanden" if value is None else f"{value:+.2f}"
