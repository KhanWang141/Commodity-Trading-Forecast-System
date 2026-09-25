from __future__ import annotations

import pandas as pd
import pytest

from src.audit.asof_audit import assert_audit_pass, audit_feature_availability


def _feature_and_trace(available_offset: str):
    timestamp = pd.Timestamp("2025-01-10 20:00", tz="Asia/Shanghai")
    features = pd.DataFrame({"timestamp": [timestamp], "instrument": ["I"], "x": [1.0]})
    trace = pd.DataFrame(
        {
            "feature": ["x"],
            "timestamp": [timestamp],
            "source": ["synthetic"],
            "observation_date": [timestamp.normalize()],
            "release_date": [timestamp + pd.Timedelta(available_offset)],
            "available_at": [timestamp + pd.Timedelta(available_offset)],
            "window_start": [timestamp],
            "window_end": [timestamp],
            "is_revision": [False],
            "value_missing": [False],
        }
    )
    return features, trace


def test_audit_passes_when_available_at_or_before_timestamp():
    features, trace = _feature_and_trace("-1h")
    result = audit_feature_availability(features, trace, ["x"])
    assert result.summary["critical_violations"] == 0
    assert_audit_pass(result)


def test_audit_fails_closed_on_future_release():
    features, trace = _feature_and_trace("1h")
    result = audit_feature_availability(features, trace, ["x"])
    assert result.summary["critical_violations"] == 1
    with pytest.raises(AssertionError, match="LOOK-AHEAD AUDIT FAILED"):
        assert_audit_pass(result)
