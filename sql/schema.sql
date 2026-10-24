-- ==============================================================================
-- Schema Definition: Indian Electricity Demand and Weather Star Schema
-- Database: SQLite (data/processed/heat_to_load.db)
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- Dimension 1: State Metadata & Capacity Constraints
DROP TABLE IF EXISTS fact_daily_load_weather;
DROP TABLE IF EXISTS fact_demand;
DROP TABLE IF EXISTS fact_weather;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_state;

CREATE TABLE dim_state (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name TEXT UNIQUE NOT NULL,
    state_code TEXT NOT NULL,
    region TEXT NOT NULL,                -- NR, WR, SR, ER, NER
    capital_city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    coord_source TEXT NOT NULL,
    demand_bound_min_mw REAL NOT NULL,   -- Baseload physical plausibility lower bound
    demand_bound_max_mw REAL NOT NULL    -- Historical peak capacity plausibility upper bound
);

-- Dimension 2: Calendar & Seasonal Dimensions
CREATE TABLE dim_date (
    date TEXT PRIMARY KEY,               -- ISO 8601 YYYY-MM-DD
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,        -- 0=Monday, 6=Sunday
    day_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL,         -- 1 if Saturday or Sunday
    season TEXT NOT NULL,                -- Summer, Monsoon, Post-Monsoon, Winter
    is_holiday INTEGER NOT NULL,         -- 1 if gazetted public holiday
    holiday_name TEXT
);

-- Fact 1: Daily Peak Electricity Demand Met & Shortage (Grid-India SCADA)
CREATE TABLE fact_demand (
    demand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL REFERENCES dim_date(date),
    state TEXT NOT NULL REFERENCES dim_state(state_name),
    max_demand_met_mw REAL,              -- SCADA peak demand served during the day
    shortage_mw REAL,                    -- Unmet shortage during peak
    unrestricted_peak_mw REAL,           -- max_demand_met_mw + shortage_mw
    energy_met_mu REAL,                  -- Total energy served in Million Units (MU)
    quality_flag TEXT NOT NULL,          -- ok, weather_interpolated, outlier_review, excluded
    flag_reasons TEXT,
    source_file TEXT,                    -- Source PSP report PDF filename
    page_number INTEGER,                 -- PDF page containing data table
    retrieved_at_utc TEXT
);

-- Fact 2: Daily Meteorological Observations (Open-Meteo ERA5 Reanalysis)
CREATE TABLE fact_weather (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL REFERENCES dim_date(date),
    state TEXT NOT NULL REFERENCES dim_state(state_name),
    temperature_2m_max REAL,             -- Daily maximum 2m dry-bulb temperature (°C)
    temperature_2m_min REAL,             -- Daily minimum 2m dry-bulb temperature (°C)
    temperature_2m_mean REAL,            -- Daily mean 2m temperature (°C)
    apparent_temperature_max REAL,      -- Daily maximum perceived temperature (°C)
    relative_humidity_2m_mean REAL,      -- Daily mean relative humidity (%)
    precipitation_sum REAL,              -- Total daily precipitation (mm)
    api_request_id TEXT,
    retrieved_at_utc TEXT
);

-- Indexes for Fast Query Optimization
CREATE INDEX idx_demand_state_date ON fact_demand(state, date);
CREATE INDEX idx_weather_state_date ON fact_weather(state, date);
CREATE INDEX idx_demand_quality ON fact_demand(quality_flag);
CREATE INDEX idx_date_year_month ON dim_date(year, month);
CREATE INDEX idx_state_region ON dim_state(region);
