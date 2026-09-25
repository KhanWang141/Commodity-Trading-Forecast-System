"""Build future realized-volatility labels independently of feature code."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import load_project_config, resolve_project_path
from src.data.loaders import localize_timestamp, read_frozen_csv, write_parquet_atomic
from src.data.verify_inputs import verify_inputs


LOGGER = logging.getLogger(__name__)


def future_realized_volatility(
    returns: pd.Series,
    horizon: int,
    *,
    annualization: int = 252,
) -> pd.Series:
    """Compute annualized RMS volatility from returns t+1 through t+h."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    values = pd.to_numeric(returns, errors="coerce").astype(float)
    future = pd.concat([values.shift(-step) for step in range(1, horizon + 1)], axis=1)
    future_sum_squares = future.pow(2).sum(axis=1, min_count=horizon)
    return np.sqrt(future_sum_squares * (annualization / horizon))


def future_cumulative_return(returns: pd.Series, horizon: int) -> pd.Series:
    """Compute the cumulative simple return implied by future log returns."""
    values = pd.to_numeric(returns, errors="coerce").astype(float)
    future = pd.concat([values.shift(-step) for step in range(1, horizon + 1)], axis=1)
    summed = future.sum(axis=1, min_count=horizon)
    return np.expm1(summed)


def compute_labels(
    returns: pd.Series,
    timestamps: pd.Series,
    horizons: list[int],
    *,
    annualization: int = 252,
) -> pd.DataFrame:
    """Compute log-volatility labels and their explicit future window bounds."""
    result = pd.DataFrame({"timestamp": timestamps})
    for horizon in horizons:
        volatility = future_realized_volatility(
            returns,
            horizon,
            annualization=annualization,
        )
        log_volatility = pd.Series(np.nan, index=volatility.index, dtype=float)
        positive = volatility > 0
        log_volatility.loc[positive] = np.log(volatility.loc[positive])
        result[f"logV_h{horizon}"] = log_volatility
        result[f"label_start_h{horizon}"] = timestamps.shift(-1)
        result[f"label_end_h{horizon}"] = timestamps.shift(-horizon)
    return result


def _assert_reference_equal(calculated: pd.Series, reference: pd.Series, name: str) -> None:
    """Validate an independent calculation against the supplied reference target."""
    actual = pd.to_numeric(calculated, errors="coerce").to_numpy(dtype=float)
    expected = pd.to_numeric(reference, errors="coerce").to_numpy(dtype=float)
    if not np.array_equal(np.isnan(actual), np.isnan(expected)):
        raise AssertionError(f"Reference missing-value mismatch for {name}")
    mask = ~np.isnan(actual)
    if not np.allclose(actual[mask], expected[mask], rtol=1e-11, atol=1e-13):
        maximum = float(np.max(np.abs(actual[mask] - expected[mask])))
        raise AssertionError(f"Reference mismatch for {name}; max_abs={maximum}")


def build_labels(
    root: str | Path | None = None,
    *,
    write_output: bool = True,
) -> pd.DataFrame:
    """Build labels from frozen returns without importing feature construction."""
    verify_inputs(root)
    config = load_project_config("labels.yaml", root)
    data_config = load_project_config("data_sources.yaml", root)
    timezone = data_config["timezone"]
    market = read_frozen_csv(config["return_source"], root)
    reference = read_frozen_csv(config["reference_source"], root)
    if not market["date"].equals(reference["date"]):
        raise AssertionError("Market and target reference dates are not aligned")

    timestamp = localize_timestamp(market[config["timestamp_column"]], timezone)
    returns = pd.to_numeric(market[config["return_column"]], errors="coerce")
    horizons = [int(value) for value in config["horizons"]]
    labels = compute_labels(
        returns,
        timestamp,
        horizons,
        annualization=int(config["annualization"]),
    )
    labels.insert(1, "instrument", config["instrument"])

    for horizon in horizons:
        volatility = future_realized_volatility(
            returns,
            horizon,
            annualization=int(config["annualization"]),
        )
        cumulative_return = future_cumulative_return(returns, horizon)
        _assert_reference_equal(
            volatility,
            reference[f"{config['reference_volatility_prefix']}{horizon}"],
            f"y_vol_{horizon}",
        )
        _assert_reference_equal(
            cumulative_return,
            reference[f"{config['reference_return_prefix']}{horizon}"],
            f"y_return_{horizon}",
        )
        expected_start = pd.to_datetime(reference[f"label_start_{horizon}"], errors="coerce")
        expected_end = pd.to_datetime(reference[f"label_end_{horizon}"], errors="coerce")
        calculated_start = labels[f"label_start_h{horizon}"].dt.tz_localize(None).dt.normalize()
        calculated_end = labels[f"label_end_h{horizon}"].dt.tz_localize(None).dt.normalize()
        if not calculated_start.equals(expected_start):
            raise AssertionError(f"Label start timestamps differ for horizon {horizon}")
        if not calculated_end.equals(expected_end):
            raise AssertionError(f"Label end timestamps differ for horizon {horizon}")
        labels[f"split_h{horizon}"] = reference[f"split_{horizon}"].astype("string")

    if write_output:
        write_parquet_atomic(labels, resolve_project_path(config["output_path"], root))
    LOGGER.info("Built independent labels for horizons=%s rows=%s", horizons, len(labels))
    return labels


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_labels()


if __name__ == "__main__":
    main()
