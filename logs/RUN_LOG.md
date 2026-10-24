# Pipeline Execution Run Log

Append-only log of pipeline commands and gates. Each entry records the UTC timestamp, phase/step, exact command executed, exit code, outcome summary, and output log path.

| Timestamp (UTC) | Step | Command | Exit Code | Outcome | Log Path |
|---|---|---|---|---|---|
| 2026-10-23T20:19:44Z | Phase 0 Setup | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | 0 | Installed all pinned packages including lightgbm, shap, statsmodels, camelot-py | logs/pip_freeze.txt |
| 2026-10-23T20:21:56Z | Phase 0 Gate | `python make.py setup` | 0 | GATE 0 PASSED: requirements installed and logs/pip_freeze.txt verified | logs/pip_freeze.txt |
| 2026-10-23T20:34:00Z | Phase 1 Gate | `python src/sample_across_years.py && python src/test_open_meteo.py && python src/test_holidays.py` | 0 | GATE 1 PASSED: demand_source_report.md and source_verification.md created from fetched evidence | logs/demand_source_report.md |
| 2026-10-24T13:32:19Z | Phase 2 Gate | `python make.py ingest` | 0 | GATE 2 PASSED: 11,728 raw demand records parsed (99.7% success across 735 reports), MANIFEST with 747 entries, spotcheck_demand.md created | logs/spotcheck_demand.md |
| 2026-10-24T13:33:07Z | Phase 3 Gate | `python make.py clean` | 0 | GATE 3 PASSED: Cleaned 11,696 records (99.4% ok, 34 excluded, 32 interpolated, 5 outlier review), logged to cleaning_summary.json | logs/cleaning_summary.json |
| 2026-10-24T13:33:26Z | Phase 4 Gate | `python make.py load` | 0 | GATE 4 PASSED: Loaded SQLite database heat_to_load.db with star-schema tables and analytical table | logs/database_load_verification.json |
| 2026-10-24T13:33:40Z | Phase 5 Gate | `python make.py features` | 0 | GATE 5 PASSED: Built 53 engineered features (degree days, thermal inertia, heat index, heatwave flags) | logs/feature_metadata.json |
| 2026-10-24T13:36:04Z | Phase 6 Gate | `python make.py model && python make.py scenarios` | 0 | GATE 6 PASSED: OLS baseline (+2,761.9 MW/C), LightGBM (Operational MAPE 3.46%, R2 0.9907), Quantile & SHAP, +1C/+2C Scenarios (+3,601.5 MW / +5,841.1 MW surge) | reports/results.json |
| 2026-10-24T13:37:45Z | Phase 7 Gate | `python make.py export && python make.py report` | 0 | GATE 7 PASSED: Tableau datasets exported, README.md, FINAL_REPORT.md, and CLAIMS_REGISTER.md rendered | reports/FINAL_REPORT.md |
| 2026-10-24T13:41:23Z | Phase 8 Gate | `python make.py test && python make.py verify` | 0 | GATE 8 PASSED: 9/9 pytest passed, Ruff/Black clean, 18/18 artifact checks passed, SHA-256 verified, Zero synthetic demand verified | logs/integrity_verification_report.json |


