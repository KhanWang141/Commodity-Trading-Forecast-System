"""Row-level look-ahead audit for every configured feature."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import load_project_config, resolve_project_path
from src.data.loaders import write_json_atomic
from src.features.build_features import build_features, configured_feature_names
from src.labels.build_labels import build_labels
from src.schema import FORBIDDEN_FEATURE_TOKENS


LOGGER = logging.getLogger(__name__)
REPORT_COLUMNS = [
    "feature",
    "timestamp",
    "source",
    "observation_date",
    "release_date",
    "available_at",
    "violation_type",
    "severity",
    "message",
]


@dataclass(frozen=True)
class AuditResult:
    """Audit outputs suitable for pipeline gating and reporting."""

    violations: pd.DataFrame
    summary: dict[str, Any]


def assert_audit_pass(result: AuditResult) -> None:
    """Fail closed when any critical look-ahead violation is present."""
    critical = int(result.summary["critical_violations"])
    if critical:
        raise AssertionError(f"LOOK-AHEAD AUDIT FAILED with {critical} critical violations")


def _records_from_mask(
    trace: pd.DataFrame,
    mask: pd.Series,
    violation_type: str,
    severity: str,
    message: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in trace.loc[mask].iterrows():
        records.append(
            {
                "feature": row.get("feature"),
                "timestamp": row.get("timestamp"),
                "source": row.get("source"),
                "observation_date": row.get("observation_date"),
                "release_date": row.get("release_date"),
                "available_at": row.get("available_at"),
                "violation_type": violation_type,
                "severity": severity,
                "message": message,
            }
        )
    return records


def audit_feature_availability(
    features: pd.DataFrame,
    availability: pd.DataFrame,
    feature_columns: list[str],
    *,
    labels: pd.DataFrame | None = None,
    macro_events: dict[str, pd.DataFrame] | None = None,
) -> AuditResult:
    """Check availability, rolling windows, label separation, and time alignment."""
    records: list[dict[str, Any]] = []
    expected = len(features) * len(feature_columns)
    if len(availability) != expected:
        records.append(
            {
                "feature": "*",
                "timestamp": pd.NaT,
                "source": "feature_availability",
                "observation_date": pd.NaT,
                "release_date": pd.NaT,
                "available_at": pd.NaT,
                "violation_type": "incomplete_provenance",
                "severity": "critical",
                "message": f"Expected {expected} availability rows, found {len(availability)}.",
            }
        )

    duplicate_mask = availability.duplicated(["feature", "timestamp"], keep=False)
    records.extend(
        _records_from_mask(
            availability,
            duplicate_mask,
            "duplicate_provenance",
            "critical",
            "More than one provenance row exists for a feature timestamp.",
        )
    )
    future_available = (
        availability["available_at"].notna()
        & (availability["available_at"] > availability["timestamp"])
    )
    records.extend(
        _records_from_mask(
            availability,
            future_available,
            "release_after_feature_time",
            "critical",
            "Feature became available after the model timestamp.",
        )
    )
    missing_available = (~availability["value_missing"]) & availability["available_at"].isna()
    records.extend(
        _records_from_mask(
            availability,
            missing_available,
            "missing_availability_time",
            "critical",
            "A populated feature has no availability timestamp.",
        )
    )
    future_window = availability["window_end"].notna() & (
        availability["window_end"] > availability["timestamp"]
    )
    records.extend(
        _records_from_mask(
            availability,
            future_window,
            "rolling_window_uses_future",
            "critical",
            "The feature window ends after the model timestamp.",
        )
    )

    for name in feature_columns:
        if any(token in name.lower() for token in FORBIDDEN_FEATURE_TOKENS):
            records.append(
                {
                    "feature": name,
                    "timestamp": pd.NaT,
                    "source": "feature_schema",
                    "observation_date": pd.NaT,
                    "release_date": pd.NaT,
                    "available_at": pd.NaT,
                    "violation_type": "label_in_features",
                    "severity": "critical",
                    "message": "A target-like column name appears in the feature schema.",
                }
            )

    traced = set(availability["feature"].unique())
    if traced != set(feature_columns):
        records.append(
            {
                "feature": "*",
                "timestamp": pd.NaT,
                "source": "feature_schema",
                "observation_date": pd.NaT,
                "release_date": pd.NaT,
                "available_at": pd.NaT,
                "violation_type": "feature_trace_schema_mismatch",
                "severity": "critical",
                "message": f"Trace features differ from schema: {sorted(traced ^ set(feature_columns))}",
            }
        )

    if features["timestamp"].dt.tz is None or availability["timestamp"].dt.tz is None:
        records.append(
            {
                "feature": "*",
                "timestamp": pd.NaT,
                "source": "timestamp",
                "observation_date": pd.NaT,
                "release_date": pd.NaT,
                "available_at": pd.NaT,
                "violation_type": "timezone_missing",
                "severity": "critical",
                "message": "Feature and audit timestamps must be timezone-aware.",
            }
        )

    if labels is not None:
        merged = features[["timestamp", "instrument"]].merge(
            labels,
            on=["timestamp", "instrument"],
            how="left",
            validate="one_to_one",
        )
        for column in [name for name in labels if name.startswith("label_start_h")]:
            bad = merged[column].notna() & (merged[column] <= merged["timestamp"])
            for timestamp in merged.loc[bad, "timestamp"]:
                records.append(
                    {
                        "feature": column,
                        "timestamp": timestamp,
                        "source": "independent_labels",
                        "observation_date": pd.NaT,
                        "release_date": pd.NaT,
                        "available_at": pd.NaT,
                        "violation_type": "target_window_overlaps_feature_time",
                        "severity": "critical",
                        "message": "The target window must begin strictly after the feature timestamp.",
                    }
                )

    limitations: list[str] = []
    if macro_events is not None:
        for feature, events in macro_events.items():
            if not events["is_revision"].any():
                message = (
                    "No revision vintages are present in the supplied source; final-vintage "
                    "contamination cannot be independently ruled out."
                )
                limitations.append(f"{feature}: {message}")
                records.append(
                    {
                        "feature": feature,
                        "timestamp": features["timestamp"].min(),
                        "source": f"features_asof:{feature}",
                        "observation_date": pd.NaT,
                        "release_date": pd.NaT,
                        "available_at": pd.NaT,
                        "violation_type": "revision_vintage_unavailable",
                        "severity": "warning",
                        "message": message,
                    }
                )

    violations = pd.DataFrame.from_records(records, columns=REPORT_COLUMNS)
    critical = int((violations["severity"] == "critical").sum()) if not violations.empty else 0
    warning = int((violations["severity"] == "warning").sum()) if not violations.empty else 0
    total_checked = int(len(availability))
    summary = {
        "status": "PASS" if critical == 0 else "FAIL",
        "total_rows_checked": total_checked,
        "total_features": len(feature_columns),
        "violations": int(len(violations)),
        "critical_violations": critical,
        "warning_violations": warning,
        "pass_rate": 1.0 if total_checked == 0 else max(0.0, 1.0 - critical / total_checked),
        "limitations": limitations,
    }
    return AuditResult(violations=violations, summary=summary)


def write_audit_report(
    result: AuditResult,
    root: str | Path | None = None,
) -> None:
    """Persist the row-level report and machine-readable summary."""
    report_path = resolve_project_path("reports/asof_audit.csv", root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result.violations.to_csv(report_path, index=False)
    write_json_atomic(result.summary, resolve_project_path("reports/asof_audit_summary.json", root))


def run_asof_audit(root: str | Path | None = None) -> AuditResult:
    """Run the audit from independently rebuilt feature and label artifacts."""
    features, availability, macro_events = build_features(root, write_outputs=False)
    labels = build_labels(root, write_output=False)
    names = configured_feature_names(root)
    result = audit_feature_availability(
        features,
        availability,
        names,
        labels=labels,
        macro_events=macro_events,
    )
    write_audit_report(result, root)
    assert_audit_pass(result)
    LOGGER.info(
        "LOOK-AHEAD AUDIT: PASS rows=%s features=%s warnings=%s",
        result.summary["total_rows_checked"],
        result.summary["total_features"],
        result.summary["warning_violations"],
    )
    return result


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_asof_audit()


if __name__ == "__main__":
    main()
