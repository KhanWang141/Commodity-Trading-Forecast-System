"""Deterministic file hashing and CSV profiling."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_csv(path: str | Path, date_column: str) -> dict[str, Any]:
    """Return stable structural metadata for a CSV input."""
    frame = pd.read_csv(path)
    if date_column not in frame.columns:
        raise ValueError(f"Missing date column {date_column!r} in {path}")
    dates = pd.to_datetime(frame[date_column], errors="raise")
    return {
        "size_bytes": Path(path).stat().st_size,
        "row_count": int(len(frame)),
        "columns": frame.columns.tolist(),
        "min_date": dates.min().isoformat(),
        "max_date": dates.max().isoformat(),
    }
