from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml


@pytest.fixture
def tiny_project(tmp_path: Path) -> Path:
    """Create a one-source project for input-freezing tests."""
    (tmp_path / "config").mkdir()
    (tmp_path / "data" / "raw").mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02"],
            "value": [1.0, 2.0],
        }
    )
    frame.to_csv(tmp_path / "data" / "raw" / "sample.csv", index=False)
    config = {
        "timezone": "Asia/Shanghai",
        "manifest_path": "data/manifests/input_manifest.json",
        "sources": {
            "sample": {
                "raw_path": "data/raw/sample.csv",
                "frozen_path": "data/frozen/sample.csv",
                "date_column": "date",
            }
        },
    }
    (tmp_path / "config" / "data_sources.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return tmp_path
