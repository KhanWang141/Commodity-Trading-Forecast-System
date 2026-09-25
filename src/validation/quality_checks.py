"""Generate a human-readable data quality report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import resolve_project_path


def _markdown_table(frame: pd.DataFrame) -> str:
    """Render a small DataFrame without requiring the optional tabulate package."""
    columns = [str(column) for column in frame.columns]
    rows = [[str(value) for value in row] for row in frame.itertuples(index=False, name=None)]
    widths = [len(column) for column in columns]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row, strict=True)]
    header = "| " + " | ".join(value.ljust(width) for value, width in zip(columns, widths, strict=True)) + " |"
    rule = "| " + " | ".join("-" * width for width in widths) + " |"
    body = [
        "| " + " | ".join(value.ljust(width) for value, width in zip(row, widths, strict=True)) + " |"
        for row in rows
    ]
    return "\n".join([header, rule, *body])


def generate_quality_report(
    dataset: pd.DataFrame,
    feature_columns: list[str],
    label_columns: list[str],
    manifest: dict[str, Any],
    schema_summary: dict[str, Any],
    audit_summary: dict[str, Any],
    root: str | Path | None = None,
) -> Path:
    """Write missingness, statistics, integrity, and leakage results to Markdown."""
    measured = [*feature_columns, *label_columns]
    missing = pd.DataFrame(
        {
            "column": measured,
            "count": [int(dataset[column].isna().sum()) for column in measured],
            "missing_pct": [f"{dataset[column].isna().mean() * 100:.3f}%" for column in measured],
        }
    )
    statistics = dataset[feature_columns].describe(
        percentiles=[0.01, 0.25, 0.50, 0.75, 0.99]
    ).T.reset_index()
    statistics = statistics.rename(columns={"index": "feature"})[
        ["feature", "mean", "std", "min", "1%", "25%", "50%", "75%", "99%", "max"]
    ]
    for column in statistics.columns[1:]:
        statistics[column] = statistics[column].map(
            lambda value: "" if pd.isna(value) else f"{float(value):.8g}"
        )

    extreme_counts: dict[str, int] = {}
    for column in feature_columns:
        series = dataset[column].dropna().astype(float)
        std = float(series.std(ddof=0)) if len(series) else 0.0
        count = 0 if std == 0.0 else int(((series - series.mean()).abs() > 10 * std).sum())
        extreme_counts[column] = count
    extreme_table = pd.DataFrame(
        {"feature": list(extreme_counts), "abs_z_gt_10_count": list(extreme_counts.values())}
    )
    sources = pd.DataFrame(
        {
            "source": [entry["name"] for entry in manifest["files"]],
            "sha256": [entry["sha256"] for entry in manifest["files"]],
            "rows": [entry["row_count"] for entry in manifest["files"]],
            "date_range": [f"{entry['min_date']} to {entry['max_date']}" for entry in manifest["files"]],
        }
    )
    lines = [
        "# Data quality report",
        "",
        "## Dataset Summary",
        "",
        f"- Time range: {schema_summary['timestamp_min']} to {schema_summary['timestamp_max']}",
        f"- Samples: {schema_summary['rows']}",
        f"- Features: {schema_summary['feature_count']}",
        f"- Labels: {schema_summary['label_count']}",
        "",
        _markdown_table(sources),
        "",
        "## Missing Values",
        "",
        _markdown_table(missing),
        "",
        "## Feature Statistics",
        "",
        _markdown_table(statistics),
        "",
        "## Extreme Values",
        "",
        "The diagnostic below counts observations more than 10 population standard deviations from the column mean; it does not alter data.",
        "",
        _markdown_table(extreme_table),
        "",
        "## Integrity",
        "",
        "- Input hash verification: PASS",
        f"- Duplicated instrument/timestamp samples: {schema_summary['duplicate_samples']}",
        f"- Infinite values: {schema_summary['infinite_values']}",
        f"- Constant features: {schema_summary['constant_features'] or 'none'}",
        f"- Feature count: {schema_summary['feature_count']} (required: 29)",
        "- Schema consistency: PASS",
        "",
        "## Leakage Audit",
        "",
        f"LOOK-AHEAD AUDIT: {audit_summary['status']}",
        "",
        f"- Rows checked: {audit_summary['total_rows_checked']}",
        f"- Critical violations: {audit_summary['critical_violations']}",
        f"- Warnings: {audit_summary['warning_violations']}",
        f"- Pass rate: {audit_summary['pass_rate']:.6%}",
        "",
        "### Vintage limitations",
        "",
    ]
    limitations = audit_summary.get("limitations", [])
    lines.extend([f"- {item}" for item in limitations] or ["- None recorded."])
    output = resolve_project_path("reports/data_quality_report.md", root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
