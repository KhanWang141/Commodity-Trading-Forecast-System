from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.build_features import compute_market_feature, configured_feature_names


def test_trailing_cumulative_return_matches_log_return_math():
    returns = pd.Series([0.01, -0.02, 0.03, 0.04])
    result = compute_market_feature(returns, transform="cumulative_log_return", window=3)
    assert np.isnan(result.iloc[1])
    assert np.isclose(result.iloc[2], np.expm1(returns.iloc[0:3].sum()))
    assert np.isclose(result.iloc[3], np.expm1(returns.iloc[1:4].sum()))


def test_annualized_rms_volatility_matches_manual_value():
    returns = pd.Series([0.01, -0.02, 0.03])
    result = compute_market_feature(returns, transform="annualized_rms_return", window=3)
    expected = np.sqrt(252 * np.mean(np.square(returns)))
    assert np.isclose(result.iloc[-1], expected)


def test_future_data_cannot_change_past_features():
    returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.02])
    original = compute_market_feature(returns, transform="annualized_rms_return", window=5)
    perturbed = returns.copy()
    perturbed.iloc[6:] = [9.0, -9.0]
    changed = compute_market_feature(perturbed, transform="annualized_rms_return", window=5)
    pd.testing.assert_series_equal(original.iloc[:6], changed.iloc[:6])


def test_config_contains_29_unique_features():
    names = configured_feature_names()
    assert len(names) == 29
    assert len(set(names)) == 29
