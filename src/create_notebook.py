"""
Generate Jupyter Walkthrough Notebook.
"""

import pathlib

import nbformat as nbf

ROOT = pathlib.Path(__file__).parent.parent.resolve()
NOTEBOOK_PATH = ROOT / "notebooks" / "01_exploratory_and_modeling_walkthrough.ipynb"

nb = nbf.v4.new_notebook()

nb.cells = [
    nbf.v4.new_markdown_cell("""# Heat to Load: Temperature Sensitivity of Indian Peak Electricity Demand
### Comprehensive Exploratory Data Analysis & Modeling Walkthrough

**Authors:** Data Science & Energy Portfolio Research  
**Reference Period:** FY 2023–24 and FY 2024–25 (April 2023 to March 2025)  
**States:** 16 Major Indian States (>85% National Electricity Consumption)  

---

## 1. Problem Statement & Motivation
India's electric grid is undergoing unprecedented stress during summer pre-monsoon heatwaves. Peak demand exceeded 250 GW in May-June 2024, driven by exponential adoption of air conditioners. 

In this notebook, we demonstrate the complete empirical analysis:
1. Connecting to the star-schema SQLite database (`heat_to_load.db`).
2. Examining non-linear thermal response curves across states.
3. Quantifying baseline temperature sensitivities ($\\Delta\\text{MW}/^\\circ\\text{C}$ and % / °C).
4. Evaluating LightGBM predictive models on the historic Summer 2024 holdout partition.
5. Interpreting driver importances using SHAP TreeExplainer.
6. Simulating climate warming scenarios (+1°C and +2°C).
"""),
    nbf.v4.new_code_cell("""import sqlite3
import json
import pathlib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import lightgbm as lgb
import statsmodels.api as sm
import shap

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['figure.figsize'] = (10, 5)

ROOT = pathlib.Path('..').resolve()
DB_PATH = ROOT / 'data' / 'processed' / 'heat_to_load.db'
RESULTS_PATH = ROOT / 'reports' / 'results.json'

print(f"Database exists: {DB_PATH.exists()}")
print(f"Authoritative results exist: {RESULTS_PATH.exists()}")
"""),
    nbf.v4.new_markdown_cell("""## 2. Relational Star Schema Database Inspection
We connect to SQLite to query `fact_daily_load_weather` joining state metadata, calendar flags, SCADA peak demand, and ERA5 weather variables.
"""),
    nbf.v4.new_code_cell("""conn = sqlite3.connect(DB_PATH)
query = \"\"\"
SELECT 
    state, date, region, capital_city,
    max_demand_met_mw, shortage_mw, energy_met_mu,
    temperature_2m_max, temperature_2m_min, relative_humidity_2m_mean,
    is_weekend, is_holiday, season
FROM fact_daily_load_weather
WHERE quality_flag != 'excluded'
ORDER BY state, date;
\"\"\"
df = pd.read_sql_query(query, conn)
conn.close()

print(f"Loaded {len(df):,} valid analytical records across {df['state'].nunique()} states.")
df.head()
"""),
    nbf.v4.new_markdown_cell("""## 3. Exploratory Data Analysis: Non-linear Temperature Response Curves
Let us visualize the relationship between daily maximum temperature (°C) and peak electricity demand (MW) across representative states. Notice the clear 'hockey-stick' inflection above 28°C.
"""),
    nbf.v4.new_code_cell("""states_to_plot = ['Maharashtra', 'Uttar Pradesh', 'Karnataka', 'Delhi']
fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey=False)
axes = axes.flatten()

for idx, state in enumerate(states_to_plot):
    ax = axes[idx]
    s_data = df[df['state'] == state].dropna(subset=['temperature_2m_max', 'max_demand_met_mw'])
    
    ax.scatter(s_data['temperature_2m_max'], s_data['max_demand_met_mw'], alpha=0.35, s=25, color='#2980b9')
    
    # Polynomial trend line
    z = np.polyfit(s_data['temperature_2m_max'], s_data['max_demand_met_mw'], 2)
    p = np.poly1d(z)
    t_grid = np.linspace(s_data['temperature_2m_max'].min(), s_data['temperature_2m_max'].max(), 100)
    ax.plot(t_grid, p(t_grid), color='#c0392b', linewidth=2.5, label='Fitted Response')
    
    ax.axvline(28.0, color='gray', linestyle='--', linewidth=1, label='28°C Inflection')
    ax.set_title(f"{state} Load-Temperature Response", fontweight='bold')
    ax.set_xlabel("Max Temperature (°C)")
    ax.set_ylabel("Peak Demand (MW)")
    ax.legend(loc='upper left', frameon=True)

plt.suptitle("Non-linear Hockey-Stick Inflection in Cooling Demand", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()
"""),
    nbf.v4.new_markdown_cell("""## 4. State Temperature Sensitivity League Table
Let us load the verified econometric sensitivity estimates from `reports/state_temperature_sensitivity.csv`.
"""),
    nbf.v4.new_code_cell("""df_sens = pd.read_csv(ROOT / 'reports' / 'state_temperature_sensitivity.csv')
df_sens_sorted = df_sens.sort_values('linear_sensitivity_pct_per_c', ascending=False).reset_index(drop=True)

df_sens_sorted[['state', 'mean_demand_mw', 'linear_sensitivity_mw_per_c', 'linear_sensitivity_pct_per_c', 'holdout_mape_pct', 'holdout_r2']]
"""),
    nbf.v4.new_markdown_cell("""## 5. Machine Learning Holdout Evaluation & SHAP Attribution
Let us examine the out-of-sample predictive performance on the historic May-June 2024 heatwave and the SHAP TreeExplainer feature importance rankings.
"""),
    nbf.v4.new_code_cell("""with open(RESULTS_PATH, 'r', encoding='utf-8') as f:
    results = json.load(f)

gbm_res = results['gbm_point_model']
print('=== Pure Meteorological Model (Holdout Summer 2024) ===')
print(f"MAPE: {gbm_res['holdout_pure_meteorological']['mape_pct']:.2f}%")
print(f"RMSE: {gbm_res['holdout_pure_meteorological']['rmse_mw']:.1f} MW")
print(f"R²:   {gbm_res['holdout_pure_meteorological']['r2']:.4f}")

print('\\n=== Operational Model with Autoregressive Lags ===')
print(f"MAPE: {gbm_res['holdout_operational_autoregressive']['mape_pct']:.2f}%")
print(f"RMSE: {gbm_res['holdout_operational_autoregressive']['rmse_mw']:.1f} MW")
print(f"R²:   {gbm_res['holdout_operational_autoregressive']['r2']:.4f}")
"""),
    nbf.v4.new_markdown_cell("""## 6. Climate Warming Counterfactual Projections (+1°C and +2°C)
Finally, we inspect the simultaneous 16-state coincident peak surge under uniform +1°C and +2°C warming scenarios.
"""),
    nbf.v4.new_code_cell("""scen_res = results['warming_scenarios']
s1 = scen_res['plus_1c']
s2 = scen_res['plus_2c']

print(f"Baseline Coincident Peak: {s1['all_india_coincident_baseline_peak_mw']:,.1f} MW")
print(f"+1.0°C Warming Coincident Peak: {s1['all_india_coincident_scenario_peak_mw']:,.1f} MW (Surge: +{s1['all_india_coincident_surge_mw']:,.1f} MW / +{s1['all_india_coincident_surge_pct']:.2f}%)")
print(f"+2.0°C Warming Coincident Peak: {s2['all_india_coincident_scenario_peak_mw']:,.1f} MW (Surge: +{s2['all_india_coincident_surge_mw']:,.1f} MW / +{s2['all_india_coincident_surge_pct']:.2f}%)")

scenarios = ['Baseline', '+1.0°C Warming', '+2.0°C Warming']
peaks = [
    s1['all_india_coincident_baseline_peak_mw'] / 1000.0,
    s1['all_india_coincident_scenario_peak_mw'] / 1000.0,
    s2['all_india_coincident_scenario_peak_mw'] / 1000.0
]

fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(scenarios, peaks, color=['#34495e', '#e67e22', '#c0392b'], edgecolor='black', alpha=0.85, width=0.55)
ax.set_ylabel('Simultaneous 16-State Coincident Peak (GW)', fontweight='bold')
ax.set_ylim(210, 240)
for bar in bars:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f'{h:.1f} GW', ha='center', fontweight='bold', fontsize=10)
plt.title('Simultaneous Peak Grid Capacity Required Under Global Warming', fontweight='bold', fontsize=12)
plt.tight_layout()
plt.show()
"""),
]

NOTEBOOK_PATH.write_text(nbf.writes(nb), encoding="utf-8")
print(f"Generated walkthrough notebook at {NOTEBOOK_PATH}")
