# -*- coding: utf-8 -*-
"""Understat trusted xG import adapter.

Phase 13.5 diagnostic/foundation only. This adapter normalizes explicit local
Understat exports or explicit user-provided Understat URLs into trusted xG
source CSVs. It never infers, estimates, or invents xG values.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

UNDERSTAT_PAIR_SCHEMA = "UNDERSTAT_PAIR_XG_SOURCE"
UNDERSTAT_ALIAS_PAIR_SCHEMA = "UNDERSTAT_ALIAS_PAIR_XG_SOURCE"
UNDERSTAT_LONG_SCHEMA = "UNDERSTAT_LONG_XG_SOURCE"
UNKNOWN_SCHEMA = "UNKNOWN_UNDERSTAT_XG_SOURCE_SCHEMA"

UNDERSTAT_XG_IMPORT_READY = "UNDERSTAT_XG_IMPORT_READY"
UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA = "UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA"
UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES = "UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES"
UNDERSTAT_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND = "UNDERSTAT_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND"
UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED = "UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED"
UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_FAILED = "UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_FAILED"
UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS = "UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS"
UNDERSTAT_XG_IMPORT_NO_SOURCE_PROVIDED = "UNDERSTAT_XG_IMPORT_NO_SOURCE_PROVIDED"

OUTPUT_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_xg",
    "away_xg",
    "xg_source_name",
    "xg_source_url",
    "xg_import_type",
]


@dataclass(frozen=True)
class UnderstatTrustedXGResult:
    source: str
    source_type: str
    raw_output_path: str
    output_path: str
    rows_read: int
    rows_normalized: int
    detected_schema: str
    import_label: str
    validation_errors: list[str]
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve(path: str | Path, base: Path | None = None) -> Path:
    out = Path(path)
    if not out.is_absolute():
        out = (base or _repo_root()) / out
    return out


def _norm_col(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _find_col(df: pd.DataFrame, *names: str) -> str | None:
    by_norm = {_norm_col(col): str(col) for col in df.columns}
    for name in names:
        key = _norm_col(name)
        if key in by_norm:
            return by_norm[key]
    return None


def _find_exact_col(df: pd.DataFrame, *names: str) -> str | None:
    existing = {str(col): str(col) for col in df.columns}
    for name in names:
        if name in existing:
            return existing[name]
    return None


def _parse_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)
    if parsed.isna().any():
        fallback = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
        parsed = parsed.fillna(fallback)
    return parsed.dt.strftime("%Y-%m-%d")


def _norm_team(value: Any) -> str:
    return " ".join(str(value or "").strip().replace(".", "").split())


def _key(df: pd.DataFrame) -> pd.Series:
    return (
        df["date"].astype(str).str.strip()
        + "|"
        + df["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + df["away_team"].astype(str).str.strip().str.lower()
    )


def _source_type(source: str | Path | None) -> str:
    if source is None or str(source).strip() == "":
        return "NO_SOURCE"
    parsed = urlparse(str(source))
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return "URL"
    return "LOCAL_FILE"


def detect_understat_source_schema(df: pd.DataFrame) -> str:
    date = _find_col(df, "date", "Date")
    home_team = _find_col(df, "home_team", "HomeTeam")
    away_team = _find_col(df, "away_team", "AwayTeam")
    home_xg = _find_exact_col(df, "home_xG")
    away_xg = _find_exact_col(df, "away_xG")
    if all([date, home_team, away_team, home_xg, away_xg]):
        return UNDERSTAT_PAIR_SCHEMA

    home = _find_col(df, "home")
    away = _find_col(df, "away")
    hxg = _find_col(df, "hxg")
    axg = _find_col(df, "axg")
    if all([date, home, away, hxg, axg]):
        return UNDERSTAT_ALIAS_PAIR_SCHEMA

    long_cols = [
        _find_col(df, "date", "Date"),
        _find_col(df, "team"),
        _find_col(df, "opponent"),
        _find_col(df, "xG"),
        _find_col(df, "xGA"),
        _find_col(df, "venue"),
    ]
    if all(long_cols):
        return UNDERSTAT_LONG_SCHEMA
    return UNKNOWN_SCHEMA


def _validate_xg(out: pd.DataFrame) -> None:
    raw = out[["home_xg", "away_xg"]]
    missing = raw.isna() | raw.astype(str).apply(lambda col: col.str.strip().eq(""))
    if missing.any().any():
        raise ValueError("MISSING_XG_VALUES")
    numeric = raw.apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        raise ValueError("NON_NUMERIC_XG_VALUES")
    if (numeric < 0).any().any():
        raise ValueError("NEGATIVE_XG_VALUES")
    out["home_xg"] = numeric["home_xg"]
    out["away_xg"] = numeric["away_xg"]


def _source_name(source_path: str | Path | None, source_url: str | None) -> str:
    if source_path is not None:
        return Path(source_path).name
    return urlparse(source_url or "").netloc


def _with_source_columns(df: pd.DataFrame, source_path: str | Path | None, source_url: str | None) -> pd.DataFrame:
    out = df.copy()
    out["xg_source_name"] = _source_name(source_path, source_url)
    out["xg_source_url"] = source_url or ""
    out["xg_import_type"] = "URL" if source_url else "LOCAL_FILE"
    return out[OUTPUT_COLUMNS]


def normalize_understat_pair_export(
    df: pd.DataFrame,
    source_path: str | Path | None = None,
    source_url: str | None = None,
) -> pd.DataFrame:
    schema = detect_understat_source_schema(df)
    date = _find_col(df, "date", "Date")
    if schema == UNDERSTAT_PAIR_SCHEMA:
        home = _find_col(df, "home_team", "HomeTeam")
        away = _find_col(df, "away_team", "AwayTeam")
        home_xg = _find_exact_col(df, "home_xG")
        away_xg = _find_exact_col(df, "away_xG")
    elif schema == UNDERSTAT_ALIAS_PAIR_SCHEMA:
        home = _find_col(df, "home")
        away = _find_col(df, "away")
        home_xg = _find_col(df, "hxg")
        away_xg = _find_col(df, "axg")
    else:
        raise ValueError("UNDERSTAT_PAIR_SCHEMA_UNSUPPORTED")
    if not all([date, home, away, home_xg, away_xg]):
        raise ValueError("UNDERSTAT_PAIR_SCHEMA_UNSUPPORTED")
    out = pd.DataFrame({
        "date": _parse_date(df[str(date)]),
        "home_team": df[str(home)].map(_norm_team),
        "away_team": df[str(away)].map(_norm_team),
        "home_xg": df[str(home_xg)],
        "away_xg": df[str(away_xg)],
    })
    _validate_xg(out)
    if out[["date", "home_team", "away_team"]].isna().any().any():
        raise ValueError("UNDERSTAT_MISSING_IDENTITY")
    if _key(out).duplicated().any():
        raise ValueError("UNDERSTAT_DUPLICATE_MATCH_KEYS")
    return _with_source_columns(out, source_path, source_url)


def normalize_understat_long_export(
    df: pd.DataFrame,
    source_path: str | Path | None = None,
    source_url: str | None = None,
) -> pd.DataFrame:
    date = _find_col(df, "date", "Date")
    team = _find_col(df, "team")
    opponent = _find_col(df, "opponent")
    xg = _find_col(df, "xG")
    xga = _find_col(df, "xGA")
    venue = _find_col(df, "venue")
    if not all([date, team, opponent, xg, xga, venue]):
        raise ValueError("UNDERSTAT_LONG_SCHEMA_UNSUPPORTED")
    home_rows = df[df[str(venue)].astype(str).str.strip().str.lower().eq("home")].copy()
    away_rows = df[df[str(venue)].astype(str).str.strip().str.lower().eq("away")].copy()
    if home_rows.empty or away_rows.empty:
        raise ValueError("UNDERSTAT_LONG_PAIRING_AMBIGUOUS")
    out = pd.DataFrame({
        "date": _parse_date(home_rows[str(date)]),
        "home_team": home_rows[str(team)].map(_norm_team),
        "away_team": home_rows[str(opponent)].map(_norm_team),
        "home_xg": home_rows[str(xg)],
        "away_xg": home_rows[str(xga)],
    })
    home_keys = (
        out["date"].astype(str).str.strip()
        + "|"
        + out["home_team"].astype(str).str.strip().str.lower()
        + "|"
        + out["away_team"].astype(str).str.strip().str.lower()
    )
    away_norm = pd.DataFrame({
        "date": _parse_date(away_rows[str(date)]),
        "home_team": away_rows[str(opponent)].map(_norm_team),
        "away_team": away_rows[str(team)].map(_norm_team),
    })
    away_keys = set(_key(away_norm))
    if home_keys.duplicated().any() or not set(home_keys).issubset(away_keys):
        raise ValueError("UNDERSTAT_LONG_PAIRING_AMBIGUOUS")
    _validate_xg(out)
    return _with_source_columns(out, source_path, source_url)


def load_understat_export(path: str | Path) -> pd.DataFrame:
    resolved = _resolve(path)
    if not resolved.exists():
        raise FileNotFoundError(str(resolved))
    if resolved.suffix.lower() in {".html", ".htm"}:
        tables = pd.read_html(resolved)
        if not tables:
            raise ValueError("NO_TABLES_IN_HTML_SOURCE")
        return tables[0]
    return pd.read_csv(resolved, low_memory=False)


def _safe_url_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "understat_xg_source.csv"
    if not name.lower().endswith((".csv", ".html", ".htm")):
        name = f"{Path(name).stem or 'understat_xg_source'}.csv"
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return safe if "understat" in safe.lower() else f"understat_{safe}"


def fetch_explicit_understat_source_url(url: str, output_dir: str | Path = "data/trusted_xg_sources/raw") -> Path:
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / _safe_url_name(url)).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("raw Understat xG output must stay under raw output_dir")
    request = Request(url, headers={"User-Agent": "football_prediction_v19 understat-xg-import/13.5"})
    with urlopen(request, timeout=30) as response:
        output.write_bytes(response.read())
    return output


def write_understat_trusted_xg_csv(
    df: pd.DataFrame,
    output_name: str,
    output_dir: str | Path = "data/trusted_xg_sources",
    overwrite: bool = False,
) -> Path:
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(output_name).name
    if not safe_name.lower().endswith(".csv"):
        safe_name = f"{safe_name}.csv"
    if "understat" not in safe_name.lower():
        safe_name = f"understat_{safe_name}"
    output = (output_root / safe_name).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("Understat trusted xG output must stay under output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    df.to_csv(output, index=False)
    return output


def _blocked(
    source: str | Path | None,
    source_type: str,
    label: str,
    errors: list[str],
    *,
    raw_output_path: str = "",
    rows_read: int = 0,
    detected_schema: str = "",
) -> UnderstatTrustedXGResult:
    return UnderstatTrustedXGResult(
        source=str(source or ""),
        source_type=source_type,
        raw_output_path=raw_output_path,
        output_path="",
        rows_read=int(rows_read),
        rows_normalized=0,
        detected_schema=detected_schema,
        import_label=label,
        validation_errors=errors,
        warning_notes=[],
    )


def _label_for_exception(exc: Exception) -> str:
    text = str(exc)
    if "PAIRING_AMBIGUOUS" in text:
        return UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA
    if any(token in text for token in ("MISSING_XG_VALUES", "NON_NUMERIC_XG_VALUES", "NEGATIVE_XG_VALUES")):
        return UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_XG_VALUES
    return UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA


def _normalize_by_schema(df: pd.DataFrame, source_path: str | Path | None, source_url: str | None) -> tuple[pd.DataFrame, str]:
    schema = detect_understat_source_schema(df)
    if schema in {UNDERSTAT_PAIR_SCHEMA, UNDERSTAT_ALIAS_PAIR_SCHEMA}:
        return normalize_understat_pair_export(df, source_path=source_path, source_url=source_url), schema
    if schema == UNDERSTAT_LONG_SCHEMA:
        return normalize_understat_long_export(df, source_path=source_path, source_url=source_url), schema
    raise ValueError("UNDERSTAT_XG_SOURCE_SCHEMA_UNSUPPORTED")


def import_understat_trusted_xg_source(
    source: str | Path | None,
    output_name: str | None = None,
    output_dir: str | Path = "data/trusted_xg_sources",
    raw_output_dir: str | Path = "data/trusted_xg_sources/raw",
    overwrite: bool = False,
    no_fetch: bool = False,
) -> UnderstatTrustedXGResult:
    source_type = _source_type(source)
    if source_type == "NO_SOURCE":
        return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_NO_SOURCE_PROVIDED, ["NO_SOURCE_PROVIDED"])

    raw_output_path = ""
    source_url = ""
    if source_type == "URL":
        if no_fetch:
            return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_DISABLED, ["NO_FETCH_REQUESTED"])
        source_url = str(source)
        try:
            source_path = fetch_explicit_understat_source_url(source_url, output_dir=raw_output_dir)
            raw_output_path = str(source_path)
        except Exception as exc:
            return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_BLOCKED_FETCH_FAILED, [str(exc)])
    else:
        source_path = _resolve(str(source))
        if not source_path.exists():
            return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND, [str(source_path)])

    try:
        raw_df = load_understat_export(source_path)
    except Exception as exc:
        return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA, [str(exc)], raw_output_path=raw_output_path)
    schema = detect_understat_source_schema(raw_df)
    try:
        normalized, schema = _normalize_by_schema(raw_df, source_path=source_path, source_url=source_url or None)
    except Exception as exc:
        return _blocked(source, source_type, _label_for_exception(exc), [str(exc)], raw_output_path=raw_output_path, rows_read=len(raw_df), detected_schema=schema)

    name = output_name or f"{source_path.stem}_understat_trusted_xg.csv"
    try:
        output_path = write_understat_trusted_xg_csv(normalized, name, output_dir=output_dir, overwrite=overwrite)
    except FileExistsError as exc:
        return _blocked(
            source,
            source_type,
            UNDERSTAT_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
            [str(exc)],
            raw_output_path=raw_output_path,
            rows_read=len(raw_df),
            detected_schema=schema,
        )
    except Exception as exc:
        return _blocked(source, source_type, UNDERSTAT_XG_IMPORT_BLOCKED_INVALID_SCHEMA, [str(exc)], raw_output_path=raw_output_path, rows_read=len(raw_df), detected_schema=schema)

    return UnderstatTrustedXGResult(
        source=str(source),
        source_type=source_type,
        raw_output_path=raw_output_path,
        output_path=str(output_path),
        rows_read=int(len(raw_df)),
        rows_normalized=int(len(normalized)),
        detected_schema=schema,
        import_label=UNDERSTAT_XG_IMPORT_READY,
        validation_errors=[],
        warning_notes=["Understat trusted xG source is not used by the model until intake, acceptance, and future enrichment are approved."],
    )
