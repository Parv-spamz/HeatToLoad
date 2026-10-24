"""
SQLite Database Loader (Phase 4).
Loads cleaned and validated data into a relational star-schema database at:
data/processed/heat_to_load.db

Tables:
- dim_state: Geographic, regional, and capacity bounds metadata.
- dim_date: Calendar, weekend, seasonal, and gazetted holiday flags.
- fact_demand: Primary electricity demand records with quality flags and provenance.
- fact_weather: ERA5 gridded reanalysis continuous weather features.
- fact_daily_load_weather: Denormalized analytical reporting table.
"""

import json
import pathlib
import sqlite3

import holidays
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = ROOT / cfg["paths"]["database_path"]
CLEANED_CSV_PATH = ROOT / "data" / "interim" / "cleaned_records.csv"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

STATES_CFG = cfg["states"]


def init_schema(conn):
    cursor = conn.cursor()
    cursor.executescript("""
    PRAGMA foreign_keys = ON;

    DROP TABLE IF EXISTS fact_daily_load_weather;
    DROP TABLE IF EXISTS fact_demand;
    DROP TABLE IF EXISTS fact_weather;
    DROP TABLE IF EXISTS dim_date;
    DROP TABLE IF EXISTS dim_state;

    CREATE TABLE dim_state (
        state_id INTEGER PRIMARY KEY AUTOINCREMENT,
        state_name TEXT UNIQUE NOT NULL,
        state_code TEXT NOT NULL,
        region TEXT NOT NULL,
        capital_city TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        coord_source TEXT NOT NULL,
        demand_bound_min_mw REAL NOT NULL,
        demand_bound_max_mw REAL NOT NULL
    );

    CREATE TABLE dim_date (
        date TEXT PRIMARY KEY,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL, -- 0=Monday, 6=Sunday
        day_name TEXT NOT NULL,
        is_weekend INTEGER NOT NULL,  -- 1 if Saturday or Sunday
        season TEXT NOT NULL,         -- Summer, Monsoon, Post-Monsoon, Winter
        is_holiday INTEGER NOT NULL,  -- 1 if gazetted public holiday
        holiday_name TEXT
    );

    CREATE TABLE fact_demand (
        demand_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL REFERENCES dim_date(date),
        state TEXT NOT NULL REFERENCES dim_state(state_name),
        max_demand_met_mw REAL,
        shortage_mw REAL,
        unrestricted_peak_mw REAL,
        energy_met_mu REAL,
        quality_flag TEXT NOT NULL,
        flag_reasons TEXT,
        source_file TEXT,
        page_number INTEGER,
        retrieved_at_utc TEXT
    );

    CREATE TABLE fact_weather (
        weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL REFERENCES dim_date(date),
        state TEXT NOT NULL REFERENCES dim_state(state_name),
        temperature_2m_max REAL,
        temperature_2m_min REAL,
        temperature_2m_mean REAL,
        apparent_temperature_max REAL,
        relative_humidity_2m_mean REAL,
        precipitation_sum REAL,
        api_request_id TEXT,
        retrieved_at_utc TEXT
    );

    CREATE INDEX idx_demand_state_date ON fact_demand(state, date);
    CREATE INDEX idx_weather_state_date ON fact_weather(state, date);
    CREATE INDEX idx_demand_quality ON fact_demand(quality_flag);
    """)
    conn.commit()


