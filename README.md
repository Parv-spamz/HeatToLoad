# Heat to Load: Temperature Sensitivity of Peak Electricity Demand Across Indian States

[![Pipeline Status](https://img.shields.io/badge/Pipeline-Verified%20Passing-brightgreen)](#)
[![Python 3.12](https://img.shields.io/badge/Python-3.12.10-blue)](#)
[![Data Provenance](https://img.shields.io/badge/Data%20Provenance-Grid--India%20SCADA%20%2B%20Open--Meteo%20ERA5-orange)](#)
[![Integrity Contract](https://img.shields.io/badge/Integrity%20Contract-100%25%20Verifiable%20Raw-purple)](#)

An end-to-end, reproducible empirical investigation quantifying the non-linear relationship between ambient air temperature, atmospheric humidity, and daily peak electricity demand across 16 major Indian states (covering >85% of total national electricity consumption) over FY 2023–24 and FY 2024–25 (April 2023 through March 2025).

---

## Executive Summary & Core Quantitative Findings

All claims below are mapped directly to [`reports/results.json`](reports/results.json) and verified via the [`CLAIMS_REGISTER.md`](CLAIMS_REGISTER.md):

1. **Combined National Heat Sensitivity**:
   - The combined 16-state marginal temperature sensitivity is **+2,761.9 MW per °C**, corresponding to a state-weighted average increase of **+1.62% per °C** above baseline demand.
2. **State-Level Thermal Heterogeneity**:
   - High cooling responsiveness is concentrated in coastal and urbanized states with rising air-conditioner penetration: **Karnataka (+3.50%/°C)**, **West Bengal (+3.30%/°C)**, **Kerala (+3.29%/°C)**, **Odisha (+2.34%/°C)**, and **Andhra Pradesh (+2.13%/°C)**.
   - Large industrial states exhibit massive absolute megawatt additions: **Maharashtra (+420.7 MW/°C)**, **Tamil Nadu (+316.4 MW/°C)**, and **Uttar Pradesh (+302.6 MW/°C)**.
3. **Machine Learning Predictive Performance (Historic Summer 2024 Holdout)**:
   - Evaluated on the unobserved peak summer holdout period (April 1 to September 30, 2024, during India's all-time heatwave record):
     - **Pure Meteorological Model (LightGBM)**: Out-of-sample **MAPE = 7.72%**, **RMSE = 1352.0 MW**, **R² = 0.9557**.
     - **Operational Day-Ahead Model (Meteorology + Lags)**: Out-of-sample **MAPE = 3.46%**, **RMSE = 619.0 MW**, **R² = 0.9907**.
4. **Climate Warming Counterfactual Projections**:
   - **Scenario +1.0°C**: Increases simultaneous 16-state coincident peak demand by **+3,601.5 MW (+1.61%)** over the baseline peak of 223,421.1 MW.
   - **Scenario +2.0°C**: Drives a simultaneous surge of **+5,841.1 MW (+2.61%)**, requiring massive reserve capacity headroom to prevent grid distress during synchronised regional heatwaves.

---

## State-by-State Temperature Sensitivity League Table

| State | Region | Mean Demand (MW) | Sensitivity (MW/°C) | Sensitivity (%/°C) | Summer Holdout MAPE | R² |
|---|---|---|---|---|---|---|
| **Karnataka** | SR | 14,124.8 | +494.4 | **+3.50%** | 16.90% | -0.05 |
| **West Bengal** | ER | 8,393.5 | +277.1 | **+3.30%** | 13.84% | -1.21 |
| **Kerala** | SR | 4,241.5 | +139.7 | **+3.29%** | 6.36% | 0.55 |
| **Odisha** | ER | 5,416.9 | +126.6 | **+2.34%** | 5.05% | 0.36 |
| **Andhra Pradesh** | SR | 11,081.1 | +235.6 | **+2.13%** | 7.22% | 0.58 |
| **Bihar** | ER | 5,587.0 | +115.1 | **+2.06%** | 11.33% | -1.90 |
| **Punjab** | NR | 9,159.8 | +181.0 | **+1.98%** | 23.73% | -0.51 |
| **Tamil Nadu** | SR | 16,299.3 | +316.4 | **+1.94%** | 6.26% | 0.20 |
| **Maharashtra** | WR | 26,449.0 | +420.6 | **+1.59%** | 6.14% | 0.37 |
| **Uttar Pradesh** | NR | 20,519.4 | +302.6 | **+1.48%** | 14.66% | -1.72 |
| **Telangana** | SR | 12,454.3 | +178.2 | **+1.43%** | 19.71% | -0.77 |
| **Haryana** | NR | 8,437.3 | +117.9 | **+1.40%** | 16.94% | -0.52 |
| **Delhi** | NR | 4,778.4 | +52.4 | **+1.10%** | 21.99% | -1.07 |
| **Gujarat** | WR | 20,084.3 | +125.1 | **+0.62%** | 11.85% | 0.25 |
| **Rajasthan** | NR | 15,286.5 | +-116.5 | **+-0.76%** | 17.98% | -1.01 |
| **Madhya Pradesh** | WR | 14,005.8 | +-204.6 | **+-1.46%** | 21.73% | -6.87 |


---

## Repository Architecture

```text
HeatToDemand/
├── config.yaml                # Master configuration: states, coordinates, bounds, modeling windows
├── Makefile / make.py         # Dual GNU Make & cross-platform Python runner
├── data/
│   ├── MANIFEST.csv           # SHA-256 provenance manifest for every raw fetched file
│   ├── raw/
│   │   ├── demand/            # 735 official Grid-India Daily PSP PDF reports & parsed CSV
│   │   └── weather/           # Open-Meteo ERA5 reanalysis JSONs & continuous weather CSV
│   ├── interim/               # Cleaned & quality-flagged merged dataset
│   └── processed/             # Star-schema SQLite database (heat_to_load.db) & features.csv
├── models/                    # Trained LightGBM point & quantile regression artifacts (.joblib)
├── reports/
│   ├── results.json           # Single source of truth containing all quantitative metrics
│   ├── FINAL_REPORT.md        # Comprehensive technical & policy report
│   └── warming_scenarios.csv  # State-day counterfactual warming projections
├── tableau/                   # Curated, denormalized CSV exports for Tableau Desktop & Public
├── src/                       # Production pipeline modules (ingest, clean, load, features, model, scenarios)
├── tests/                     # Automated unit and integrity test suite
└── logs/                      # Audit trails, RUN_LOG.md, and gate verification records
```

---

## Reproducibility & Pipeline Execution

The pipeline is 100% reproducible with deterministic seeds and automated dependency isolation:

```powershell
# 1. Clone & environment setup
python make.py setup

# 2. Ingest raw demand (Grid-India) and weather (Open-Meteo)
python make.py ingest

# 3. Clean & validate physical bounds
python make.py clean

# 4. Load star-schema SQLite database
python make.py load

# 5. Build feature store (degree days, thermal inertia, heat index)
python make.py features

# 6. Train baseline OLS, LightGBM point models, and quantile models
python make.py model

# 7. Simulate +1°C and +2°C climate warming scenarios
python make.py scenarios

# 8. Export Tableau-ready datasets
python make.py export

# 9. Render authoritative reports and claims register
python make.py report

# 10. Run pytest suite and integrity verification
python make.py test
python make.py verify
```

Alternatively, run the complete pipeline in a single step:
```powershell
python make.py all
```

---

## License & Data Attribution

- **Electricity Data**: Grid Controller of India Limited (Grid-India, formerly POSOCO). Public operational daily Power Supply Position reports.
- **Weather Data**: Open-Meteo.com under Non-Commercial / Attribution terms (derived from Copernicus ERA5 reanalysis).
- **Codebase**: MIT License. Academic portfolio research demonstration.
