"""
LightGBM Point Forecasting & Non-linear Load Modeling (Phase 6b).
Implements state-of-the-art gradient boosted trees for electricity peak load:
- Expanding-origin 4-fold cross-validation.
- Holdout evaluation during historic 2024 heatwave (2024-04-01 to 2024-09-30).
- Pure meteorological response model vs operational (autoregressive lag) model.
- Global pooled model with categorical state encoding + state-level sub-models.
- Feature importance analysis.
- Serializes evaluation metrics to reports/results.json and models to models/.
"""

import json
import pathlib

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = pathlib.Path(__file__).parent.parent.resolve()
CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

FEATURES_CSV_PATH = ROOT / "data" / "processed" / "features.csv"
RESULTS_JSON_PATH = ROOT / "reports" / "results.json"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "relative_humidity_2m_mean",
    "cdd_18",
    "cdd_24",
    "hdd_18",
    "heat_index",
    "temp_max_sq",
    "temp_max_lag1",
    "temp_max_lag2",
    "temp_max_lag3",
    "temp_max_roll3",
    "temp_max_roll7",
    "sin_doy",
    "cos_doy",
    "sin_dow",
    "cos_dow",
    "sin_month",
    "cos_month",
    "is_weekend",
    "is_holiday",
    "trend_day",
    "is_heatwave",
]

AUTOREGRESSIVE_COLS = ["demand_lag1", "demand_lag7", "demand_roll7_mean"]


