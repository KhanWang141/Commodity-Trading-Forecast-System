"""Strong schema validation for the final research dataset."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


FORBIDDEN_FEATURE_TOKENS = (
    "label",
    "target",
    "future",
    "forward_return",
    "future_vol",
)


def assert_no_label_leakage(feature_columns: list[str]) -> None:
    """Reject names that indicate target information in the feature matrix."""
    offenders = [
        name
        for name in feature_columns
        if any(token in name.lower() for token in FORBIDDEN_FEATURE_TOKENS)
    ]
    if offenders:
        raise AssertionError(f"Target-like feature columns are forbidden: {offenders}")


def validate_model_dataset(
    frame: pd.DataFrame,
    feature_columns: list[str],
    label_columns: list[str],
) -> dict[str, Any]:
    """Validate column count, types, ordering, uniqueness, and finite values."""
    if len(feature_columns) != 29:
        raise AssertionError(f"Expected 29 feature columns, found {len(feature_columns)}")
    if len(set(feature_columns)) != 29:
        raise AssertionError("Feature columns must be unique")
    assert_no_label_leakage(feature_columns)
    required = ["timestamp", "instrument", *feature_columns, *label_columns]
    missing = [column for column in required if column not in frame]
    if missing:
        raise AssertionError(f"Dataset is missing required columns: {missing}")
    if frame.empty:
        raise AssertionError("Dataset must contain at least one row")
    if frame[["timestamp", "instrument"]].duplicated().any():
        raise AssertionError("Duplicate instrument/timestamp samples found")
    if frame["timestamp"].isna().any():
        raise AssertionError("Timestamp contains missing values")
    if frame["timestamp"].dt.tz is None:
        raise AssertionError("Timestamp must be timezone-aware")
    ordered = frame.sort_values(["instrument", "timestamp"], kind="stable")
    if not ordered.index.equals(frame.index):
        raise AssertionError("Dataset must be sorted by instrument and timestamp")

    numeric_columns = [*feature_columns, *label_columns]
    non_numeric = [column for column in numeric_columns if not pd.api.types.is_numeric_dtype(frame[column])]
    if non_numeric:
        raise AssertionError(f"Numeric columns have unstable types: {non_numeric}")
    values = frame[numeric_columns].to_numpy(dtype=float)
    if np.isinf(values).any():
        locations = np.argwhere(np.isinf(values))[:10].tolist()
        raise AssertionError(f"Infinite values found at numeric matrix positions: {locations}")

    constants = [column for column in feature_columns if frame[column].nunique(dropna=True) <= 1]
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "feature_count": len(feature_columns),
        "label_count": len(label_columns),
        "duplicate_samples": 0,
        "infinite_values": 0,
        "constant_features": constants,
        "timestamp_min": frame["timestamp"].min().isoformat(),
        "timestamp_max": frame["timestamp"].max().isoformat(),
    }
