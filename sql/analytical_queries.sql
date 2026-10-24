-- ==============================================================================
-- Curated Analytical Queries for Energy Economists & Grid Operators
-- Database: SQLite (data/processed/heat_to_load.db)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Query 1: Top 5 All-Time Historical Peak Demand Days per State
-- Identifies maximum stress events with corresponding ambient temperatures.
-- ------------------------------------------------------------------------------
WITH RankedDemand AS (
    SELECT 
        d.state,
        d.date,
        d.max_demand_met_mw,
        d.shortage_mw,
        w.temperature_2m_max,
        w.apparent_temperature_max,
        w.relative_humidity_2m_mean,
        ROW_NUMBER() OVER (PARTITION BY d.state ORDER BY d.max_demand_met_mw DESC) as rnk
    FROM fact_demand d
    JOIN fact_weather w ON d.state = w.state AND d.date = w.date
    WHERE d.quality_flag = 'ok'
)
SELECT 
    state,
    rnk as peak_rank,
    date,
    max_demand_met_mw,
    shortage_mw,
    temperature_2m_max as t_max_c,
    apparent_temperature_max as app_t_max_c,
    relative_humidity_2m_mean as rel_humidity_pct
FROM RankedDemand
WHERE rnk <= 3
ORDER BY state, rnk;

-- ------------------------------------------------------------------------------
-- Query 2: Regional Monthly Aggregate Coincident Demand & Temperature
-- Compares regional demand volume and mean temperature across seasons.
-- ------------------------------------------------------------------------------
SELECT 
    s.region,
    dt.year,
    dt.month,
    dt.season,
    COUNT(DISTINCT d.date) as active_days,
    ROUND(AVG(d.max_demand_met_mw), 1) as avg_daily_peak_mw,
    ROUND(MAX(d.max_demand_met_mw), 1) as max_state_peak_mw,
    ROUND(AVG(w.temperature_2m_max), 2) as avg_max_temp_c,
    ROUND(AVG(w.relative_humidity_2m_mean), 1) as avg_rel_humidity_pct
FROM fact_demand d
JOIN dim_state s ON d.state = s.state_name
JOIN dim_date dt ON d.date = dt.date
JOIN fact_weather w ON d.state = w.state AND d.date = w.date
WHERE d.quality_flag = 'ok'
GROUP BY s.region, dt.year, dt.month
ORDER BY s.region, dt.year, dt.month;

-- ------------------------------------------------------------------------------
-- Query 3: Extreme Heatwave Day Performance (May-June 2024 vs May-June 2023)
-- Measures year-over-year load growth during peak pre-monsoon heatwave months.
-- ------------------------------------------------------------------------------
SELECT 
    d.state,
    ROUND(AVG(CASE WHEN dt.year = 2023 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END), 1) as peak_may_jun_2023_mw,
    ROUND(AVG(CASE WHEN dt.year = 2024 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END), 1) as peak_may_jun_2024_mw,
    ROUND(
        (AVG(CASE WHEN dt.year = 2024 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END) -
         AVG(CASE WHEN dt.year = 2023 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END)), 1
    ) as yoy_absolute_growth_mw,
    ROUND(
        ((AVG(CASE WHEN dt.year = 2024 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END) -
          AVG(CASE WHEN dt.year = 2023 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END)) /
         AVG(CASE WHEN dt.year = 2023 AND dt.month IN (5, 6) THEN d.max_demand_met_mw END)) * 100.0, 2
    ) as yoy_growth_pct
FROM fact_demand d
JOIN dim_date dt ON d.date = dt.date
WHERE d.quality_flag = 'ok' AND dt.month IN (5, 6)
GROUP BY d.state
ORDER BY yoy_growth_pct DESC;

-- ------------------------------------------------------------------------------
-- Query 4: Weekend vs Weekday Demand Destruction / Industrial Load Profile
-- Measures the drop in electricity consumption on weekends by state.
-- ------------------------------------------------------------------------------
SELECT 
    d.state,
    ROUND(AVG(CASE WHEN dt.is_weekend = 0 THEN d.max_demand_met_mw END), 1) as weekday_mean_mw,
    ROUND(AVG(CASE WHEN dt.is_weekend = 1 THEN d.max_demand_met_mw END), 1) as weekend_mean_mw,
    ROUND(
        (AVG(CASE WHEN dt.is_weekend = 1 THEN d.max_demand_met_mw END) - 
         AVG(CASE WHEN dt.is_weekend = 0 THEN d.max_demand_met_mw END)), 1
    ) as weekend_delta_mw,
    ROUND(
        ((AVG(CASE WHEN dt.is_weekend = 1 THEN d.max_demand_met_mw END) - 
          AVG(CASE WHEN dt.is_weekend = 0 THEN d.max_demand_met_mw END)) / 
         AVG(CASE WHEN dt.is_weekend = 0 THEN d.max_demand_met_mw END)) * 100.0, 2
    ) as weekend_drop_pct
FROM fact_demand d
JOIN dim_date dt ON d.date = dt.date
WHERE d.quality_flag = 'ok'
GROUP BY d.state
ORDER BY weekend_drop_pct ASC;

-- ------------------------------------------------------------------------------
-- Query 5: Data Quality and Integrity Audit Summary
-- Reports completeness, physical bound violations, and interpolation tracking.
-- ------------------------------------------------------------------------------
SELECT 
    state,
    COUNT(*) as total_days_recorded,
    SUM(CASE WHEN quality_flag = 'ok' THEN 1 ELSE 0 END) as ok_clean_days,
    SUM(CASE WHEN quality_flag = 'weather_interpolated' THEN 1 ELSE 0 END) as weather_interpolated_days,
    SUM(CASE WHEN quality_flag = 'outlier_review' THEN 1 ELSE 0 END) as outlier_review_days,
    SUM(CASE WHEN quality_flag = 'excluded' THEN 1 ELSE 0 END) as excluded_days,
    ROUND((CAST(SUM(CASE WHEN quality_flag = 'ok' THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 100.0, 2) as clean_data_pct
FROM fact_demand
GROUP BY state
ORDER BY clean_data_pct DESC;
