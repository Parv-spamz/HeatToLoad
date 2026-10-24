"""
Feature Engineering Pipeline (Phase 5).
Constructs domain-specific meteorological, temporal, and lag features:
- Cooling Degree Days (CDD_18, CDD_24) & Heating Degree Days (HDD_18)
- NOAA Heat Index approximation combining temperature and relative humidity
- Multi-day thermal inertia: Lags (1d, 2d, 3d) and Rolling Means (3d, 7d)
- Calendar dynamics: Day of week, weekend, month, cyclical harmonics, gazetted holidays
- Linear trend capturing structural electrification/economic growth
- IMD-consistent Heatwave indicator against 95th percentile baseline
- Target lags (1d, 7d) for day-ahead forecasting benchmarks
"""

import json
import pathlib
import sqlite3

import numpy as np
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

DB_PATH = ROOT / cfg["paths"]["database_path"]
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_CSV_PATH = PROCESSED_DIR / "features.csv"


def calculate_heat_index(temp_c, rh):
    """
    NOAA Steadman / Rothfusz heat index formula adapted for Celsius.
    """
    if pd.isna(temp_c) or pd.isna(rh):
        return None
    # Convert C to F
    T = temp_c * 9.0 / 5.0 + 32.0
    R = rh
    if T < 80.0:
        HI_f = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (R * 0.094))
    else:
        HI_f = (
            -42.379
            + 2.04901523 * T
            + 10.14333127 * R
            - 0.22475541 * T * R
            - 0.00683783 * T * T
            - 0.05481717 * R * R
            + 0.00122874 * T * T * R
            + 0.00085282 * T * R * R
            - 0.00000199 * T * T * R * R
        )
    # Convert back to C
    HI_c = (HI_f - 32.0) * 5.0 / 9.0
    return HI_c


