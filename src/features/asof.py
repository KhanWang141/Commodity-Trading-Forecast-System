"""Strict point-in-time joins."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def point_in_time_join(
    left: pd.DataFrame,
    events: pd.DataFrame,
    *,
    left_on: str = "timestamp",
    available_on: str = "available_at",
    by: str | Sequence[str] | None = None,
) -> pd.DataFrame:
    """Backward as-of join that asserts no event is used before publication."""
    if left_on not in left or available_on not in events:
        raise KeyError(f"Join keys must include {left_on!r} and {available_on!r}")
    if left[left_on].isna().any():
        raise ValueError(f"Left as-of key {left_on!r} contains missing timestamps")
    right = events.loc[events[available_on].notna()].copy()
    left_sorted = left.sort_values(left_on, kind="stable").copy()
    right_sorted = right.sort_values(available_on, kind="stable")
    result = pd.merge_asof(
        left_sorted,
        right_sorted,
        left_on=left_on,
        right_on=available_on,
        by=by,
        direction="backward",
        allow_exact_matches=True,
    )
    known = result[available_on].notna()
    if (result.loc[known, available_on] > result.loc[known, left_on]).any():
        raise AssertionError("Point-in-time join produced future information")
    return result
