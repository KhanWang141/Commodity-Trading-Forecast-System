from __future__ import annotations

import stat

import pytest

from src.data.freeze_inputs import freeze_inputs
from src.data.verify_inputs import InputIntegrityError, verify_inputs


def test_modified_frozen_file_fails_hash_validation(tiny_project):
    freeze_inputs(tiny_project)
    frozen = tiny_project / "data" / "frozen" / "sample.csv"
    frozen.chmod(frozen.stat().st_mode | stat.S_IWUSR)
    try:
        with frozen.open("a", encoding="utf-8") as handle:
            handle.write("2025-01-03,3\n")
        with pytest.raises(InputIntegrityError, match="Frozen input modified"):
            verify_inputs(tiny_project)
    finally:
        frozen.chmod(frozen.stat().st_mode | stat.S_IWUSR)


def test_changed_raw_file_cannot_overwrite_snapshot(tiny_project):
    freeze_inputs(tiny_project)
    raw = tiny_project / "data" / "raw" / "sample.csv"
    with raw.open("a", encoding="utf-8") as handle:
        handle.write("2025-01-03,3\n")
    with pytest.raises(InputIntegrityError, match="changed after freezing"):
        freeze_inputs(tiny_project)