def compute_features():
    print("=" * 70)
    print("Starting Phase 5 Feature Engineering Pipeline")
    print(f"Reading from database: {DB_PATH}")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run 'make load' first.")

    conn = sqlite3.connect(DB_PATH)
    try:
        query = """
        SELECT * FROM fact_daily_load_weather
        ORDER BY state, date ASC;
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    print(f"Loaded {len(df)} analytical records from fact_daily_load_weather.")

    df["date_dt"] = pd.to_datetime(df["date"])
    df["day_of_year"] = df["date_dt"].dt.day_of_year

    # 1. Thermal & Meteorological Features
    print("\nComputing meteorological non-linearities and heat metrics...")
    df["cdd_18"] = (df["temperature_2m_mean"] - 18.0).clip(lower=0.0)
    df["cdd_24"] = (df["temperature_2m_mean"] - 24.0).clip(lower=0.0)
    df["hdd_18"] = (18.0 - df["temperature_2m_mean"]).clip(lower=0.0)

    df["temp_max_sq"] = df["temperature_2m_max"] ** 2
    df["temp_max_cube"] = df["temperature_2m_max"] ** 3

    # Heat Index
    df["heat_index"] = [
        calculate_heat_index(t, rh) for t, rh in zip(df["temperature_2m_max"], df["relative_humidity_2m_mean"])
    ]

    # 2. State-wise Thermal Inertia & Rolling Dynamics
    print("Computing state-wise lags and multi-day rolling temperature averages...")
    state_dfs = []

    # Reference period for monthly 95th percentile heatwave baseline
    ref_start = cfg["modeling"]["heatwave_reference_start"]
    ref_end = cfg["modeling"]["heatwave_reference_end"]
    df_ref = df[(df["date"] >= ref_start) & (df["date"] <= ref_end)]

    monthly_p95_by_state = {}
    for (state, mo), grp in df_ref.groupby(["state", "month"]):
        valid_t = grp["temperature_2m_max"].dropna()
        p95 = np.percentile(valid_t, 95) if len(valid_t) > 0 else 40.0
        monthly_p95_by_state[(state, mo)] = p95

    # Base date for structural linear trend
    base_date = pd.to_datetime("2023-04-01")
    df["trend_day"] = (df["date_dt"] - base_date).dt.days

    for state, grp in df.groupby("state"):
        g = grp.sort_values("date").copy()

        # Temperature lags
        g["temp_max_lag1"] = g["temperature_2m_max"].shift(1)
        g["temp_max_lag2"] = g["temperature_2m_max"].shift(2)
        g["temp_max_lag3"] = g["temperature_2m_max"].shift(3)

        # Rolling temperature metrics
        g["temp_max_roll3"] = g["temperature_2m_max"].rolling(window=3, min_periods=1).mean()
        g["temp_max_roll7"] = g["temperature_2m_max"].rolling(window=7, min_periods=1).mean()

        # Demand lags for autoregressive benchmark
        g["demand_lag1"] = g["max_demand_met_mw"].shift(1)
        g["demand_lag7"] = g["max_demand_met_mw"].shift(7)
        g["demand_roll7_mean"] = g["max_demand_met_mw"].shift(1).rolling(window=7, min_periods=1).mean()

        # Heatwave flag
        hw_flags = []
        for _, row in g.iterrows():
            mo = row["month"]
            thresh = monthly_p95_by_state.get((state, mo), 42.0)
            t_max = row["temperature_2m_max"]
            hw_flags.append(1 if (not pd.isna(t_max) and t_max >= thresh) else 0)
        g["is_heatwave"] = hw_flags

        state_dfs.append(g)

    df_featured = pd.concat(state_dfs, ignore_index=True)

    # 3. Calendar & Cyclical Features
    print("Computing calendar cyclical harmonics (sin/cos encoding)...")
    # Day of year cyclical
    df_featured["sin_doy"] = np.sin(2 * np.pi * df_featured["day_of_year"] / 365.25)
    df_featured["cos_doy"] = np.cos(2 * np.pi * df_featured["day_of_year"] / 365.25)

    # Day of week cyclical
    df_featured["sin_dow"] = np.sin(2 * np.pi * df_featured["day_of_week"] / 7.0)
    df_featured["cos_dow"] = np.cos(2 * np.pi * df_featured["day_of_week"] / 7.0)

    # Month cyclical
    df_featured["sin_month"] = np.sin(2 * np.pi * df_featured["month"] / 12.0)
    df_featured["cos_month"] = np.cos(2 * np.pi * df_featured["month"] / 12.0)

    # 4. Train/Holdout Partition Labeling
    holdout_start = cfg["modeling"]["holdout_start"]
    holdout_end = cfg["modeling"]["holdout_end"]
    df_featured["is_holdout"] = ((df_featured["date"] >= holdout_start) & (df_featured["date"] <= holdout_end)).astype(
        int
    )

    # Drop temporary datetime object
    df_featured = df_featured.drop(columns=["date_dt"])

    # Save to features.csv
    df_featured.to_csv(FEATURES_CSV_PATH, index=False)
    print(
        f"\nSaved feature dataset with {len(df_featured)} records and {len(df_featured.columns)} columns to {FEATURES_CSV_PATH}"
    )

    # Log feature metadata
    feature_meta = {
        "record_count": len(df_featured),
        "column_count": len(df_featured.columns),
        "columns": list(df_featured.columns),
        "holdout_count": int(df_featured["is_holdout"].sum()),
        "train_count": int((1 - df_featured["is_holdout"]).sum()),
        "heatwave_days_count": int(df_featured["is_heatwave"].sum()),
        "heatwave_reference_period": f"{ref_start} to {ref_end}",
        "holdout_period": f"{holdout_start} to {holdout_end}",
    }
    (LOGS_DIR / "feature_metadata.json").write_text(json.dumps(feature_meta, indent=2), encoding="utf-8")
    print("Saved feature metadata to logs/feature_metadata.json")
    print("\nPhase 5 Feature Engineering Complete!")


if __name__ == "__main__":
    compute_features()
