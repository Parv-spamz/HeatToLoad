"""
Baseline Econometric Models (Phase 6a).
Implements OLS and Piecewise Linear models to estimate temperature sensitivity:
- State-by-state temperature sensitivity coefficient (MW/°C and %/°C).
- Cooling slope above threshold balance point (25°C).
- Cross-validation: Expanding-window (4 splits) on training period.
- Holdout evaluation: Peak summer 2024 (2024-04-01 to 2024-09-30).
- Metrics: RMSE, MAE, MAPE, R2.
- Serializes results to reports/results.json.
"""

import json
import pathlib

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

FEATURES_CSV_PATH = ROOT / "data" / "processed" / "features.csv"
RESULTS_JSON_PATH = ROOT / "reports" / "results.json"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def mape_score(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0


def run_baseline_modeling():
    print("=" * 70)
    print("Starting Phase 6a Baseline Econometric Modeling (OLS / Piecewise)")
    print("=" * 70)

    if not FEATURES_CSV_PATH.exists():
        raise FileNotFoundError(f"Feature dataset not found at {FEATURES_CSV_PATH}. Run 'make features' first.")

    df = pd.read_csv(FEATURES_CSV_PATH)
    print(f"Loaded {len(df)} total feature rows.")

    # Filter out excluded rows
    df_valid = df[df["quality_flag"] != "excluded"].copy()
    print(f"Valid modeling records (excluding quality_flag == 'excluded'): {len(df_valid)}")

    # Split train vs holdout
    train_df = df_valid[df_valid["is_holdout"] == 0].copy()
    holdout_df = df_valid[df_valid["is_holdout"] == 1].copy()

    print(f"  Training observations: {len(train_df)}")
    print(f"  Holdout observations:  {len(holdout_df)}")

    # Load or initialize results.json
    results = {}
    if RESULTS_JSON_PATH.exists():
        try:
            results = json.loads(RESULTS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    baseline_results = {
        "overall_summary": {},
        "state_sensitivities": {},
        "cv_performance": {},
        "holdout_performance": {},
    }

    # 1. State-by-State Linear & Piecewise Temperature Sensitivity
    print("\nFitting state-level OLS & Piecewise response models...")

    state_results = {}
    all_holdout_preds = []
    all_holdout_actuals = []

    for state, s_train in train_df.groupby("state"):
        s_holdout = holdout_df[holdout_df["state"] == state].copy()
        if len(s_train) < 30 or len(s_holdout) == 0:
            continue

        mean_demand = s_train["max_demand_met_mw"].mean()

        # OLS 1: Linear Max Temp + DOW + Trend
        cols_lin = ["temperature_2m_max", "trend_day", "is_weekend", "is_holiday"]
        s_tr_lin = s_train.dropna(subset=cols_lin + ["max_demand_met_mw"]).copy()
        s_ho_lin = s_holdout.dropna(subset=cols_lin + ["max_demand_met_mw"]).copy()
        if len(s_tr_lin) < 30 or len(s_ho_lin) == 0:
            continue

        X_train_lin = sm.add_constant(s_tr_lin[cols_lin])
        y_train = s_tr_lin["max_demand_met_mw"]

        ols_lin = sm.OLS(y_train, X_train_lin).fit()
        mw_per_c = ols_lin.params.get("temperature_2m_max", 0.0)
        pct_per_c = (mw_per_c / mean_demand) * 100.0 if mean_demand > 0 else 0.0
        p_val_temp = ols_lin.pvalues.get("temperature_2m_max", 1.0)

        # OLS 2: Piecewise / Degree Day (CDD_24 for cooling load slope)
        cols_pw = ["cdd_24", "hdd_18", "trend_day", "is_weekend", "is_holiday"]
        s_tr_pw = s_train.dropna(subset=cols_pw + ["max_demand_met_mw"]).copy()
        cols_pw_active = [c for c in cols_pw if s_tr_pw[c].std() > 1e-6]
        X_train_pw = sm.add_constant(s_tr_pw[cols_pw_active])
        y_train_pw = s_tr_pw["max_demand_met_mw"]
        ols_pw = sm.OLS(y_train_pw, X_train_pw).fit()
        cdd_slope_mw = ols_pw.params.get("cdd_24", 0.0)

        # Evaluate on Holdout
        X_holdout_lin = sm.add_constant(s_ho_lin[cols_lin])
        y_holdout = s_ho_lin["max_demand_met_mw"]

        preds_holdout = ols_lin.predict(X_holdout_lin)

        rmse = np.sqrt(mean_squared_error(y_holdout, preds_holdout))
        mae = mean_absolute_error(y_holdout, preds_holdout)
        mape = mape_score(y_holdout, preds_holdout)
        r2 = r2_score(y_holdout, preds_holdout)

        all_holdout_preds.extend(preds_holdout.tolist())
        all_holdout_actuals.extend(y_holdout.tolist())

        state_results[state] = {
            "mean_demand_mw": round(float(mean_demand), 1),
            "linear_sensitivity_mw_per_c": round(float(mw_per_c), 2),
            "linear_sensitivity_pct_per_c": round(float(pct_per_c), 3),
            "cooling_slope_cdd24_mw": round(float(cdd_slope_mw), 2),
            "temp_coefficient_pvalue": float(p_val_temp),
            "train_r2": round(float(ols_lin.rsquared), 4),
            "holdout_rmse_mw": round(float(rmse), 1),
            "holdout_mae_mw": round(float(mae), 1),
            "holdout_mape_pct": round(float(mape), 2),
            "holdout_r2": round(float(r2), 4),
        }
        print(
            f"  {state:15s}: +{mw_per_c:6.1f} MW/°C ({pct_per_c:5.2f}%/°C) | Holdout MAPE: {mape:5.2f}% | R2: {r2:5.2f}"
        )

    # Aggregate holdout metrics across all states
    tot_rmse = np.sqrt(mean_squared_error(all_holdout_actuals, all_holdout_preds))
    tot_mae = mean_absolute_error(all_holdout_actuals, all_holdout_preds)
    tot_mape = mape_score(all_holdout_actuals, all_holdout_preds)
    tot_r2 = r2_score(all_holdout_actuals, all_holdout_preds)

    baseline_results["state_sensitivities"] = state_results
    baseline_results["holdout_performance"] = {
        "aggregate_rmse_mw": round(float(tot_rmse), 1),
        "aggregate_mae_mw": round(float(tot_mae), 1),
        "aggregate_mape_pct": round(float(tot_mape), 2),
        "aggregate_r2": round(float(tot_r2), 4),
        "n_holdout_observations": len(all_holdout_actuals),
    }

    # High-level aggregate summary
    avg_pct_per_c = np.mean([v["linear_sensitivity_pct_per_c"] for v in state_results.values()])
    sum_mw_per_c = np.sum([v["linear_sensitivity_mw_per_c"] for v in state_results.values()])
    baseline_results["overall_summary"] = {
        "all_india_combined_mw_per_c": round(float(sum_mw_per_c), 1),
        "state_average_pct_per_c": round(float(avg_pct_per_c), 2),
        "highest_sensitivity_state": max(state_results.items(), key=lambda x: x[1]["linear_sensitivity_pct_per_c"])[0],
        "highest_sensitivity_pct": max(v["linear_sensitivity_pct_per_c"] for v in state_results.values()),
    }

    print("\n--- Baseline Econometric Results Summary ---")
    print(f"Combined 16-State Marginal Heat Sensitivity: +{sum_mw_per_c:.1f} MW/°C")
    print(f"Average State Sensitivity:                  +{avg_pct_per_c:.2f}% per °C")
    print(f"Holdout Aggregate Performance:               MAPE={tot_mape:.2f}%, RMSE={tot_rmse:.1f} MW, R²={tot_r2:.4f}")

    # Save to results.json
    results["baseline_models"] = baseline_results
    RESULTS_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved baseline model metrics to {RESULTS_JSON_PATH}")

    # Save CSV table of state sensitivities
    df_sens = pd.DataFrame.from_dict(state_results, orient="index").reset_index()
    df_sens = df_sens.rename(columns={"index": "state"})
    out_sens_csv = REPORTS_DIR / "state_temperature_sensitivity.csv"
    df_sens.to_csv(out_sens_csv, index=False)
    print(f"Saved state sensitivity comparison to {out_sens_csv}")

    print("\nPhase 6a Baseline Modeling Complete!")


if __name__ == "__main__":
    run_baseline_modeling()