def populate_dim_state(conn):
    cursor = conn.cursor()
    rows = []
    for s_name, s_info in STATES_CFG.items():
        rows.append(
            (
                s_name,
                s_info["code"],
                s_info["region"],
                s_info["city"],
                s_info["lat"],
                s_info["lon"],
                s_info["coord_source"],
                s_info["demand_bounds_mw"][0],
                s_info["demand_bounds_mw"][1],
            )
        )
    cursor.executemany(
        """
    INSERT INTO dim_state (
        state_name, state_code, region, capital_city, latitude, longitude,
        coord_source, demand_bound_min_mw, demand_bound_max_mw
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        rows,
    )
    conn.commit()
    print(f"Populated dim_state with {len(rows)} state metadata records.")


def populate_dim_date(conn, start_date="2023-01-01", end_date="2025-04-30"):
    cursor = conn.cursor()
    india_holidays = holidays.India(years=[2023, 2024, 2025])
    dates = pd.date_range(start_date, end_date, freq="D")
    rows = []
    for dt in dates:
        dt_str = dt.strftime("%Y-%m-%d")
        dt_obj = dt.date()
        is_hol = 1 if dt_obj in india_holidays else 0
        hol_name = india_holidays.get(dt_obj, None)

        # Indian seasonal classification (IMD standard)
        mo = dt.month
        if mo in [3, 4, 5, 6]:
            season = "Summer"
        elif mo in [7, 8, 9]:
            season = "Monsoon"
        elif mo in [10, 11]:
            season = "Post-Monsoon"
        else:
            season = "Winter"

        rows.append(
            (
                dt_str,
                dt.year,
                dt.month,
                dt.day,
                dt.day_of_week,
                dt.strftime("%A"),
                1 if dt.day_of_week in [5, 6] else 0,
                season,
                is_hol,
                hol_name,
            )
        )
    cursor.executemany(
        """
    INSERT INTO dim_date (
        date, year, month, day, day_of_week, day_name, is_weekend, season, is_holiday, holiday_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        rows,
    )
    conn.commit()
    print(f"Populated dim_date with {len(rows)} calendar date records.")


def load_database():
    print("=" * 70)
    print("Starting Phase 4 SQLite Database Ingestion")
    print(f"Database Path: {DB_PATH}")
    print("=" * 70)

    if not CLEANED_CSV_PATH.exists():
        raise FileNotFoundError(f"Cleaned records not found at {CLEANED_CSV_PATH}. Run 'make clean' first.")

    df = pd.read_csv(CLEANED_CSV_PATH)
    print(f"Loaded {len(df)} cleaned records for database ingestion.")

    conn = sqlite3.connect(DB_PATH)
    try:
        init_schema(conn)
        populate_dim_state(conn)
        populate_dim_date(conn)

        cursor = conn.cursor()

        # Populate fact_demand
        demand_rows = []
        for _, r in df.iterrows():
            demand_rows.append(
                (
                    r["date"],
                    r["state"],
                    None if pd.isna(r.get("max_demand_met_mw")) else float(r["max_demand_met_mw"]),
                    None if pd.isna(r.get("shortage_mw")) else float(r["shortage_mw"]),
                    None if pd.isna(r.get("unrestricted_peak_mw")) else float(r["unrestricted_peak_mw"]),
                    None if pd.isna(r.get("energy_met_mu")) else float(r["energy_met_mu"]),
                    r.get("quality_flag", "ok"),
                    r.get("flag_reasons", "none"),
                    r.get("source_file_demand", r.get("source_file")),
                    None if pd.isna(r.get("page_number")) else int(r["page_number"]),
                    r.get("retrieved_at_utc_demand", r.get("retrieved_at_utc")),
                )
            )

        cursor.executemany(
            """
        INSERT INTO fact_demand (
            date, state, max_demand_met_mw, shortage_mw, unrestricted_peak_mw,
            energy_met_mu, quality_flag, flag_reasons, source_file, page_number, retrieved_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            demand_rows,
        )
        print(f"Inserted {len(demand_rows)} records into fact_demand.")

        # Populate fact_weather
        weather_rows = []
        for _, r in df.iterrows():
            weather_rows.append(
                (
                    r["date"],
                    r["state"],
                    None if pd.isna(r.get("temperature_2m_max")) else float(r["temperature_2m_max"]),
                    None if pd.isna(r.get("temperature_2m_min")) else float(r["temperature_2m_min"]),
                    None if pd.isna(r.get("temperature_2m_mean")) else float(r["temperature_2m_mean"]),
                    None if pd.isna(r.get("apparent_temperature_max")) else float(r["apparent_temperature_max"]),
                    None if pd.isna(r.get("relative_humidity_2m_mean")) else float(r["relative_humidity_2m_mean"]),
                    None if pd.isna(r.get("precipitation_sum")) else float(r["precipitation_sum"]),
                    r.get("api_request_id"),
                    r.get("retrieved_at_utc_weather"),
                )
            )

        cursor.executemany(
            """
        INSERT INTO fact_weather (
            date, state, temperature_2m_max, temperature_2m_min, temperature_2m_mean,
            apparent_temperature_max, relative_humidity_2m_mean, precipitation_sum,
            api_request_id, retrieved_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            weather_rows,
        )
        print(f"Inserted {len(weather_rows)} records into fact_weather.")

        # Create denormalized analytical table
        cursor.execute("""
        CREATE TABLE fact_daily_load_weather AS
        SELECT 
            d.demand_id,
            d.date,
            d.state,
            s.state_code,
            s.region,
            s.capital_city,
            s.latitude,
            s.longitude,
            dt.year,
            dt.month,
            dt.day,
            dt.day_of_week,
            dt.day_name,
            dt.is_weekend,
            dt.season,
            dt.is_holiday,
            dt.holiday_name,
            d.max_demand_met_mw,
            d.shortage_mw,
            d.unrestricted_peak_mw,
            d.energy_met_mu,
            d.quality_flag,
            d.flag_reasons,
            w.temperature_2m_max,
            w.temperature_2m_min,
            w.temperature_2m_mean,
            w.apparent_temperature_max,
            w.relative_humidity_2m_mean,
            w.precipitation_sum
        FROM fact_demand d
        JOIN dim_state s ON d.state = s.state_name
        JOIN dim_date dt ON d.date = dt.date
        JOIN fact_weather w ON d.state = w.state AND d.date = w.date;
        """)
        conn.commit()

        # Verification count
        count = cursor.execute("SELECT COUNT(*) FROM fact_daily_load_weather;").fetchone()[0]
        print(f"Created denormalized analytical table fact_daily_load_weather with {count} rows.")

        # Save verification log
        db_stats = {
            "dim_state_count": cursor.execute("SELECT COUNT(*) FROM dim_state;").fetchone()[0],
            "dim_date_count": cursor.execute("SELECT COUNT(*) FROM dim_date;").fetchone()[0],
            "fact_demand_count": cursor.execute("SELECT COUNT(*) FROM fact_demand;").fetchone()[0],
            "fact_weather_count": cursor.execute("SELECT COUNT(*) FROM fact_weather;").fetchone()[0],
            "fact_daily_load_weather_count": count,
            "database_file_size_bytes": DB_PATH.stat().st_size,
        }
        (LOGS_DIR / "database_load_verification.json").write_text(json.dumps(db_stats, indent=2), encoding="utf-8")
        print("Database load verified and logged to logs/database_load_verification.json")

    finally:
        conn.close()

    print("\nPhase 4 Database Loading Complete!")


if __name__ == "__main__":
    load_database()
