# Tableau Visualization Architecture & Guide

This directory contains standardized, clean, denormalized datasets optimized for Tableau Desktop, Tableau Public, and PowerBI.

## Packaged Datasets

1. **`tableau_daily_state_load.csv`**:
   - Primary daily observation table (11,680 rows across 16 major Indian states for FY 2023-24 and FY 2024-25).
   - Variables include SCADA peak demand (`max_demand_met_mw`), ERA5 weather (`temperature_2m_max`, `apparent_temperature_max`, `relative_humidity_2m_mean`), Cooling Degree Days (`cdd_24`), Heat Index, and IMD-aligned `is_heatwave` indicators.

2. **`tableau_state_sensitivity_summary.csv`**:
   - State-level sensitivity coefficients ($\Delta \text{MW} / ^\circ\text{C}$ and $\% / ^\circ\text{C}$).
   - Baseline average load and simulated peak surge under +1°C and +2°C warming.

3. **`tableau_warming_scenarios.csv`**:
   - Counterfactual daily load projections across baseline, +1°C, and +2°C scenarios for FY 2024-25.

## Recommended Tableau Visualizations

### Dashboard 1: India Heat-to-Load Geo-Spatial Cockpit
- **Choropleth Map / Symbol Map**: State centroids mapped to `latitude` and `longitude`, sized by `linear_sensitivity_mw_per_c` and color-coded by `linear_sensitivity_pct_per_c`.
- **Scatter Plot (Thermal Response Curve)**: `temperature_2m_max` on X-axis vs `max_demand_met_mw` on Y-axis with polynomial/piecewise trend line showing the sharp inflection above 28°C.
- **Interactive State Filter**: Allows single or multi-state drill-down.

### Dashboard 2: Heatwave Stress & Peak Load Spikes (Summer 2024)
- **Dual-Axis Timeline**: Daily peak demand (Area chart) alongside maximum daily temperature (Line chart) highlighting the historic May-June 2024 heatwave period.
- **Heatwave Days Highlight**: Filter or highlight using `is_heatwave = 1`.

### Dashboard 3: Climate Scenario Simulator (+1°C vs +2°C)
- **Bar Chart Comparison**: Simultaneous 16-state coincident peak under Baseline vs +1°C vs +2°C.
- **Capacity Headroom Waterfall**: Extra gigawatts required to maintain grid adequacy under progressive global warming.

## Calculated Fields in Tableau

- **`Peak Capacity Utilization (%)`**:
  `[Max Demand Met Mw] / [Demand Bound Max Mw] * 100`

- **`Thermal Responsiveness Category`**:
  `IF [Linear Sensitivity Pct Per C] >= 3.0 THEN "High Heat Sensitivity (>3%/°C)" ELSEIF [Linear Sensitivity Pct Per C] >= 1.5 THEN "Moderate Sensitivity (1.5-3.0%/°C)" ELSE "Low Heat Sensitivity (<1.5%/°C)" END`
