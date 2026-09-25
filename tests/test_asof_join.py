from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.asof import point_in_time_join


def test_value_is_not_visible_before_release():
    timestamps = pd.to_datetime(
        ["2025-01-05 20:00", "2025-01-10 09:29", "2025-01-10 09:30"],
    ).tz_localize("Asia/Shanghai")
    events = pd.DataFrame(
        {
            "available_at": pd.to_datetime(["2025-01-10 09:30"]).tz_localize("Asia/Shanghai"),
            "value": [7.5],
        }
    )
    joined = point_in_time_join(pd.DataFrame({"timestamp": timestamps}), events)
    assert np.isnan(joined.loc[0, "value"])
    assert np.isnan(joined.loc[1, "value"])
    assert joined.loc[2, "value"] == 7.5


def test_revision_uses_only_vintage_known_at_each_timestamp():
    timestamps = pd.to_datetime(["2025-01-15", "2025-01-25"]).tz_localize("Asia/Shanghai")
    events = pd.DataFrame(
        {
            "available_at": pd.to_datetime(["2025-01-10", "2025-01-20"]).tz_localize("Asia/Shanghai"),
            "observation_date": pd.to_datetime(["2024-12-31", "2024-12-31"]).tz_localize("Asia/Shanghai"),
            "value": [1.0, 1.2],
        }
    )
    joined = point_in_time_join(pd.DataFrame({"timestamp": timestamps}), events)
    assert joined["value"].tolist() == [1.0, 1.2]
