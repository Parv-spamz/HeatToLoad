"""
Data Cleaning and Quality Flagging Pipeline.
Strictly implements Section 1 Integrity Contract and DEC-009 / DEC-010 / DEC-011 / DEC-012:
- Physical bounds validation per state.
- Target demand is NEVER imputed (retains NULL, zero synthetic demand).
- Weather gap linear interpolation <= 2 days explicitly flagged as 'weather_interpolated'.
- Quality flag hierarchy: 'ok', 'weather_interpolated', 'outlier_review', 'excluded'.
- Deduplication of (state, date) retaining the most complete record.
- Full provenance and audit trail written to logs/.
"""

import json
import pathlib

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

INTERIM_DIR = ROOT / "data" / "interim"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

RAW_DEMAND_PATH = ROOT / "data" / "raw" / "demand" / "raw_demand_records.csv"
RAW_WEATHER_PATH = ROOT / "data" / "raw" / "weather" / "raw_weather_records.csv"
OUTPUT_CLEANED_PATH = INTERIM_DIR / "cleaned_records.csv"

STATES_CFG = cfg["states"]
TARGET_STATES = list(STATES_CFG.keys())

ANALYSIS_START = "2023-04-01"
ANALYSIS_END = "2025-03-31"


def clean_data():
    print("=" * 70)
    print("Starting Phase 3 Data Cleaning & Quality Validation")
    print(f"Analysis Period: {ANALYSIS_START} to {ANALYSIS_END}")
    print(f"Target States ({len(TARGET_STATES)}): {', '.join(TARGET_STATES)}")
    print("=" * 70)

    if not RAW_DEMAND_PATH.exists():
        raise FileNotFoundError(f"Raw demand records not found at {RAW_DEMAND_PATH}. Run 'make ingest' first.")
    if not RAW_WEATHER_PATH.exists():
        raise FileNotFoundError(f"Raw weather records not found at {RAW_WEATHER_PATH}. Run 'make ingest' first.")

    # 1. Load Raw Datasets
    print("\nLoading raw demand and weather datasets...")
    df_demand = pd.read_csv(RAW_DEMAND_PATH)
    df_weather = pd.read_csv(RAW_WEATHER_PATH)

    print(f"  Raw Demand Rows: {len(df_demand)}")
    print(f"  Raw Weather Rows: {len(df_weather)}")

    # Standardize column types & formats
    df_demand["date"] = pd.to_datetime(df_demand["date"]).dt.strftime("%Y-%m-%d")
    df_weather["date"] = pd.to_datetime(df_weather["date"]).dt.strftime("%Y-%m-%d")

    # Filter to analysis window and target states
    df_demand = df_demand[df_demand["state"].isin(TARGET_STATES)].copy()
    df_weather = df_weather[df_weather["state"].isin(TARGET_STATES)].copy()

    # Deduplicate demand records on (date, state)
    print("\nDeduplicating demand records...")
    initial_demand_count = len(df_demand)
    # Score completeness: non-null count across key fields
    df_demand["_completeness"] = (
        df_demand["max_demand_met_mw"].notna().astype(int) * 3
        + df_demand["energy_met_mu"].notna().astype(int) * 2
        + df_demand["shortage_mw"].notna().astype(int)
    )
    df_demand = df_demand.sort_values(["date", "state", "_completeness"], ascending=[True, True, False])
    df_demand = df_demand.drop_duplicates(subset=["date", "state"], keep="first").drop(columns=["_completeness"])
    dedup_demand_dropped = initial_demand_count - len(df_demand)
    print(f"  Deduplicated demand: removed {dedup_demand_dropped} redundant/duplicate state-day records.")

    # Deduplicate weather records on (date, state)
    initial_weather_count = len(df_weather)
    df_weather = df_weather.sort_values(["date", "state"]).drop_duplicates(subset=["date", "state"], keep="last")
    dedup_weather_dropped = initial_weather_count - len(df_weather)
    print(f"  Deduplicated weather: removed {dedup_weather_dropped} redundant records.")

    # 2. Weather Pre-processing & Limited Interpolation (<= 2 days)
    print("\nProcessing weather continuity and gap inspection...")
    weather_interpolated_records = []
    weather_processed_dfs = []

    for state, group in df_weather.groupby("state"):
        g = group.sort_values("date").copy()
        g = g.set_index(pd.to_datetime(g["date"]))
        # Reindex to full expected date grid
        full_date_range = pd.date_range(start=ANALYSIS_START, end=ANALYSIS_END, freq="D")
        g_reindexed = g.reindex(full_date_range)
        g_reindexed["state"] = state
        g_reindexed["date"] = g_reindexed.index.strftime("%Y-%m-%d")

        weather_cols = [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "apparent_temperature_max",
            "relative_humidity_2m_mean",
            "precipitation_sum",
        ]

        g_reindexed["_weather_interpolated"] = False
        for col in weather_cols:
            if col in g_reindexed.columns:
                null_mask = g_reindexed[col].isna()
                # Interpolate up to 2 consecutive missing days
                interpolated = g_reindexed[col].interpolate(method="linear", limit=2, limit_direction="both")
                filled_mask = null_mask & interpolated.notna()
                if filled_mask.any():
                    g_reindexed.loc[filled_mask, "_weather_interpolated"] = True
                    for dt_idx in g_reindexed[filled_mask]["date"]:
                        weather_interpolated_records.append({"state": state, "date": dt_idx, "variable": col})
                g_reindexed[col] = interpolated

        weather_processed_dfs.append(g_reindexed.reset_index(drop=True))

    df_weather_clean = pd.concat(weather_processed_dfs, ignore_index=True)
    print(f"  Weather interpolated instances (gap <= 2 days): {len(weather_interpolated_records)}")

    # 3. Outer Merge Demand and Weather on (date, state)
    print("\nMerging demand and weather on (date, state)...")
    merged = pd.merge(df_demand, df_weather_clean, on=["date", "state"], how="outer", suffixes=("_demand", "_weather"))

    # Filter strictly to the analysis date window
    merged = merged[(merged["date"] >= ANALYSIS_START) & (merged["date"] <= ANALYSIS_END)].copy()
    merged = merged.sort_values(["state", "date"]).reset_index(drop=True)

    # 4. Physical Plausibility and Quality Flag Assignment
    print("\nApplying physical bounds validation and quality flag hierarchy...")
    quality_flags = []
    flag_reasons = []

    # Calculate day-over-day changes per state for outlier detection
    merged["prev_demand_mw"] = merged.groupby("state")["max_demand_met_mw"].shift(1)
    merged["prev_temp_max"] = merged.groupby("state")["temperature_2m_max"].shift(1)
    merged["demand_dod_pct"] = (merged["max_demand_met_mw"] - merged["prev_demand_mw"]).abs() / merged["prev_demand_mw"]
    merged["temp_dod_abs"] = (merged["temperature_2m_max"] - merged["prev_temp_max"]).abs()

    for idx, row in merged.iterrows():
        state = row["state"]
        demand = row["max_demand_met_mw"]
        bounds = STATES_CFG[state]["demand_bounds_mw"]
        reasons = []

        # Check demand existence and bounds
        if pd.isna(demand):
            flag = "excluded"
            reasons.append("missing_demand")
        elif demand < 100:  # Unit corruption (<100 MW impossible for any state)
            flag = "excluded"
            reasons.append(f"corrupt_unit_value_{demand}")
        elif demand < bounds[0] or demand > bounds[1]:
            flag = "excluded"
            reasons.append(f"outside_bounds_[{bounds[0]},{bounds[1]}]_val_{demand}")
        elif row["demand_dod_pct"] > 0.35 and row["temp_dod_abs"] < 2.0:
            # Significant day-over-day jump/drop >35% without temperature change
            flag = "outlier_review"
            reasons.append(f"sudden_swing_{row['demand_dod_pct']*100:.1f}pct_with_dt_{row['temp_dod_abs']:.1f}C")
        elif row.get("_weather_interpolated", False):
            flag = "weather_interpolated"
            reasons.append("weather_gap_interpolated")
        else:
            flag = "ok"

        quality_flags.append(flag)
        flag_reasons.append("; ".join(reasons) if reasons else "passed_all_checks")

    merged["quality_flag"] = quality_flags
    merged["flag_reasons"] = flag_reasons

    # Drop intermediate helper columns
    cols_to_drop = ["prev_demand_mw", "prev_temp_max", "demand_dod_pct", "temp_dod_abs", "_weather_interpolated"]
    merged = merged.drop(columns=[c for c in cols_to_drop if c in merged.columns])

    # 5. Output Summary & Integrity Audit
    flag_dist = merged["quality_flag"].value_counts().to_dict()
    print("\nQuality Flag Distribution across state-days:")
    for k, v in flag_dist.items():
        pct = (v / len(merged)) * 100
        print(f"  - {k}: {v} ({pct:.2f}%)")

    # Save cleaned interim dataset
    merged.to_csv(OUTPUT_CLEANED_PATH, index=False)
    print(f"\nSaved cleaned interim dataset with {len(merged)} records to {OUTPUT_CLEANED_PATH}")

    # Save audit logs
    summary_report = {
        "analysis_start": ANALYSIS_START,
        "analysis_end": ANALYSIS_END,
        "total_state_day_records": len(merged),
        "target_states_count": len(TARGET_STATES),
        "flag_distribution": flag_dist,
        "dedup_demand_records_removed": dedup_demand_dropped,
        "dedup_weather_records_removed": dedup_weather_dropped,
        "weather_interpolated_records_count": len(weather_interpolated_records),
        "excluded_count": flag_dist.get("excluded", 0),
        "usable_modeling_records": flag_dist.get("ok", 0)
        + flag_dist.get("weather_interpolated", 0)
        + flag_dist.get("outlier_review", 0),
    }

    summary_json_path = LOGS_DIR / "cleaning_summary.json"
    summary_json_path.write_text(json.dumps(summary_report, indent=2), encoding="utf-8")
    print(f"Saved cleaning summary log to {summary_json_path}")

    # Save flagged records audit table
    flagged_df = merged[merged["quality_flag"] != "ok"][
        ["date", "state", "max_demand_met_mw", "temperature_2m_max", "quality_flag", "flag_reasons"]
    ]
    flagged_csv_path = LOGS_DIR / "flagged_records_audit.csv"
    flagged_df.to_csv(flagged_csv_path, index=False)
    print(f"Saved {len(flagged_df)} flagged audit records to {flagged_csv_path}")

    print("\nPhase 3 Cleaning & Validation Complete!")


if __name__ == "__main__":
    clean_data()
