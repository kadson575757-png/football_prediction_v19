# -*- coding: utf-8 -*-
"""Controlled Understat data-access fallback resolver.

Phase 13.7 diagnostic/foundation only. This module never infers, estimates, or
invents xG values. It only normalizes real xG values from explicit local files,
existing trusted sources, raw saved Understat payloads, an explicitly enabled
optional provider, or an explicitly enabled fetch CLI path.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.understat_fetch import (
    UNDERSTAT_FETCH_READY,
    detect_understat_html_state,
    fetch_understat_league_season,
    normalize_understat_matches_to_trusted_xg,
    parse_understat_matches_from_html,
    parse_understat_matches_from_runtime_payload,
)
from football_prediction_v19.importers.understat_optional_provider import (
    check_understat_optional_provider,
    get_understat_optional_provider_install_command,
    load_soccerdata_understat_provider,
    normalize_soccerdata_understat_output,
)
from football_prediction_v19.importers.understat_trusted_xg import (
    OUTPUT_COLUMNS,
    _normalize_by_schema,
    load_understat_export,
)

UNDERSTAT_ACCESS_READY = "UNDERSTAT_ACCESS_READY"
UNDERSTAT_ACCESS_BLOCKED_NO_INPUT = "UNDERSTAT_ACCESS_BLOCKED_NO_INPUT"
UNDERSTAT_ACCESS_BLOCKED_NO_LOCAL_SOURCE = "UNDERSTAT_ACCESS_BLOCKED_NO_LOCAL_SOURCE"
UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED = "UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED"
UNDERSTAT_ACCESS_BLOCKED_OPTIONAL_PROVIDER_UNAVAILABLE = "UNDERSTAT_ACCESS_BLOCKED_OPTIONAL_PROVIDER_UNAVAILABLE"
UNDERSTAT_ACCESS_BLOCKED_PROVIDER_FAILED = "UNDERSTAT_ACCESS_BLOCKED_PROVIDER_FAILED"
UNDERSTAT_ACCESS_BLOCKED_FETCH_FAILED = "UNDERSTAT_ACCESS_BLOCKED_FETCH_FAILED"
UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND = "UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND"
UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS = "UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS"

MODES = {"existing", "local", "raw", "optional_provider", "explicit_fetch"}
DEFAULT_MODES = ["existing", "local", "raw"]


@dataclass(frozen=True)
class UnderstatDataAccessResult:
    league: str
    season: str
    source_mode: str
    source: str
    output_path: str
    rows_normalized: int
    access_label: str
    attempted_modes: list[str]
    successful_mode: str
    validation_errors: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve(path: str | Path) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = _repo_root() / out
    return out


def _safe_output_name(output_name: str | None, league: str | None, season: str | int | None, fallback: str = "understat_xg_source.csv") -> str:
    if output_name:
        name = Path(output_name).name
    elif league and season:
        league_slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(league)).strip("_")
        name = f"understat_xg_{league_slug}_{season}.csv"
    else:
        name = fallback
    if not name.lower().endswith(".csv"):
        name = f"{name}.csv"
    if "understat" not in name.lower():
        name = f"understat_{name}"
    return name


def _blocked(
    label: str,
    errors: list[str],
    *,
    league: str | None = None,
    season: str | int | None = None,
    source_mode: str = "",
    source: str | Path | None = None,
    attempted_modes: list[str] | None = None,
    warnings: list[str] | None = None,
) -> UnderstatDataAccessResult:
    return UnderstatDataAccessResult(
        league=str(league or ""),
        season=str(season or ""),
        source_mode=source_mode,
        source=str(source or ""),
        output_path="",
        rows_normalized=0,
        access_label=label,
        attempted_modes=attempted_modes or [],
        successful_mode="",
        validation_errors=errors,
        warning_notes=warnings or [],
    )


def _ready(
    df: pd.DataFrame,
    output_path: str | Path,
    *,
    league: str | None,
    season: str | int | None,
    source_mode: str,
    source: str | Path | None,
    attempted_modes: list[str],
    warnings: list[str] | None = None,
) -> UnderstatDataAccessResult:
    return UnderstatDataAccessResult(
        league=str(league or ""),
        season=str(season or ""),
        source_mode=source_mode,
        source=str(source or ""),
        output_path=str(output_path),
        rows_normalized=int(len(df)),
        access_label=UNDERSTAT_ACCESS_READY,
        attempted_modes=attempted_modes,
        successful_mode=source_mode,
        validation_errors=[],
        warning_notes=warnings or ["Phase 13.7 data access is diagnostic/foundation only. The model does not use these xG values yet."],
    )


def _serialize_errors(errors: list[str]) -> list[str]:
    return [str(error) for error in errors if str(error)]


def validate_understat_normalized_xg(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    required = set(OUTPUT_COLUMNS)
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        errors.append("MISSING_REQUIRED_COLUMNS=" + ",".join(missing_columns))
        return errors
    if df.empty:
        errors.append("NO_XG_ROWS")
        return errors
    identity = df[["date", "home_team", "away_team"]]
    if identity.isna().any().any() or identity.astype(str).apply(lambda col: col.str.strip().eq("")).any().any():
        errors.append("UNDERSTAT_MATCH_IDENTITY_MISSING")
    raw = df[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    if missing.any().any():
        errors.append("MISSING_XG_VALUES")
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        errors.append("NON_NUMERIC_XG_VALUES")
    if (numeric < 0).any().any():
        errors.append("NEGATIVE_XG_VALUES")
    return errors


def write_understat_data_access_csv(
    df: pd.DataFrame,
    output_name: str,
    output_dir: str | Path = "data/trusted_xg_sources",
    overwrite: bool = False,
) -> Path:
    errors = validate_understat_normalized_xg(df)
    if errors:
        raise ValueError(" | ".join(errors))
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_output_name(output_name, None, None)
    output = (output_root / safe_name).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("Understat data-access output must stay under output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    df.to_csv(output, index=False)
    return output


def discover_existing_understat_sources(
    output_dir: str | Path = "data/trusted_xg_sources",
    league: str | None = None,
    season: str | int | None = None,
) -> list[Path]:
    root = _resolve(output_dir)
    if not root.exists():
        return []
    paths = sorted(path for path in root.glob("*understat*.csv") if path.is_file())
    terms = [str(value).lower().replace(" ", "_") for value in (league, season) if value]
    if terms:
        paths = [path for path in paths if all(term in path.name.lower() for term in terms)]
    return paths


def _read_existing_normalized(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    errors = validate_understat_normalized_xg(df)
    if errors:
        raise ValueError(" | ".join(errors))
    return df[OUTPUT_COLUMNS].copy()


def parse_local_understat_source(source: str | Path) -> pd.DataFrame:
    path = _resolve(source)
    if not path.exists():
        raise FileNotFoundError(str(path))
    raw_df = load_understat_export(path)
    normalized, _schema = _normalize_by_schema(raw_df, source_path=path, source_url=None)
    errors = validate_understat_normalized_xg(normalized)
    if errors:
        raise ValueError(" | ".join(errors))
    return normalized


def parse_raw_understat_payload_or_html(raw_path: str | Path, league: str | None = None, season: str | int | None = None) -> pd.DataFrame:
    path = _resolve(raw_path)
    payload = path.read_text(encoding="utf-8", errors="replace")
    source_url = f"file://{path.name}"
    parse_errors: list[str] = []
    matches: list[dict[str, Any]] = []
    try:
        matches = parse_understat_matches_from_html(payload, source_url=source_url)
    except Exception as exc:
        parse_errors.append(str(exc))
    if not matches:
        try:
            matches = parse_understat_matches_from_runtime_payload(payload, source_url=source_url)
        except Exception as exc:
            parse_errors.append(str(exc))
    if not matches:
        state = detect_understat_html_state(payload)
        raise ValueError("UNDERSTAT_MATCH_DATA_NOT_FOUND | " + state + " | " + " | ".join(parse_errors))
    normalized = normalize_understat_matches_to_trusted_xg(matches, source_url=source_url)
    errors = validate_understat_normalized_xg(normalized)
    if errors:
        raise ValueError(" | ".join(errors))
    return normalized


def import_understat_from_optional_provider(league: str, season: str | int) -> pd.DataFrame:
    status = check_understat_optional_provider()
    if not status.installed:
        raise ImportError("SOCCERDATA_UNAVAILABLE")
    if status.provider_label != "UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE":
        raise ImportError(status.provider_label)
    try:
        provider_class = load_soccerdata_understat_provider()
        provider = provider_class(leagues=str(league), seasons=str(season))
        if hasattr(provider, "read_schedule"):
            raw = provider.read_schedule()
        elif hasattr(provider, "read_league_match_stats"):
            raw = provider.read_league_match_stats()
        else:
            raise RuntimeError("SOCCERDATA_UNDERSTAT_NO_SUPPORTED_METHOD")
    except Exception as exc:
        raise RuntimeError(f"SOCCERDATA_UNDERSTAT_FAILED: {exc}") from exc
    if not isinstance(raw, pd.DataFrame):
        raw = pd.DataFrame(raw)
    normalized = normalize_soccerdata_understat_output(raw, league=league, season=season)
    errors = validate_understat_normalized_xg(normalized)
    if errors:
        raise ValueError(" | ".join(errors))
    return normalized


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {"".join(ch for ch in str(col).lower() if ch.isalnum()): str(col) for col in df.columns}
    for name in names:
        key = "".join(ch for ch in name.lower() if ch.isalnum())
        if key in by_norm:
            return by_norm[key]
    return None


def _normalize_provider_frame(df: pd.DataFrame) -> pd.DataFrame:
    date = _find_col(df, "date", "game_date")
    home = _find_col(df, "home_team", "home")
    away = _find_col(df, "away_team", "away")
    hxg = _find_col(df, "home_xg", "home_xG", "hxg", "h_xg")
    axg = _find_col(df, "away_xg", "away_xG", "axg", "a_xg")
    if not all([date, home, away, hxg, axg]):
        raise ValueError("OPTIONAL_PROVIDER_SCHEMA_UNSUPPORTED")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[str(date)], errors="coerce", format="mixed").dt.strftime("%Y-%m-%d"),
        "home_team": df[str(home)].astype(str).str.strip(),
        "away_team": df[str(away)].astype(str).str.strip(),
        "home_xg": df[str(hxg)],
        "away_xg": df[str(axg)],
    })
    out["xg_source_name"] = "soccerdata_understat"
    out["xg_source_url"] = ""
    out["xg_import_type"] = "OPTIONAL_PROVIDER"
    return out[OUTPUT_COLUMNS]


def _raw_candidates(raw_dir: str | Path, league: str | None, season: str | int | None) -> list[Path]:
    root = _resolve(raw_dir)
    if not root.exists():
        return []
    paths = sorted(path for path in root.glob("*understat*") if path.is_file())
    terms = [str(value).lower().replace(" ", "_") for value in (league, season) if value]
    if terms:
        filtered = [path for path in paths if all(term in path.name.lower() for term in terms)]
        if filtered:
            return filtered
    return paths


def _normalise_modes(modes: list[str] | tuple[str, ...] | None, source: str | Path | None, raw_dir: str | Path) -> list[str]:
    requested = list(modes) if modes else list(DEFAULT_MODES)
    if source and "local" not in requested:
        requested.insert(0, "local")
    root = _resolve(raw_dir)
    if root.exists() and any(root.glob("*understat*")) and "raw" not in requested:
        requested.append("raw")
    out: list[str] = []
    for mode in requested:
        if mode not in MODES:
            raise ValueError(f"UNKNOWN_UNDERSTAT_ACCESS_MODE={mode}")
        if mode not in out:
            out.append(mode)
    return out


def _resolve_requested_modes(
    modes: list[str] | tuple[str, ...] | None,
    source: str | Path | None,
    raw_dir: str | Path,
    allow_optional_provider: bool,
    allow_network: bool,
) -> list[str]:
    requested = _normalise_modes(modes, source, raw_dir)
    if modes is None:
        if allow_optional_provider and "optional_provider" not in requested:
            requested.append("optional_provider")
        if allow_network and "explicit_fetch" not in requested:
            requested.append("explicit_fetch")
    return requested


def _label_for_validation_error(errors: list[str], raw: bool = False) -> str:
    text = " | ".join(errors)
    if "FileExistsError" in text:
        return UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS
    if raw:
        return UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED
    if "NO_XG_ROWS" in text or "NO_MATCH" in text:
        return UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND
    return UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND


def resolve_understat_trusted_xg_source(
    league: str | None = None,
    season: str | int | None = None,
    source: str | Path | None = None,
    output_name: str | None = None,
    output_dir: str | Path = "data/trusted_xg_sources",
    raw_dir: str | Path = "data/trusted_xg_sources/raw",
    modes: list[str] | tuple[str, ...] | None = None,
    overwrite: bool = False,
    allow_network: bool = False,
    allow_optional_provider: bool = False,
) -> UnderstatDataAccessResult:
    try:
        requested_modes = _resolve_requested_modes(modes, source, raw_dir, allow_optional_provider, allow_network)
    except ValueError as exc:
        return _blocked(str(exc), [str(exc)], league=league, season=season)
    gated_modes = []
    warnings: list[str] = []
    for mode in requested_modes:
        if mode == "optional_provider" and not allow_optional_provider:
            warnings.append("optional_provider skipped because allow_optional_provider=False")
            continue
        if mode == "explicit_fetch" and not allow_network:
            warnings.append("explicit_fetch skipped because allow_network=False")
            continue
        gated_modes.append(mode)
    if not gated_modes:
        return _blocked(UNDERSTAT_ACCESS_BLOCKED_NO_INPUT, ["NO_ENABLED_UNDERSTAT_ACCESS_MODE"], league=league, season=season, attempted_modes=requested_modes, warnings=warnings)
    if not source and not league and not season and set(gated_modes).issubset({"existing", "local", "raw"}):
        return _blocked(UNDERSTAT_ACCESS_BLOCKED_NO_INPUT, ["LEAGUE_SEASON_OR_SOURCE_REQUIRED"], league=league, season=season, attempted_modes=gated_modes, warnings=warnings)

    errors_by_mode: list[str] = []
    attempted: list[str] = []
    for mode in gated_modes:
        attempted.append(mode)
        if mode == "existing":
            for candidate in discover_existing_understat_sources(output_dir, league=league, season=season):
                try:
                    df = _read_existing_normalized(candidate)
                    return _ready(df, candidate, league=league, season=season, source_mode=mode, source=candidate, attempted_modes=attempted, warnings=warnings)
                except Exception as exc:
                    errors_by_mode.append(f"existing:{candidate.name}:{exc}")
            errors_by_mode.append("existing:NO_NORMALIZED_UNDERSTAT_SOURCE")
        elif mode == "local":
            if not source:
                errors_by_mode.append("local:NO_LOCAL_SOURCE_PROVIDED")
                continue
            source_path = _resolve(source)
            if not source_path.exists():
                errors_by_mode.append(f"local:SOURCE_NOT_FOUND:{source_path}")
                continue
            try:
                df = parse_local_understat_source(source_path)
                name = _safe_output_name(output_name, league, season, fallback=f"{source_path.stem}_understat.csv")
                output_path = write_understat_data_access_csv(df, name, output_dir=output_dir, overwrite=overwrite)
                return _ready(df, output_path, league=league, season=season, source_mode=mode, source=source_path, attempted_modes=attempted, warnings=warnings)
            except FileExistsError as exc:
                return _blocked(UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS, [str(exc)], league=league, season=season, source_mode=mode, source=source_path, attempted_modes=attempted, warnings=warnings)
            except Exception as exc:
                errors_by_mode.append(f"local:{exc}")
        elif mode == "raw":
            raw_candidates = _raw_candidates(raw_dir, league, season)
            if not raw_candidates:
                errors_by_mode.append("raw:NO_RAW_UNDERSTAT_SOURCE")
                continue
            for candidate in raw_candidates:
                try:
                    df = parse_raw_understat_payload_or_html(candidate, league=league, season=season)
                    name = _safe_output_name(output_name, league, season, fallback=f"{candidate.stem}_normalized.csv")
                    output_path = write_understat_data_access_csv(df, name, output_dir=output_dir, overwrite=overwrite)
                    return _ready(df, output_path, league=league, season=season, source_mode=mode, source=candidate, attempted_modes=attempted, warnings=warnings)
                except FileExistsError as exc:
                    return _blocked(UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS, [str(exc)], league=league, season=season, source_mode=mode, source=candidate, attempted_modes=attempted, warnings=warnings)
                except Exception as exc:
                    errors_by_mode.append(f"raw:{candidate.name}:{exc}")
        elif mode == "optional_provider":
            if not league or not season:
                errors_by_mode.append("optional_provider:LEAGUE_AND_SEASON_REQUIRED")
                continue
            try:
                df = import_understat_from_optional_provider(str(league), season)
                name = _safe_output_name(output_name, league, season)
                output_path = write_understat_data_access_csv(df, name, output_dir=output_dir, overwrite=overwrite)
                return _ready(df, output_path, league=league, season=season, source_mode=mode, source="soccerdata.Understat", attempted_modes=attempted, warnings=warnings)
            except ImportError as exc:
                errors_by_mode.append(f"optional_provider:{exc}")
                warnings.append("optional_provider unavailable; install soccerdata separately to use this mode.")
                warnings.append("install_command=" + get_understat_optional_provider_install_command())
            except FileExistsError as exc:
                return _blocked(UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS, [str(exc)], league=league, season=season, source_mode=mode, source="soccerdata.Understat", attempted_modes=attempted, warnings=warnings)
            except Exception as exc:
                errors_by_mode.append(f"optional_provider:{exc}")
        elif mode == "explicit_fetch":
            if not (league and season):
                errors_by_mode.append("explicit_fetch:LEAGUE_AND_SEASON_REQUIRED")
                continue
            result = fetch_understat_league_season(
                league=league,
                season=season,
                output_name=_safe_output_name(output_name, league, season),
                output_dir=output_dir,
                raw_output_dir=raw_dir,
                overwrite=overwrite,
                no_fetch=False,
            )
            if result.fetch_label == UNDERSTAT_FETCH_READY:
                try:
                    df = _read_existing_normalized(Path(result.output_path))
                    return _ready(df, result.output_path, league=league, season=season, source_mode=mode, source=result.source_url, attempted_modes=attempted, warnings=warnings + result.warning_notes)
                except Exception as exc:
                    errors_by_mode.append(f"explicit_fetch:{exc}")
            elif "OUTPUT_EXISTS" in result.fetch_label:
                return _blocked(UNDERSTAT_ACCESS_BLOCKED_OUTPUT_EXISTS, result.validation_errors, league=league, season=season, source_mode=mode, source=result.source_url, attempted_modes=attempted, warnings=warnings + result.warning_notes)
            else:
                errors_by_mode.append(f"explicit_fetch:{result.fetch_label}:{' | '.join(result.validation_errors)}")

    if any(error.startswith("raw:") and "NO_RAW_UNDERSTAT_SOURCE" not in error for error in errors_by_mode):
        label = UNDERSTAT_ACCESS_BLOCKED_RAW_PARSE_FAILED
    elif any("optional_provider:SOCCERDATA_UNAVAILABLE" in error for error in errors_by_mode):
        label = UNDERSTAT_ACCESS_BLOCKED_OPTIONAL_PROVIDER_UNAVAILABLE
    elif any(error.startswith("optional_provider:") for error in errors_by_mode):
        label = UNDERSTAT_ACCESS_BLOCKED_PROVIDER_FAILED
    elif any(error.startswith("explicit_fetch:") for error in errors_by_mode):
        label = UNDERSTAT_ACCESS_BLOCKED_FETCH_FAILED
    elif any("NO_LOCAL_SOURCE" in error or "SOURCE_NOT_FOUND" in error for error in errors_by_mode):
        label = UNDERSTAT_ACCESS_BLOCKED_NO_LOCAL_SOURCE
    else:
        label = UNDERSTAT_ACCESS_BLOCKED_NO_XG_DATA_FOUND
    return _blocked(label, _serialize_errors(errors_by_mode), league=league, season=season, attempted_modes=attempted, warnings=warnings)


def result_to_json(result: UnderstatDataAccessResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
