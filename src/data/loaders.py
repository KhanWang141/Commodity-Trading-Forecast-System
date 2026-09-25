"""Shared I/O helpers with explicit timestamp handling."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import load_project_config, project_root, resolve_project_path


def localize_timestamp(values: pd.Series, timezone: str) -> pd.Series:
    """Parse timestamps and normalize them to one timezone."""
    parsed = pd.to_datetime(values, errors="raise")
    if parsed.dt.tz is None:
        return parsed.dt.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    return parsed.dt.tz_convert(timezone)


def source_config(source_name: str, root: str | Path | None = None) -> dict[str, Any]:
    """Return one configured data source."""
    config = load_project_config("data_sources.yaml", root)
    try:
        return dict(config["sources"][source_name])
    except KeyError as exc:
        raise KeyError(f"Unknown data source: {source_name}") from exc


def read_frozen_csv(source_name: str, root: str | Path | None = None) -> pd.DataFrame:
    """Read a configured frozen CSV snapshot."""
    spec = source_config(source_name, root)
    path = resolve_project_path(spec["frozen_path"], root)
    if not path.exists():
        raise FileNotFoundError(f"Frozen input not found: {path}. Run freeze_inputs first.")
    return pd.read_csv(path)


def write_json_atomic(payload: Any, path: str | Path) -> None:
    """Write JSON through a same-directory temporary file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    os.replace(temporary, destination)


def write_parquet_atomic(frame: pd.DataFrame, path: str | Path) -> None:
    """Write a Parquet file atomically using pyarrow through pandas."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, engine="pyarrow")
    os.replace(temporary, destination)


def load_manifest(root: str | Path | None = None) -> dict[str, Any]:
    """Load the active input manifest."""
    config = load_project_config("data_sources.yaml", root)
    path = resolve_project_path(config["manifest_path"], root)
    if not path.exists():
        raise FileNotFoundError(f"Input manifest not found: {path}. Run freeze_inputs first.")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def root_path(root: str | Path | None = None) -> Path:
    """Compatibility helper used by command modules."""
    return project_root(root)
