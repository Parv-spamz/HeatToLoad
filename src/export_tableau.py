"""
Tableau Export Pipeline (Phase 7a).
Prepares curated, production-ready CSV exports for Tableau Desktop & Public:
- tableau/tableau_daily_state_load.csv (Daily state demand, weather, degree days, heatwave flags)
- tableau/tableau_state_sensitivity_summary.csv (Aggregated sensitivity metrics per state)
- tableau/tableau_warming_scenarios.csv (Daily counterfactual warming projections)
- tableau/README_TABLEAU.md (Workbook architecture and calculated fields guide)
"""

import json
import pathlib

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

TABLEAU_DIR = ROOT / "tableau"
TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
RESULTS_JSON_PATH = REPORTS_DIR / "results.json"

FEATURES_PATH = PROCESSED_DIR / "features.csv"
SCENARIOS_PATH = REPORTS_DIR / "warming_scenarios.csv"
SENSITIVITY_PATH = REPORTS_DIR / "state_temperature_sensitivity.csv"


def export_tableau_data():
    print("=" * 70)
    print("Starting Phase 7a Tableau Data Export")
    print(f"Export directory: {TABLEAU_DIR}")
    print("=" * 70)

    if not FEATURES_PATH.exists():
        raise FileNotFoundError(f"Feature dataset not found at {FEATURES_PATH}. Run 'make features' first.")

    df_feat = pd.read_csv(FEATURES_PATH)
    print(f"Loaded {len(df_feat)} feature records.")

    # 1. Main Daily State Load Dataset
    tableau_cols = [
        "date",
        "state",
        "state_code",
        "region",
        "capital_city",
        "latitude",
        "longitude",
        "max_demand_met_mw",
        "shortage_mw",
        "unrestricted_peak_mw",
        "energy_met_mu",
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "apparent_temperature_max",
        "relative_humidity_2m_mean",
        "precipitation_sum",
        "cdd_18",
        "cdd_24",
        "hdd_18",
        "heat_index",
        "is_heatwave",
        "quality_flag",
        "is_weekend",
        "is_holiday",
        "season",
        "is_holdout",
    ]
    df_main = df_feat[[c for c in tableau_cols if c in df_feat.columns]].copy()
    out_main = TABLEAU_DIR / "tableau_daily_state_load.csv"
    df_main.to_csv(out_main, index=False)
    print(f"Exported main daily load dataset: {out_main} ({len(df_main)} rows)")

    # 2. State Sensitivity Summary
    if SENSITIVITY_PATH.exists():
        df_sens = pd.read_csv(SENSITIVITY_PATH)
        # Add region and capital info
        regions = {k: v["region"] for k, v in cfg["states"].items()}
        cities = {k: v["city"] for k, v in cfg["states"].items()}
        df_sens["region"] = df_sens["state"].map(regions)
        df_sens["capital_city"] = df_sens["state"].map(cities)

        # Merge scenario increments if available
        if RESULTS_JSON_PATH.exists():
            try:
                res = json.loads(RESULTS_JSON_PATH.read_text(encoding="utf-8"))
                surges_1c = res.get("warming_scenarios", {}).get("plus_1c", {}).get("state_surges", {})
                surges_2c = res.get("warming_scenarios", {}).get("plus_2c", {}).get("state_surges", {})
                df_sens["surge_plus_1c_mw"] = df_sens["state"].map(
                    lambda s: surges_1c.get(s, {}).get("mean_daily_surge_mw")
                )
                df_sens["surge_plus_2c_mw"] = df_sens["state"].map(
                    lambda s: surges_2c.get(s, {}).get("mean_daily_surge_mw")
                )
            except Exception as e:
                print(f"Warning merging scenario summaries: {e}")

        out_sens = TABLEAU_DIR / "tableau_state_sensitivity_summary.csv"
        df_sens.to_csv(out_sens, index=False)
        print(f"Exported state sensitivity summary: {out_sens} ({len(df_sens)} rows)")

    # 3. Warming Scenarios Export
    if SCENARIOS_PATH.exists():
        df_scen = pd.read_csv(SCENARIOS_PATH)
        out_scen = TABLEAU_DIR / "tableau_warming_scenarios.csv"
        df_scen.to_csv(out_scen, index=False)
        print(f"Exported warming scenarios: {out_scen} ({len(df_scen)} rows)")

    # 4. Generate Tableau Documentation Guide
    guide_content = r"""# Tableau Visualization Architecture & Guide

This directory contains standardized, clean, denormalized datasets optimized for Tableau Desktop, Tableau Public, and PowerBI.

## Packaged Datasets

1. **`tableau_daily_state_load.csv`**:
   - Primary daily observation table (11,680 rows across 16 major Indian states for FY 2023-24 and FY 2024-25).
   - Variables include SCADA peak demand (`max_demand_met_mw`), ERA5 weather (`temperature_2m_max`, `apparent_temperature_max`, `relative_humidity_2m_mean`), Cooling Degree Days (`cdd_24`), Heat Index, and IMD-aligned `is_heatwave` indicators.

2. **`tableau_state_sensitivity_summary.csv`**:
   - State-level sensitivity coefficients ($\Delta \\text{MW} / ^\circ\\text{C}$ and $\% / ^\circ\\text{C}$).
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
"""
    (TABLEAU_DIR / "README_TABLEAU.md").write_text(guide_content, encoding="utf-8")
    print(f"Generated Tableau architecture guide at {TABLEAU_DIR / 'README_TABLEAU.md'}")

    print("\nPhase 7a Tableau Export Complete!")


if __name__ == "__main__":
    export_tableau_data()
