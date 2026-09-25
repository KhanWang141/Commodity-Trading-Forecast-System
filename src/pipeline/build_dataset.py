"""Build the audited 29-feature commodity research dataset."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src import __version__
from src.audit.asof_audit import assert_audit_pass, audit_feature_availability, write_audit_report
from src.config import feature_specs, load_project_config, resolve_project_path
from src.data.freeze_inputs import freeze_inputs
from src.data.loaders import load_manifest, write_json_atomic, write_parquet_atomic
from src.data.verify_inputs import verify_inputs
from src.features.build_features import build_features
from src.labels.build_labels import build_labels
from src.schema import validate_model_dataset
from src.validation.quality_checks import generate_quality_report


LOGGER = logging.getLogger(__name__)


def _verified_or_frozen(root: str | Path | None = None) -> dict[str, Any]:
    """Verify an existing snapshot, or create the first immutable snapshot."""
    try:
        return verify_inputs(root)
    except FileNotFoundError:
        return freeze_inputs(root)


def build_dataset(root: str | Path | None = None) -> pd.DataFrame:
    """Run verification, feature/label builds, audit, schema validation, and export."""
    manifest = _verified_or_frozen(root)
    feature_config = load_project_config("features.yaml", root)
    label_config = load_project_config("labels.yaml", root)
    specs = feature_specs(feature_config)
    feature_columns = [spec["name"] for spec in specs]
    horizons = [int(value) for value in label_config["horizons"]]
    label_columns = [f"logV_h{horizon}" for horizon in horizons]
    split_columns = [f"split_h{horizon}" for horizon in horizons]

    features, availability, macro_events = build_features(root, write_outputs=True)
    labels = build_labels(root, write_output=True)
    audit = audit_feature_availability(
        features,
        availability,
        feature_columns,
        labels=labels,
        macro_events=macro_events,
    )
    write_audit_report(audit, root)
    assert_audit_pass(audit)

    selected_labels = labels[["timestamp", "instrument", *label_columns, *split_columns]]
    dataset = features.merge(
        selected_labels,
        on=["timestamp", "instrument"],
        how="left",
        validate="one_to_one",
    )
    dataset = dataset[["timestamp", "instrument", *feature_columns, *label_columns, *split_columns]]
    schema_summary = validate_model_dataset(dataset, feature_columns, label_columns)
    output_path = resolve_project_path("data/processed/model_dataset.parquet", root)
    write_parquet_atomic(dataset, output_path)

    metadata = {
        "pipeline_version": __version__,
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "timezone": feature_config["timezone"],
        "instrument": label_config["instrument"],
        "sample_size": len(dataset),
        "column_count": len(dataset.columns),
        "time_range": {
            "min": dataset["timestamp"].min().isoformat(),
            "max": dataset["timestamp"].max().isoformat(),
        },
        "feature_names": feature_columns,
        "label_names": label_columns,
        "split_columns": split_columns,
        "feature_catalog": specs,
        "label_definition": label_config["label_definition"],
        "volatility_definition": label_config["volatility_definition"],
        "annualization": label_config["annualization"],
        "missing_rate": {
            column: float(dataset[column].isna().mean())
            for column in [*feature_columns, *label_columns]
        },
        "source_hashes": {
            entry["name"]: entry["sha256"] for entry in manifest["files"]
        },
        "asof_join": {
            "method": "pandas.merge_asof",
            "direction": "backward",
            "allow_exact_matches": True,
            "constraint": "available_at <= timestamp",
        },
        "audit_summary": audit.summary,
        "known_limitations": audit.summary.get("limitations", []),
    }
    metadata_path = resolve_project_path(
        "data/processed/model_dataset_metadata.json",
        root,
    )
    write_json_atomic(metadata, metadata_path)
    generate_quality_report(
        dataset,
        feature_columns,
        label_columns,
        manifest,
        schema_summary,
        audit.summary,
        root,
    )
    LOGGER.info(
        "DATASET BUILT rows=%s columns=%s range=%s..%s output=%s",
        len(dataset),
        len(dataset.columns),
        dataset["timestamp"].min(),
        dataset["timestamp"].max(),
        output_path,
    )
    return dataset


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_dataset()


if __name__ == "__main__":
    main()
