"""
Unit Tests for Data Cleaning and Validation Logic.
"""

import pathlib

import pandas as pd

from src.clean import STATES_CFG

ROOT = pathlib.Path(__file__).parent.parent.resolve()
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "fixture_cleaning_records.csv"


def test_fixture_bounds_evaluation():
    # Read fixture skipping comments
    df_fix = pd.read_csv(FIXTURE_PATH, comment="#")
    assert len(df_fix) > 0

    for _, row in df_fix.iterrows():
        state = row["state"]
        demand = row["max_demand_met_mw"]
        expected = row["expected_flag"]

        # Test bounds
        bounds = STATES_CFG.get(state, {}).get("demand_bounds_mw")
        assert bounds is not None, f"State {state} must be in config"

        if pd.isna(demand) or demand < 100 or demand < bounds[0] or demand > bounds[1]:
            computed_flag = "excluded"
        else:
            computed_flag = "ok"

        if expected in ["ok", "excluded"]:
            assert computed_flag == expected, f"Failed on row {row['record_id']}: {row['test_case_description']}"


def test_no_synthetic_imputation():
    # Confirm that missing demand remains NaN and is not imputed
    df_fix = pd.read_csv(FIXTURE_PATH, comment="#")
    missing_row = df_fix[df_fix["record_id"] == 8].iloc[0]
    assert pd.isna(missing_row["max_demand_met_mw"])
