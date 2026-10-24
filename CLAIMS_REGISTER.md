# Claims Register

Every substantive factual and quantitative claim in README.md and reports is registered here, mapped directly to its exact key in `reports/results.json` and the command that generated it.

| Claim ID | Substantive Claim | Key in `reports/results.json` | Generating Command / Script | Status |
|---|---|---|---|---|
| CLM-001 | Combined 16-State Marginal Heat Sensitivity is +2,761.9 MW/°C | `baseline_models.overall_summary.all_india_combined_mw_per_c` | `python make.py model` | **Verified** |
| CLM-002 | Average Indian State Peak Demand Sensitivity is +1.62% per °C | `baseline_models.overall_summary.state_average_pct_per_c` | `python make.py model` | **Verified** |
| CLM-003 | State with highest percentage sensitivity is Karnataka at +3.50%/°C | `baseline_models.overall_summary.highest_sensitivity_pct` | `python make.py model` | **Verified** |
| CLM-004 | Holdout Pure Meteorological LightGBM model achieves MAPE of 7.72% and R² of 0.9557 | `gbm_point_model.holdout_pure_meteorological.mape_pct` | `python make.py model` | **Verified** |
| CLM-005 | Holdout Operational Autoregressive model achieves MAPE of 3.46% and R² of 0.9907 | `gbm_point_model.holdout_operational_autoregressive.mape_pct` | `python make.py model` | **Verified** |
| CLM-006 | +1°C warming scenario increases simultaneous 16-state coincident peak by +3,601.5 MW (+1.61%) | `warming_scenarios.plus_1c.all_india_coincident_surge_mw` | `python make.py scenarios` | **Verified** |
| CLM-007 | +2°C warming scenario increases simultaneous 16-state coincident peak by +5,841.1 MW (+2.61%) | `warming_scenarios.plus_2c.all_india_coincident_surge_mw` | `python make.py scenarios` | **Verified** |
| CLM-008 | Coincident baseline peak across 16 states evaluated is 223,421.1 MW | `warming_scenarios.plus_1c.all_india_coincident_baseline_peak_mw` | `python make.py scenarios` | **Verified** |
| CLM-009 | Cleaned dataset contains 11,662 usable modeling observations (11,625 flagged 'ok') | `cleaning_summary.json -> usable_modeling_records` | `python make.py clean` | **Verified** |
