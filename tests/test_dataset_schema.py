from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.schema import validate_model_dataset


def _dataset(feature_count: int = 29) -> tuple[pd.DataFrame, list[str], list[str]]:
    feature_columns = [f"x_{index}" for index in range(feature_count)]
    label_columns = ["logV_h5", "logV_h20"]
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01 20:00", periods=3, tz="Asia/Shanghai"),
            "instrument": ["I"] * 3,
            **{name: np.arange(3, dtype=float) + index for index, name in enumerate(feature_columns)},
            "logV_h5": [0.1, 0.2, np.nan],
            "logV_h20": [0.3, np.nan, np.nan],
        }
    )
    return frame, feature_columns, label_columns


def test_schema_accepts_exactly_29_unique_features():
    frame, features, labels = _dataset()
    summary = validate_model_dataset(frame, features, labels)
    assert summary["feature_count"] == 29


def test_schema_rejects_wrong_feature_count():
    frame, features, labels = _dataset(28)
    with pytest.raises(AssertionError, match="Expected 29"):
        validate_model_dataset(frame, features, labels)


def test_schema_rejects_duplicate_samples():
    frame, features, labels = _dataset()
    frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]
    with pytest.raises(AssertionError, match="Duplicate"):
        validate_model_dataset(frame, features, labels)


def test_schema_rejects_infinite_values():
    frame, features, labels = _dataset()
    frame.loc[1, features[0]] = np.inf
    with pytest.raises(AssertionError, match="Infinite"):
        validate_model_dataset(frame, features, labels)
