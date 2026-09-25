#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare the frozen iron-ore dataset for the Continuous Volatility Forecasting V1.0 protocol.

What this script DOES
---------------------
1. Reads ONLY the frozen source files:
   - features_asof.csv
   - targets_and_splits.csv
2. Keeps the original source data unchanged and records SHA256 hashes.
3. Uses the fixed A / AB / ABC feature groups:
   A   = 6 iron-ore own-market features (5/22/66-day return + volatility)
   AB  = A + 18 RB/J/JM related-futures features
   ABC = AB + 5 macro features
4. Does NOT impute missing values.
5. Builds eligible_continuous_5 and eligible_continuous_20 using the common ABC sample.
6. Verifies y_vol_5 / y_vol_20 independently from I_r.
7. Audits release-time constraints for the selected macro variables.
8. Produces directly usable h=5 and h=20 modelling datasets.

What this script DOES NOT DO
----------------------------
- It does not use old split_5 / split_20.
- It does not use risk_threshold or y_high_vol labels.
- It does not standardize globally..
- It does not perform PCA / Granger screening / imputation.
- It does not train any forecasting model.

Usage
-----
python prepare_continuous_v1.py --input data.zip --output continuous_forecast_v1_data

or, if data.zip has already been extracted:
python prepare_continuous_v1.py --input path/to/data --output continuous_forecast_v1_data
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


PROTOCOL_VERSION = "continuous_forecast_v1.0"
OOS_START = pd.Timestamp("2023-01-01")
ANNUALIZATION = 252

A_FEATURES = [
    "I_cumret_5",
    "I_daily_squared_return_vol_5",
    "I_cumret_22",
    "I_daily_squared_return_vol_22",
    "I_cumret_66",
    "I_daily_squared_return_vol_66",
]

B_ADD_FEATURES = [
    f"{symbol}_{kind}_{window}"
    for symbol in ["RB", "J", "JM"]
    for window in [5, 22, 66]
    for kind in ["cumret", "daily_squared_return_vol"]
]

C_ADD_FEATURES = [
    "cpi_yoy",
    "ppi_yoy",
    "pmi_manufacturing",
    "industrial_value_added_yoy",
    "industrial_value_added_yoy_joint_jan_feb",
]

AB_FEATURES = A_FEATURES + B_ADD_FEATURES
ABC_FEATURES = AB_FEATURES + C_ADD_FEATURES

