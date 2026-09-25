"""Configuration loading and project path helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_root(root: str | Path | None = None) -> Path:
    """Return the resolved project root."""
    return Path(root).resolve() if root is not None else DEFAULT_PROJECT_ROOT


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML mapping and reject non-mapping documents."""
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {resolved}")
    return data


def load_project_config(name: str, root: str | Path | None = None) -> dict[str, Any]:
    """Load a configuration file from the project's config directory."""
    return load_yaml(project_root(root) / "config" / name)


def resolve_project_path(path: str | Path, root: str | Path | None = None) -> Path:
    """Resolve a project-relative path without requiring the current directory."""
    candidate = Path(path)
    return candidate.resolve() if candidate.is_absolute() else (project_root(root) / candidate).resolve()


def feature_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the configured feature groups while preserving declared order."""
    specs: list[dict[str, Any]] = []
    for group, group_specs in config["groups"].items():
        for raw_spec in group_specs:
            spec = dict(raw_spec)
            spec["group"] = group
            specs.append(spec)
    return specs
