from __future__ import annotations

import stat

from src.data.freeze_inputs import freeze_inputs


def test_freeze_creates_manifest_and_read_only_snapshot(tiny_project):
    manifest = freeze_inputs(tiny_project)
    frozen = tiny_project / "data" / "frozen" / "sample.csv"
    assert frozen.exists()
    assert manifest["files"][0]["row_count"] == 2
    assert len(manifest["files"][0]["sha256"]) == 64
    assert not (frozen.stat().st_mode & stat.S_IWUSR)


def test_freeze_is_idempotent_when_raw_input_is_unchanged(tiny_project):
    first = freeze_inputs(tiny_project)
    second = freeze_inputs(tiny_project)
    assert first == second