EXPECTED = {
    5: {
        "eligible": 1716,
        "first": "2019-04-12",
        "last": "2026-08-24",
        "pre2023_mature": 829,
        "oos": 882,
        "oos_by_year": {2023: 242, 2024: 242, 2025: 243, 2026: 155},
    },
    20: {
        "eligible": 1700,
        "first": "2019-07-30",
        "last": "2026-08-03",
        "pre2023_mature": 813,
        "oos": 867,
        "oos_by_year": {2023: 242, 2024: 242, 2025: 243, 2026: 140},
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_data_root(input_path: Path, temp_dir: Path) -> Path:
    """Return directory containing frozen/features_asof.csv and frozen/targets_and_splits.csv."""
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        extract_root = temp_dir / "unzipped"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(extract_root)
        search_root = extract_root
    elif input_path.is_dir():
        search_root = input_path
    else:
        raise FileNotFoundError(f"Input does not exist or is not a zip/directory: {input_path}")

    candidates = []
    for p in search_root.rglob("features_asof.csv"):
        if p.parent.name == "frozen" and (p.parent / "targets_and_splits.csv").exists():
            candidates.append(p.parent.parent)

    if len(candidates) == 0:
        raise FileNotFoundError(
            "Could not find frozen/features_asof.csv + frozen/targets_and_splits.csv under input."
        )
    if len(candidates) > 1:
        raise RuntimeError(f"Multiple candidate data roots found: {candidates}")
    return candidates[0]


def require_columns(df: pd.DataFrame, cols: List[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{name} is missing required columns: {missing}")


def forward_vol_from_returns(r: pd.Series, h: int) -> np.ndarray:
    """
    Recalculate V_{t,h} = sqrt(252/h * sum_{i=1}^h r_{t+i}^2).
    If any of the h future returns is missing, target is NaN.
    """
    x = pd.to_numeric(r, errors="coerce").to_numpy(dtype=float)
    out = np.full(len(x), np.nan, dtype=float)
    for i in range(0, len(x) - h):
        w = x[i + 1 : i + h + 1]
        if np.isfinite(w).all():
            out[i] = math.sqrt((ANNUALIZATION / h) * float(np.sum(w * w)))
    return out


def verify_targets(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in [5, 20]:
        recalculated = forward_vol_from_returns(merged["I_r"], h)
        frozen = pd.to_numeric(merged[f"y_vol_{h}"], errors="coerce").to_numpy(dtype=float)
        both = np.isfinite(recalculated) & np.isfinite(frozen)
        finite_equal = np.allclose(
            recalculated[both], frozen[both], rtol=1e-10, atol=1e-12
        )
        same_nan_pattern = np.array_equal(np.isnan(recalculated), np.isnan(frozen))
        max_abs_diff = (
            float(np.max(np.abs(recalculated[both] - frozen[both]))) if both.any() else np.nan
        )
        rows.append(
            {
                "horizon": h,
                "finite_values_equal": bool(finite_equal),
                "same_nan_pattern": bool(same_nan_pattern),
                "allclose_pass": bool(finite_equal and same_nan_pattern),
                "n_compared": int(both.sum()),
                "max_abs_diff": max_abs_diff,
            }
        )
    return pd.DataFrame(rows)


def release_time_audit(features: pd.DataFrame) -> pd.DataFrame:
    """Audit selected macro variables: whenever value exists, release_time <= forecast_time."""
    rows = []
    forecast_time = pd.to_datetime(features["forecast_time"], errors="coerce")
    for var in ["cpi_yoy", "ppi_yoy", "pmi_manufacturing", "industrial_value_added_yoy"]:
        release_col = f"{var}_release_time"
        require_columns(features, [var, release_col], "features_asof.csv")
        release = pd.to_datetime(features[release_col], errors="coerce")
        value_present = features[var].notna()
        release_missing_when_value_present = value_present & release.isna()
        future_release = value_present & release.notna() & (release > forecast_time)
        rows.append(
            {
                "variable": var,
                "n_value_present": int(value_present.sum()),
                "n_release_missing_when_value_present": int(release_missing_when_value_present.sum()),
                "n_future_release_violations": int(future_release.sum()),
                "status": "PASS"
                if (release_missing_when_value_present.sum() == 0 and future_release.sum() == 0)
                else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def build_dataset(features: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        features,
        ["date", "forecast_time", "I_r"] + ABC_FEATURES,
        "features_asof.csv",
    )
    require_columns(
        targets,
        ["date", "y_vol_5", "label_end_5", "y_vol_20", "label_end_20"],
        "targets_and_splits.csv",
    )

    if features["date"].duplicated().any():
        raise ValueError("features_asof.csv contains duplicated dates.")
    if targets["date"].duplicated().any():
        raise ValueError("targets_and_splits.csv contains duplicated dates.")

    keep_f = ["date", "forecast_time", "I_r"] + ABC_FEATURES
    keep_t = ["date", "y_vol_5", "label_end_5", "y_vol_20", "label_end_20"]
    df = features[keep_f].merge(targets[keep_t], on="date", how="left", validate="one_to_one")
    df = df.sort_values("date").reset_index(drop=True)

    for h in [5, 20]:
        y = pd.to_numeric(df[f"y_vol_{h}"], errors="coerce")
        end = pd.to_datetime(df[f"label_end_{h}"], errors="coerce")
        common_features_complete = df[ABC_FEATURES].notna().all(axis=1)
        eligible = common_features_complete & y.notna() & (y > 0) & end.notna()
        df[f"eligible_continuous_{h}"] = eligible
        df[f"log_y_vol_{h}"] = np.where(eligible, np.log(y), np.nan)
        df[f"pre2023_mature_{h}"] = eligible & (df["date"] < OOS_START) & (end < OOS_START)
        df[f"oos_{h}"] = eligible & (df["date"] >= OOS_START)

    return df


def validate_expected_counts(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    rows = []
    all_pass = True
    for h in [5, 20]:
        elig = df[f"eligible_continuous_{h}"]
        pre = df[f"pre2023_mature_{h}"]
        oos = df[f"oos_{h}"]
        dates = df.loc[elig, "date"]
        by_year = df.loc[oos].groupby(df.loc[oos, "date"].dt.year).size().to_dict()
        actual = {
            "eligible": int(elig.sum()),
            "first": dates.min().strftime("%Y-%m-%d") if len(dates) else None,
            "last": dates.max().strftime("%Y-%m-%d") if len(dates) else None,
            "pre2023_mature": int(pre.sum()),
            "oos": int(oos.sum()),
            "oos_by_year": {int(k): int(v) for k, v in by_year.items()},
        }
        expected = EXPECTED[h]
        status = actual == expected
        all_pass &= status
        rows.append(
            {
                "horizon": h,
                "eligible": actual["eligible"],
                "expected_eligible": expected["eligible"],
                "first_date": actual["first"],
                "expected_first_date": expected["first"],
                "last_date": actual["last"],
                "expected_last_date": expected["last"],
                "pre2023_mature": actual["pre2023_mature"],
                "expected_pre2023_mature": expected["pre2023_mature"],
                "oos": actual["oos"],
                "expected_oos": expected["oos"],
                "oos_by_year": json.dumps(actual["oos_by_year"], ensure_ascii=False, sort_keys=True),
                "expected_oos_by_year": json.dumps(expected["oos_by_year"], ensure_ascii=False, sort_keys=True),
                "status": "PASS" if status else "FAIL",
            }
        )
    return pd.DataFrame(rows), all_pass


def safe_write_parquet(df: pd.DataFrame, path: Path) -> bool:
    try:
        df.to_parquet(path, index=False)
        return True
    except Exception as exc:
        print(f"[WARN] Could not write parquet {path.name}: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to data.zip or extracted data directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument(
        "--strict-counts",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail if the frozen dataset does not reproduce the agreed V1.0 sample counts.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_dir}\n"
            "Use a new directory name so an earlier research artifact is never overwritten."
        )

    output_dir.mkdir(parents=True)
    (output_dir / "inputs").mkdir()
    (output_dir / "processed").mkdir()
    (output_dir / "audit").mkdir()
    (output_dir / "config").mkdir()

    with tempfile.TemporaryDirectory(prefix="continuous_v1_") as td:
        data_root = locate_data_root(input_path, Path(td))
        features_path = data_root / "frozen" / "features_asof.csv"
        targets_path = data_root / "frozen" / "targets_and_splits.csv"

        # Copy frozen sources, but never modify them.
        shutil.copy2(features_path, output_dir / "inputs" / "features_asof.csv")
        shutil.copy2(targets_path, output_dir / "inputs" / "targets_and_splits.csv")

        input_hashes = {
            "features_asof.csv": sha256_file(features_path),
            "targets_and_splits.csv": sha256_file(targets_path),
        }
        (output_dir / "config" / "input_sha256.json").write_text(
            json.dumps(input_hashes, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        features = pd.read_csv(features_path)
        targets = pd.read_csv(targets_path)

        features["date"] = pd.to_datetime(features["date"], errors="raise")
        features["forecast_time"] = pd.to_datetime(features["forecast_time"], errors="raise")
        targets["date"] = pd.to_datetime(targets["date"], errors="raise")
        for h in [5, 20]:
            targets[f"label_end_{h}"] = pd.to_datetime(targets[f"label_end_{h}"], errors="coerce")

        # Basic date audit.
        date_audit = {
            "feature_rows": int(len(features)),
            "target_rows": int(len(targets)),
            "feature_date_unique": bool(not features["date"].duplicated().any()),
            "target_date_unique": bool(not targets["date"].duplicated().any()),
            "feature_dates_monotone": bool(features["date"].is_monotonic_increasing),
            "target_dates_monotone": bool(targets["date"].is_monotonic_increasing),
            "feature_start": features["date"].min().strftime("%Y-%m-%d"),
            "feature_end": features["date"].max().strftime("%Y-%m-%d"),
        }
        (output_dir / "audit" / "date_audit.json").write_text(
            json.dumps(date_audit, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Macro release-time audit.
        release_audit = release_time_audit(features)
        release_audit.to_csv(output_dir / "audit" / "release_time_audit.csv", index=False)
        if (release_audit["status"] != "PASS").any():
            raise RuntimeError("Release-time audit failed. See audit/release_time_audit.csv")

        # Merge and independently verify targets from I_r.
        verify_merge = features[["date", "I_r"]].merge(
            targets[["date", "y_vol_5", "y_vol_20"]], on="date", how="left", validate="one_to_one"
        )
        target_check = verify_targets(verify_merge)
        target_check.to_csv(output_dir / "audit" / "target_verification.csv", index=False)
        if not target_check["allclose_pass"].all():
            raise RuntimeError("Target verification failed. See audit/target_verification.csv")

        # Build continuous forecasting dataset.
        df = build_dataset(features, targets)

        # Sample count validation.
        count_check, count_pass = validate_expected_counts(df)
        count_check.to_csv(output_dir / "audit" / "sample_counts.csv", index=False)
        if args.strict_counts and not count_pass:
            raise RuntimeError(
                "Sample counts differ from the frozen V1.0 protocol. "
                "See audit/sample_counts.csv. Use --no-strict-counts only for a deliberately new data version."
            )

        # Feature availability report for the selected 29 columns.
        avail_rows = []
        for group_name, cols in [
            ("A", A_FEATURES),
            ("B_add", B_ADD_FEATURES),
            ("C_add", C_ADD_FEATURES),
            ("ABC_all", ABC_FEATURES),
        ]:
            for col in cols:
                avail_rows.append(
                    {
                        "group": group_name,
                        "feature": col,
                        "n_nonmissing": int(df[col].notna().sum()),
                        "n_missing": int(df[col].isna().sum()),
                        "missing_rate": float(df[col].isna().mean()),
                    }
                )
        pd.DataFrame(avail_rows).to_csv(
            output_dir / "audit" / "selected_feature_availability.csv", index=False
        )

        # Protocol / feature configuration.
        feature_groups = {
            "A": A_FEATURES,
            "B_add": B_ADD_FEATURES,
            "AB": AB_FEATURES,
            "C_add": C_ADD_FEATURES,
            "ABC": ABC_FEATURES,
        }
        (output_dir / "config" / "feature_groups_v1.json").write_text(
            json.dumps(feature_groups, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        protocol = {
            "protocol_version": PROTOCOL_VERSION,
            "oos_start": OOS_START.strftime("%Y-%m-%d"),
            "annualization": ANNUALIZATION,
            "target": {
                "horizons": [5, 20],
                "raw_target_columns": ["y_vol_5", "y_vol_20"],
                "fit_target": "log(y_vol_h)",
                "definition": "sqrt(252/h * sum_{i=1..h}(r_{t+i}^2))",
            },
            "sample_rule": "Common complete ABC sample; no imputation; y_vol_h > 0; label_end_h present.",
            "macro_alignment": "Use values already aligned as-of forecast_time; no new fill performed here.",
            "forbidden_for_main_experiment": [
                "split_5",
                "split_20",
                "risk_threshold_5",
                "risk_threshold_20",
                "y_high_vol_5",
                "y_high_vol_20",
                "10-day features",
                "global standardization",
                "imputation",
                "PCA",
                "Granger-based post-hoc feature screening",
            ],
            "notes": [
                "cumret variables are cumulative SIMPLE returns computed as exp(sum(log returns))-1, not cumulative log returns.",
                "Macro variables are release-time aligned, but historical revision-vintage contamination cannot be fully ruled out from the supplied source.",
            ],
        }
        (output_dir / "config" / "protocol_v1.json").write_text(
            json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Full audit/eligibility table.
        eligibility_cols = [
            "date",
            "forecast_time",
            "y_vol_5",
            "log_y_vol_5",
            "label_end_5",
            "eligible_continuous_5",
            "pre2023_mature_5",
            "oos_5",
            "y_vol_20",
            "log_y_vol_20",
            "label_end_20",
            "eligible_continuous_20",
            "pre2023_mature_20",
            "oos_20",
        ]
        eligibility = df[eligibility_cols].copy()
        eligibility.to_csv(output_dir / "processed" / "sample_eligibility.csv", index=False)
        safe_write_parquet(eligibility, output_dir / "processed" / "sample_eligibility.parquet")

        # Directly usable modelling datasets, one per horizon.
        for h in [5, 20]:
            cols = ["date", "forecast_time"] + ABC_FEATURES + [
                f"y_vol_{h}",
                f"log_y_vol_{h}",
                f"label_end_{h}",
                f"pre2023_mature_{h}",
                f"oos_{h}",
            ]
            model_h = df.loc[df[f"eligible_continuous_{h}"], cols].copy()
            model_h.to_csv(output_dir / "processed" / f"model_dataset_h{h}_v1.csv", index=False)
            safe_write_parquet(model_h, output_dir / "processed" / f"model_dataset_h{h}_v1.parquet")

        # One combined master table if preferred by downstream code.
        master_cols = ["date", "forecast_time"] + ABC_FEATURES + [
            "y_vol_5", "log_y_vol_5", "label_end_5", "eligible_continuous_5", "pre2023_mature_5", "oos_5",
            "y_vol_20", "log_y_vol_20", "label_end_20", "eligible_continuous_20", "pre2023_mature_20", "oos_20",
        ]
        master = df[master_cols].copy()
        master.to_csv(output_dir / "processed" / "continuous_model_dataset_master_v1.csv", index=False)
        safe_write_parquet(master, output_dir / "processed" / "continuous_model_dataset_master_v1.parquet")

        metadata = {
            "protocol_version": PROTOCOL_VERSION,
            "input_sha256": input_hashes,
            "feature_counts": {"A": len(A_FEATURES), "AB": len(AB_FEATURES), "ABC": len(ABC_FEATURES)},
            "feature_groups": feature_groups,
            "cumret_definition": "exp(sum(log_returns over trailing window)) - 1",
            "volatility_feature_definition": "sqrt(252 * mean(daily_log_return^2 over trailing window))",
            "future_volatility_target_definition": "sqrt(252/h * sum(next h daily_log_returns^2))",
            "no_imputation": True,
            "target_verification_pass": bool(target_check["allclose_pass"].all()),
            "release_time_audit_pass": bool((release_audit["status"] == "PASS").all()),
            "sample_count_audit_pass": bool(count_pass),
            "sample_counts": count_check.to_dict(orient="records"),
            "important_limitations": [
                "Historical revision vintages are not supplied, so final-vintage contamination cannot be independently ruled out.",
                "This V1.0 main dataset intentionally excludes sparse additional macro/industry variables from the main ABC group.",
                "Old classification split/risk-label fields are not used in the continuous-volatility experiment.",
            ],
        }
        (output_dir / "processed" / "model_dataset_metadata_v1.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        readme = "Continuous Forecast Dataset V1.0\n\n"
        readme += "Main files for modelling:\n"
        readme += "  processed/model_dataset_h5_v1.parquet (or .csv)\n"
        readme += "  processed/model_dataset_h20_v1.parquet (or .csv)\n"
        readme += "  config/feature_groups_v1.json\n\n"
        readme += "Do not use old split_5/split_20, risk thresholds, or high-volatility labels for this experiment.\n"
        readme += "A/AB/ABC comparisons must use the same horizon-specific dataset rows.\n"
        readme += "Ridge scaling must be fitted inside each training fold/month, never globally here.\n"
        readme += "Expected h=5 rows: 1716; expected h=20 rows: 1700.\n"
        (output_dir / "README.txt").write_text(readme, encoding="utf-8")

        # Reproducibility receipt: hashes of key outputs.
        key_outputs = [
            output_dir / "processed" / "model_dataset_h5_v1.csv",
            output_dir / "processed" / "model_dataset_h20_v1.csv",
            output_dir / "config" / "feature_groups_v1.json",
            output_dir / "config" / "protocol_v1.json",
            output_dir / "audit" / "target_verification.csv",
            output_dir / "audit" / "sample_counts.csv",
        ]
        receipt = {str(p.relative_to(output_dir)): sha256_file(p) for p in key_outputs}
        (output_dir / "config" / "reproduction_receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print("\n=== Continuous Forecast V1.0 dataset prepared successfully ===")
        print(f"Output: {output_dir}")
        print("Features: A=6, AB=24, ABC=29")
        for h in [5, 20]:
            row = count_check.loc[count_check["horizon"] == h].iloc[0]
            print(
                f"h={h}: eligible={int(row['eligible'])}, "
                f"pre2023_mature={int(row['pre2023_mature'])}, oos={int(row['oos'])}, "
                f"status={row['status']}"
            )
        print("Target verification: PASS")
        print("Release-time audit: PASS")


if __name__ == "__main__":
    main()
