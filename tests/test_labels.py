from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

import src.labels.build_labels as label_module
from src.labels.build_labels import compute_labels, future_realized_volatility


def _manual_series():
    prices = pd.Series([100.0, 102.0, 101.0, 105.0, 104.0, 108.0, 107.0, 109.0])
    returns = np.log(prices / prices.shift(1))
    timestamps = pd.Series(pd.date_range("2025-01-01 20:00", periods=len(prices), tz="Asia/Shanghai"))
    return prices, returns, timestamps


def test_manual_future_volatility_and_log_label():
    _, returns, timestamps = _manual_series()
    labels = compute_labels(returns, timestamps, [3], annualization=252)
    expected_vol = np.sqrt(252 * np.mean(np.square(returns.iloc[1:4])))
    assert np.isclose(labels.loc[0, "logV_h3"], np.log(expected_vol))
    assert labels.loc[0, "label_start_h3"] == timestamps.iloc[1]
    assert labels.loc[0, "label_end_h3"] == timestamps.iloc[3]


def test_last_h_rows_are_missing_without_future_data():
    _, returns, timestamps = _manual_series()
    labels = compute_labels(returns, timestamps, [3])
    assert labels["logV_h3"].tail(3).isna().all()
    assert labels["label_end_h3"].tail(3).isna().all()


def test_shift_direction_uses_t_plus_one_not_t():
    _, returns, _ = _manual_series()
    original = future_realized_volatility(returns, 3)
    changed_current = returns.copy()
    changed_current.iloc[0] = 100.0
    changed_future = returns.copy()
    changed_future.iloc[1] *= 2
    assert np.isclose(future_realized_volatility(changed_current, 3).iloc[0], original.iloc[0])
    assert not np.isclose(future_realized_volatility(changed_future, 3).iloc[0], original.iloc[0])


def test_label_module_has_no_feature_dependency():
    source = inspect.getsource(label_module)
    assert "src.features" not in source
