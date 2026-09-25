"""Build the configured 29-column causal feature matrix."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import feature_specs, load_project_config, resolve_project_path
from src.data.loaders import localize_timestamp, read_frozen_csv, write_parquet_atomic
from src.data.verify_inputs import verify_inputs
from src.features.asof import point_in_time_join


LOGGER = logging.getLogger(__name__)


def configured_feature_names(root: str | Path | None = None) -> list[str]:
    """Return the ordered, immutable feature schema from configuration."""
    config = load_project_config("features.yaml", root)
    return [spec["name"] for spec in feature_specs(config)]


def compute_market_feature(
    returns: pd.Series,
    *,
    transform: str,
    window: int,
    annualization: int = 252,
) -> pd.Series:
    """Compute a trailing market feature using observations no later than t."""
    values = pd.to_numeric(returns, errors="coerce").astype(float)
    if transform == "identity":
        if window != 1:
            raise ValueError("Identity market features must use window=1")
        return values.copy()
    rolling = values.rolling(window=window, min_periods=window, center=False)
    if transform == "cumulative_log_return":
        return np.expm1(rolling.sum())
    if transform == "annualized_rms_return":
        return np.sqrt(rolling.apply(lambda x: float(np.mean(np.square(x))), raw=True) * annualization)
    raise ValueError(f"Unsupported market transform: {transform}")


def _assert_equivalent(actual: pd.Series, expected: pd.Series, name: str) -> None:
    """Assert values and missingness match an upstream reference column."""
    actual_numeric = pd.to_numeric(actual, errors="coerce").to_numpy(dtype=float)
    expected_numeric = pd.to_numeric(expected, errors="coerce").to_numpy(dtype=float)
    if not np.array_equal(np.isnan(actual_numeric), np.isnan(expected_numeric)):
        raise AssertionError(f"Missing-value pattern differs for {name}")
    mask = ~np.isnan(actual_numeric)
    if not np.allclose(actual_numeric[mask], expected_numeric[mask], rtol=1e-11, atol=1e-13):
        maximum = float(np.max(np.abs(actual_numeric[mask] - expected_numeric[mask])))
        raise AssertionError(f"Independent reconstruction mismatch for {name}; max_abs={maximum}")


def _localized_optional(values: pd.Series, timezone: str) -> pd.Series:
    """Parse an optional timestamp/date series in the project timezone."""
    return localize_timestamp(values, timezone)


def extract_macro_events(source: pd.DataFrame, name: str, timezone: str) -> pd.DataFrame:
    """Collapse a daily as-of column into publication events, retaining null tombstones."""
    release_column = f"{name}_release_time"
    observation_column = f"{name}_period_end"
    period_start_column = f"{name}_period_start"
    joint_column = f"{name}_joint_jan_feb"
    missing_column = f"{name}_missing_latest_release"
    required = [
        "forecast_time",
        name,
        release_column,
        observation_column,
        period_start_column,
        joint_column,
        missing_column,
    ]
    missing = [column for column in required if column not in source]
    if missing:
        raise KeyError(f"Macro source {name} is missing metadata columns: {missing}")

    daily = source[required].copy()
    daily = daily.rename(
        columns={
            "forecast_time": "feature_timestamp",
            name: "value",
            release_column: "release_date",
            observation_column: "observation_date",
            period_start_column: "period_start",
            joint_column: "joint_jan_feb",
            missing_column: "missing_latest_release",
        }
    )
    daily["feature_timestamp"] = _localized_optional(daily["feature_timestamp"], timezone)
    daily["release_date"] = _localized_optional(daily["release_date"], timezone)
    daily["observation_date"] = _localized_optional(daily["observation_date"], timezone)
    daily["period_start"] = _localized_optional(daily["period_start"], timezone)
    daily["value"] = pd.to_numeric(daily["value"], errors="coerce")
    daily["missing_latest_release"] = daily["missing_latest_release"].fillna(False).astype(bool)

    state_columns = [
        "value",
        "release_date",
        "observation_date",
        "period_start",
        "joint_jan_feb",
        "missing_latest_release",
    ]
    previous = daily[state_columns].shift(1)
    same = daily[state_columns].eq(previous) | (daily[state_columns].isna() & previous.isna())
    changed = ~same.all(axis=1)
    meaningful = (
        daily["value"].notna()
        | daily["release_date"].notna()
        | daily["missing_latest_release"]
    )
    events = daily.loc[changed & meaningful].copy()
    # A null tombstone begins when the source first reports that the expected
    # latest release is missing. Its availability is that detection timestamp,
    # while release_date preserves the last actual publication shown upstream.
    events["available_at"] = events["release_date"].where(
        events["value"].notna(),
        events["feature_timestamp"],
    )
    events = events.sort_values("available_at", kind="stable")
    if events["available_at"].duplicated().any():
        raise AssertionError(f"Conflicting state changes share an availability time for {name}")
    populated = events["value"].notna()
    events["vintage_number"] = 0
    events.loc[populated, "vintage_number"] = (
        events.loc[populated].groupby("observation_date", dropna=False).cumcount() + 1
    )
    events["is_revision"] = events["vintage_number"] > 1
    events["feature"] = name
    return events.reset_index(drop=True)


def build_features(
    root: str | Path | None = None,
    *,
    write_outputs: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """Recompute market features and rebuild macro values with point-in-time joins."""
    verify_inputs(root)
    config = load_project_config("features.yaml", root)
    specs = feature_specs(config)
    names = [spec["name"] for spec in specs]
    if len(names) != config["feature_count"] or len(set(names)) != config["feature_count"]:
        raise AssertionError("Feature configuration must contain 29 unique names")

    source = read_frozen_csv(config["source"], root)
    timezone = config["timezone"]
    timestamp = localize_timestamp(source["forecast_time"], timezone)
    if not timestamp.is_monotonic_increasing or timestamp.duplicated().any():
        raise AssertionError("Forecast timestamps must be increasing and unique")
    features = pd.DataFrame({"timestamp": timestamp, "instrument": "I"})
    traces: list[pd.DataFrame] = []
    macro_events: dict[str, pd.DataFrame] = {}
    observation_dates = _localized_optional(source["date"], timezone)

    for spec in specs:
        name = spec["name"]
        if spec["release_lag"] == "available_at_forecast_time":
            calculated = compute_market_feature(
                source[spec["return_column"]],
                transform=spec["transform"],
                window=int(spec["window"]),
                annualization=int(config["annualization"]),
            )
            lag = int(spec.get("lag", 0))
            if lag:
                calculated = calculated.shift(lag)
            _assert_equivalent(calculated, source[spec["source_column"]], name)
            features[name] = calculated
            window = int(spec["window"])
            trace = pd.DataFrame(
                {
                    "feature": name,
                    "timestamp": timestamp,
                    "source": spec["source"],
                    "observation_date": observation_dates,
                    "release_date": timestamp,
                    "available_at": timestamp,
                    "window_start": timestamp.shift(window - 1),
                    "window_end": timestamp,
                    "is_revision": False,
                    "value_missing": calculated.isna(),
                }
            )
            traces.append(trace)
            continue

        events = extract_macro_events(source, name, timezone)
        macro_events[name] = events.copy()
        event_columns = [
            "available_at",
            "release_date",
            "observation_date",
            "period_start",
            "value",
            "is_revision",
            "missing_latest_release",
        ]
        joined = point_in_time_join(
            pd.DataFrame({"timestamp": timestamp}),
            events[event_columns],
        )
        _assert_equivalent(joined["value"], source[spec["source_column"]], name)
        source_release = _localized_optional(source[f"{name}_release_time"], timezone)
        joined_release = joined["release_date"].reset_index(drop=True)
        expected_release = source_release.reset_index(drop=True)
        same_release = joined_release.eq(expected_release) | (
            joined_release.isna() & expected_release.isna()
        )
        if not same_release.all():
            raise AssertionError(f"Publication timestamp reconstruction mismatch for {name}")
        features[name] = joined["value"].to_numpy()
        trace = pd.DataFrame(
            {
                "feature": name,
                "timestamp": timestamp,
                "source": spec["source"],
                "observation_date": joined["observation_date"],
                "release_date": joined["release_date"],
                "available_at": joined["available_at"],
                "window_start": pd.NaT,
                # Macro observation periods can legitimately end after an early
                # publication (for example month-end PMI). Publication time,
                # not period-end, controls availability; rolling-window checks
                # therefore do not use this field for macro features.
                "window_end": pd.NaT,
                "is_revision": joined["is_revision"].fillna(False).astype(bool),
                "value_missing": joined["value"].isna(),
            }
        )
        traces.append(trace)

    availability = pd.concat(traces, ignore_index=True)
    if len(availability) != len(features) * len(names):
        raise AssertionError("Availability trace is incomplete")
    features = features[["timestamp", "instrument", *names]]
    if write_outputs:
        write_parquet_atomic(features, resolve_project_path(config["output_path"], root))
        write_parquet_atomic(
            availability,
            resolve_project_path(config["availability_output_path"], root),
        )
    LOGGER.info("Built %s rows and %s configured features", len(features), len(names))
    return features, availability, macro_events


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_features()


if __name__ == "__main__":
    main()