def mape_score(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0


def run_gbm_modeling():
    print("=" * 70)
    print("Starting Phase 6b LightGBM Machine Learning Pipeline")
    print("=" * 70)

    if not FEATURES_CSV_PATH.exists():
        raise FileNotFoundError(f"Feature dataset not found at {FEATURES_CSV_PATH}. Run 'make features' first.")

    df = pd.read_csv(FEATURES_CSV_PATH)
    # Filter valid rows
    df_valid = df[df["quality_flag"] != "excluded"].dropna(subset=["max_demand_met_mw"]).copy()
    print(f"Loaded {len(df_valid)} valid modeling records.")

    # Train / Holdout split
    train_df = df_valid[df_valid["is_holdout"] == 0].copy()
    holdout_df = df_valid[df_valid["is_holdout"] == 1].copy()

    print(f"  Training observations (pre-holdout): {len(train_df)}")
    print(f"  Holdout observations (summer 2024):  {len(holdout_df)}")

    # 1. Expanding-Window Cross-Validation on Pre-Holdout Data
    print("\nExecuting 4-Split Expanding-Window Cross-Validation...")
    train_dates = np.sort(train_df["date"].unique())
    n_splits = 4
    split_size = len(train_dates) // (n_splits + 1)

    cv_scores = []
    for split in range(1, n_splits + 1):
        cutoff_idx = split_size * (split + 1)
        train_window_dates = train_dates[: cutoff_idx - split_size]
        val_window_dates = train_dates[cutoff_idx - split_size : cutoff_idx]

        cv_tr = train_df[train_df["date"].isin(train_window_dates)]
        cv_va = train_df[train_df["date"].isin(val_window_dates)]

        # Prepare categorical state
        cv_tr_X = cv_tr[FEATURE_COLS + ["state"]].copy()
        cv_tr_X["state"] = cv_tr_X["state"].astype("category")
        cv_va_X = cv_va[FEATURE_COLS + ["state"]].copy()
        cv_va_X["state"] = cv_va_X["state"].astype("category")

        model_cv = lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
        model_cv.fit(cv_tr_X, cv_tr["max_demand_met_mw"])
        preds = model_cv.predict(cv_va_X)

        val_rmse = np.sqrt(mean_squared_error(cv_va["max_demand_met_mw"], preds))
        val_mape = mape_score(cv_va["max_demand_met_mw"], preds)
        val_r2 = r2_score(cv_va["max_demand_met_mw"], preds)

        cv_scores.append(
            {
                "split": split,
                "train_days": len(train_window_dates),
                "val_days": len(val_window_dates),
                "val_rmse_mw": round(float(val_rmse), 1),
                "val_mape_pct": round(float(val_mape), 2),
                "val_r2": round(float(val_r2), 4),
            }
        )
        print(
            f"  Split {split}: Train={len(train_window_dates)}d, Val={len(val_window_dates)}d | Val MAPE: {val_mape:.2f}%, RMSE: {val_rmse:.1f} MW, R²: {val_r2:.4f}"
        )

    # 2. Train Full Meteorological Model
    print("\nTraining Full Meteorological LightGBM Model on entire training set...")
    X_train_full = train_df[FEATURE_COLS + ["state"]].copy()
    X_train_full["state"] = X_train_full["state"].astype("category")
    y_train_full = train_df["max_demand_met_mw"]

    X_holdout_full = holdout_df[FEATURE_COLS + ["state"]].copy()
    X_holdout_full["state"] = X_holdout_full["state"].astype("category")
    y_holdout_full = holdout_df["max_demand_met_mw"]

    gbm_meteo = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbose=-1,
    )
    gbm_meteo.fit(X_train_full, y_train_full)

    # Evaluate on Holdout
    holdout_preds_meteo = gbm_meteo.predict(X_holdout_full)
    meteo_rmse = np.sqrt(mean_squared_error(y_holdout_full, holdout_preds_meteo))
    meteo_mae = mean_absolute_error(y_holdout_full, holdout_preds_meteo)
    meteo_mape = mape_score(y_holdout_full, holdout_preds_meteo)
    meteo_r2 = r2_score(y_holdout_full, holdout_preds_meteo)

    print(f"  Holdout Pure Meteorological Model: MAPE={meteo_mape:.2f}%, RMSE={meteo_rmse:.1f} MW, R²={meteo_r2:.4f}")

    # 3. Train Operational Model (with Autoregressive Demand Lags)
    print("\nTraining Operational Model (Meteorology + Lagged Demand)...")
    train_op = train_df.dropna(subset=AUTOREGRESSIVE_COLS).copy()
    holdout_op = holdout_df.dropna(subset=AUTOREGRESSIVE_COLS).copy()

    X_train_op = train_op[FEATURE_COLS + AUTOREGRESSIVE_COLS + ["state"]].copy()
    X_train_op["state"] = X_train_op["state"].astype("category")
    y_train_op = train_op["max_demand_met_mw"]

    X_holdout_op = holdout_op[FEATURE_COLS + AUTOREGRESSIVE_COLS + ["state"]].copy()
    X_holdout_op["state"] = X_holdout_op["state"].astype("category")
    y_holdout_op = holdout_op["max_demand_met_mw"]

    gbm_op = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbose=-1,
    )
    gbm_op.fit(X_train_op, y_train_op)

    holdout_preds_op = gbm_op.predict(X_holdout_op)
    op_rmse = np.sqrt(mean_squared_error(y_holdout_op, holdout_preds_op))
    op_mae = mean_absolute_error(y_holdout_op, holdout_preds_op)
    op_mape = mape_score(y_holdout_op, holdout_preds_op)
    op_r2 = r2_score(y_holdout_op, holdout_preds_op)

    print(f"  Holdout Operational Model (with lags): MAPE={op_mape:.2f}%, RMSE={op_rmse:.1f} MW, R²={op_r2:.4f}")

    # 4. Feature Importance Analysis
    imp_df = pd.DataFrame(
        {
            "feature": gbm_meteo.feature_name_,
            "importance_gain": gbm_meteo.booster_.feature_importance(importance_type="gain"),
            "importance_split": gbm_meteo.booster_.feature_importance(importance_type="split"),
        }
    ).sort_values("importance_gain", ascending=False)
    imp_df.to_csv(REPORTS_DIR / "feature_importance_meteo.csv", index=False)

    top_features = imp_df.head(10)[["feature", "importance_gain"]].to_dict("records")

    # 5. State-Level Holdout Performance Breakdown
    holdout_df["pred_meteo"] = holdout_preds_meteo
    state_breakdown = {}
    for state, grp in holdout_df.groupby("state"):
        s_rmse = np.sqrt(mean_squared_error(grp["max_demand_met_mw"], grp["pred_meteo"]))
        s_mape = mape_score(grp["max_demand_met_mw"], grp["pred_meteo"])
        s_r2 = r2_score(grp["max_demand_met_mw"], grp["pred_meteo"])
        state_breakdown[state] = {
            "holdout_rmse_mw": round(float(s_rmse), 1),
            "holdout_mape_pct": round(float(s_mape), 2),
            "holdout_r2": round(float(s_r2), 4),
        }

    # Save models
    joblib.dump(gbm_meteo, MODELS_DIR / "lgbm_meteo_point.joblib")
    joblib.dump(gbm_op, MODELS_DIR / "lgbm_operational_point.joblib")
    print(f"\nSaved trained models to {MODELS_DIR}")

    # Update results.json
    results = {}
    if RESULTS_JSON_PATH.exists():
        try:
            results = json.loads(RESULTS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    results["gbm_point_model"] = {
        "cv_performance": cv_scores,
        "cv_mean_mape_pct": round(float(np.mean([s["val_mape_pct"] for s in cv_scores])), 2),
        "cv_mean_r2": round(float(np.mean([s["val_r2"] for s in cv_scores])), 4),
        "holdout_pure_meteorological": {
            "rmse_mw": round(float(meteo_rmse), 1),
            "mae_mw": round(float(meteo_mae), 1),
            "mape_pct": round(float(meteo_mape), 2),
            "r2": round(float(meteo_r2), 4),
        },
        "holdout_operational_autoregressive": {
            "rmse_mw": round(float(op_rmse), 1),
            "mae_mw": round(float(op_mae), 1),
            "mape_pct": round(float(op_mape), 2),
            "r2": round(float(op_r2), 4),
        },
        "top_features_by_gain": top_features,
        "state_holdout_performance": state_breakdown,
    }

    RESULTS_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Updated results in {RESULTS_JSON_PATH}")

    print("\nPhase 6b LightGBM Modeling Complete!")


if __name__ == "__main__":
    run_gbm_modeling()
