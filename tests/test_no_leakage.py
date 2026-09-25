from __future__ import annotations

import pandas as pd
import pytest

from src.features.build_features import configured_feature_names
from src.labels.build_labels import build_labels
from src.schema import assert_no_label_leakage


def test_configured_feature_names_have_no_target_tokens():
    assert_no_label_leakage(configured_feature_names())


@pytest.mark.parametrize("name", ["label", "target_value", "future_vol", "forward_return_5"])
def test_target_like_feature_names_are_rejected(name):
    with pytest.raises(AssertionError):
        assert_no_label_leakage([name])


def test_real_label_windows_begin_after_feature_time():
    labels = build_labels(write_output=False)
    for column in [name for name in labels if name.startswith("label_start_h")]:
        populated = labels[column].notna()
        assert (labels.loc[populated, column] > labels.loc[populated, "timestamp"]).all()
