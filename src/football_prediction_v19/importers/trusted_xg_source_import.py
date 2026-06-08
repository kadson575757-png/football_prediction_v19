# -*- coding: utf-8 -*-
"""Trusted xG source import adapter.

Phase 13.4 diagnostic/foundation only. Imports explicit local exports or
explicit user-provided URLs into trusted xG source CSVs. No xG values are
inferred, estimated, scraped from hidden locations, or written back to inputs.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

from football_prediction_v19.importers.trusted_xg_source import (
    FBREF_LONG_SCHEMA,
    UNKNOWN_SCHEMA,
    detect_trusted_xg_source_schema,
    normalize_trusted_xg_source,
)

TRUSTED_XG_IMPORT_READY = "TRUSTED_XG_IMPORT_READY"
TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA = "TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA"
TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES = "TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES"
TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT = "TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT"
TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND = "TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND"
TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED = "TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED"
TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS = "TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS"
TRUSTED_XG_IMPORT_NO_SOURCE_PROVIDED = "TRUSTED_XG_IMPORT_NO_SOURCE_PROVIDED"

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
class TrustedXGSourceImportResult:
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


def detect_import_source_type(path_or_url: str | Path | None) -> str:
    if path_or_url is None or str(path_or_url).strip() == "":
        return "NO_SOURCE"
    parsed = urlparse(str(path_or_url))
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return "URL"
    return "LOCAL_FILE"


def _blocked(
    source: str | Path | None,
    source_type: str,
    label: str,
    errors: list[str],
    *,
    raw_output_path: str = "",
    rows_read: int = 0,
    detected_schema: str = "",
) -> TrustedXGSourceImportResult:
    return TrustedXGSourceImportResult(
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


def load_local_trusted_xg_export(path: str | Path) -> pd.DataFrame:
    resolved = _resolve(path)
    if not resolved.exists():
        raise FileNotFoundError(str(resolved))
    return pd.read_csv(resolved, low_memory=False)


def _safe_url_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "trusted_xg_source.csv"
    if not name.lower().endswith((".csv", ".html", ".htm")):
        name = f"{Path(name).stem or 'trusted_xg_source'}.csv"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def fetch_explicit_trusted_xg_source_url(url: str, output_dir: str | Path = "data/trusted_xg_sources/raw") -> Path:
    output_root = _resolve(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = (output_root / _safe_url_name(url)).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("raw trusted xG fetch output must stay under raw output_dir")
    request = Request(url, headers={"User-Agent": "football_prediction_v19 trusted-xg-import/13.4"})
    with urlopen(request, timeout=30) as response:
        content = response.read()
    output.write_bytes(content)
    return output


def _read_source_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".html", ".htm"}:
        tables = pd.read_html(path)
        if not tables:
            raise ValueError("NO_TABLES_IN_HTML_SOURCE")
        return tables[0]
    return pd.read_csv(path, low_memory=False)


def normalize_imported_trusted_xg_source(
    df: pd.DataFrame,
    source_path: str | Path | None = None,
    source_url: str | None = None,
) -> pd.DataFrame:
    normalized = normalize_trusted_xg_source(df, source_path=source_path)
    xg = normalized[["home_xg", "away_xg"]]
    if xg.isna().any().any():
        raise ValueError("MISSING_XG_VALUES")
    source_name = Path(source_path).name if source_path is not None else (urlparse(source_url or "").netloc or "")
    out = pd.DataFrame({
        "date": normalized["date"],
        "home_team": normalized["home_team"],
        "away_team": normalized["away_team"],
        "home_xg": normalized["home_xg"],
        "away_xg": normalized["away_xg"],
        "xg_source_name": source_name,
        "xg_source_url": source_url or "",
        "xg_import_type": "URL" if source_url else "LOCAL_FILE",
    })
    return out[OUTPUT_COLUMNS]


def write_trusted_xg_source_csv(
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
    output = (output_root / safe_name).resolve()
    if output_root.resolve() not in output.parents:
        raise ValueError("trusted xG source output must stay under output_dir")
    if output.exists() and not overwrite:
        raise FileExistsError(str(output))
    df.to_csv(output, index=False)
    return output


def _label_for_exception(exc: Exception, schema: str = "") -> str:
    text = str(exc)
    if "FBREF_HOME_AWAY_PAIRING_AMBIGUOUS" in text or "LONG_XG_PAIRING_REQUIRED" in text:
        return TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT
    if any(token in text for token in ("NON_NUMERIC_XG_VALUES", "NEGATIVE_XG_VALUES", "MISSING_XG_VALUES")):
        return TRUSTED_XG_IMPORT_BLOCKED_INVALID_XG_VALUES
    if schema == FBREF_LONG_SCHEMA:
        return TRUSTED_XG_IMPORT_BLOCKED_AMBIGUOUS_LONG_FORMAT
    return TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA


def import_trusted_xg_source(
    source: str | Path | None,
    output_name: str | None = None,
    output_dir: str | Path = "data/trusted_xg_sources",
    raw_output_dir: str | Path = "data/trusted_xg_sources/raw",
    overwrite: bool = False,
    no_fetch: bool = False,
) -> TrustedXGSourceImportResult:
    source_type = detect_import_source_type(source)
    if source_type == "NO_SOURCE":
        return _blocked(source, source_type, TRUSTED_XG_IMPORT_NO_SOURCE_PROVIDED, ["NO_SOURCE_PROVIDED"])

    raw_output_path = ""
    source_path: Path
    source_url = ""
    if source_type == "URL":
        if no_fetch:
            return _blocked(source, source_type, TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED, ["NO_FETCH_REQUESTED"])
        source_url = str(source)
        try:
            source_path = fetch_explicit_trusted_xg_source_url(source_url, output_dir=raw_output_dir)
            raw_output_path = str(source_path)
        except Exception as exc:
            return _blocked(source, source_type, TRUSTED_XG_IMPORT_BLOCKED_FETCH_FAILED, [str(exc)])
    else:
        source_path = _resolve(str(source))
        if not source_path.exists():
            return _blocked(source, source_type, TRUSTED_XG_IMPORT_BLOCKED_SOURCE_NOT_FOUND, [str(source_path)])

    try:
        raw_df = _read_source_table(source_path)
    except Exception as exc:
        return _blocked(source, source_type, TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA, [str(exc)], raw_output_path=raw_output_path)
    schema = detect_trusted_xg_source_schema(raw_df)
    try:
        normalized = normalize_imported_trusted_xg_source(raw_df, source_path=source_path, source_url=source_url or None)
    except Exception as exc:
        label = _label_for_exception(exc, schema)
        return _blocked(source, source_type, label, [str(exc)], raw_output_path=raw_output_path, rows_read=len(raw_df), detected_schema=schema)

    name = output_name or f"{source_path.stem}_trusted_xg_source.csv"
    try:
        output_path = write_trusted_xg_source_csv(normalized, name, output_dir=output_dir, overwrite=overwrite)
    except FileExistsError as exc:
        return _blocked(
            source,
            source_type,
            TRUSTED_XG_IMPORT_BLOCKED_OUTPUT_EXISTS,
            [str(exc)],
            raw_output_path=raw_output_path,
            rows_read=len(raw_df),
            detected_schema=schema,
        )
    except Exception as exc:
        return _blocked(source, source_type, TRUSTED_XG_IMPORT_BLOCKED_INVALID_SCHEMA, [str(exc)], raw_output_path=raw_output_path, rows_read=len(raw_df), detected_schema=schema)

    return TrustedXGSourceImportResult(
        source=str(source),
        source_type=source_type,
        raw_output_path=raw_output_path,
        output_path=str(output_path),
        rows_read=int(len(raw_df)),
        rows_normalized=int(len(normalized)),
        detected_schema=schema,
        import_label=TRUSTED_XG_IMPORT_READY,
        validation_errors=[],
        warning_notes=["Imported source is not used by the model until intake, acceptance, and future enrichment are approved."],
    )
