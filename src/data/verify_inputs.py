"""Verify immutable frozen inputs against the recorded manifest."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config import load_project_config, resolve_project_path
from src.data.hashing import sha256_file
from src.data.loaders import load_manifest


LOGGER = logging.getLogger(__name__)


class InputIntegrityError(RuntimeError):
    """Raised when a frozen input differs from its manifest."""


def verify_inputs(root: str | Path | None = None) -> dict[str, Any]:
    """Verify every frozen file hash and size, failing on the first mismatch."""
    manifest = load_manifest(root)
    config = load_project_config("data_sources.yaml", root)
    configured_names = set(config["sources"])
    manifest_names = {entry["name"] for entry in manifest["files"]}
    if configured_names != manifest_names:
        raise InputIntegrityError(
            f"Manifest sources {sorted(manifest_names)} do not match configuration "
            f"{sorted(configured_names)}"
        )

    for entry in manifest["files"]:
        path = resolve_project_path(entry["frozen_path"], root)
        if not path.is_file():
            raise InputIntegrityError(f"Missing frozen file: {path}")
        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        if actual_size != entry["size_bytes"] or actual_hash != entry["sha256"]:
            raise InputIntegrityError(
                f"Frozen input modified: {path.name}; expected sha256={entry['sha256']} "
                f"size={entry['size_bytes']}, actual sha256={actual_hash} size={actual_size}"
            )
        LOGGER.info(
            "PASS file=%s sha256=%s rows=%s range=%s..%s",
            path.name,
            actual_hash,
            entry["row_count"],
            entry["min_date"],
            entry["max_date"],
        )
    return manifest


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    verify_inputs()


if __name__ == "__main__":
    main()
