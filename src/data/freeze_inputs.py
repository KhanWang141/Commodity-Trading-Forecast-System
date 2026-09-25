"""Create immutable input snapshots and their SHA-256 manifest."""

from __future__ import annotations

import logging
import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import load_project_config, resolve_project_path
from src.data.hashing import profile_csv, sha256_file
from src.data.loaders import write_json_atomic
from src.data.verify_inputs import InputIntegrityError, verify_inputs


LOGGER = logging.getLogger(__name__)


def _make_read_only(path: Path) -> None:
    """Remove write bits as an additional guard around hash validation."""
    path.chmod(path.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def freeze_inputs(root: str | Path | None = None) -> dict[str, Any]:
    """Freeze configured raw inputs without silently overwriting snapshots."""
    config = load_project_config("data_sources.yaml", root)
    manifest_path = resolve_project_path(config["manifest_path"], root)
    if manifest_path.exists():
        manifest = verify_inputs(root)
        for entry in manifest["files"]:
            raw_path = resolve_project_path(config["sources"][entry["name"]]["raw_path"], root)
            raw_hash = sha256_file(raw_path)
            if raw_hash != entry["sha256"]:
                raise InputIntegrityError(
                    f"Raw input {raw_path.name} changed after freezing. Create a new snapshot "
                    "and manifest explicitly instead of overwriting the current experiment."
                )
        LOGGER.info("Frozen inputs already exist and match the manifest.")
        return manifest

    files: list[dict[str, Any]] = []
    for name, spec in config["sources"].items():
        raw_path = resolve_project_path(spec["raw_path"], root)
        frozen_path = resolve_project_path(spec["frozen_path"], root)
        if not raw_path.is_file():
            raise FileNotFoundError(f"Raw input not found: {raw_path}")
        raw_hash = sha256_file(raw_path)
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        if frozen_path.exists():
            if sha256_file(frozen_path) != raw_hash:
                raise FileExistsError(
                    f"Refusing to overwrite non-matching frozen input: {frozen_path}"
                )
        else:
            temporary = frozen_path.with_suffix(frozen_path.suffix + ".tmp")
            shutil.copy2(raw_path, temporary)
            os.replace(temporary, frozen_path)
        _make_read_only(frozen_path)
        profile = profile_csv(frozen_path, spec["date_column"])
        entry = {
            "name": name,
            "filename": frozen_path.name,
            "raw_path": str(Path(spec["raw_path"]).as_posix()),
            "frozen_path": str(Path(spec["frozen_path"]).as_posix()),
            "sha256": raw_hash,
            **profile,
        }
        files.append(entry)
        LOGGER.info(
            "FROZEN file=%s sha256=%s rows=%s range=%s..%s",
            frozen_path.name,
            raw_hash,
            profile["row_count"],
            profile["min_date"],
            profile["max_date"],
        )

    manifest = {
        "manifest_version": 1,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    write_json_atomic(manifest, manifest_path)
    verify_inputs(root)
    return manifest


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    freeze_inputs()


if __name__ == "__main__":
    main()
