"""
Quantile Regression & SHAP Explainability Pipeline (Phase 6c).
Implements probabilistic peak load modeling and interpretability:
- LightGBM Quantile models (alpha = 0.10, 0.50, 0.90) for peak demand uncertainty bands.
- Calibration and empirical coverage evaluation on Holdout period (80% interval).
- SHAP (SHapley Additive exPlanations) TreeExplainer analysis:
  - Global feature contribution (mean |SHAP| value).
  - Heatwave attribution and non-linear temperature response attribution.
- Serializes evaluation to reports/results.json and reports/shap_importance.csv.
"""

import json
import pathlib

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
import yaml

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


def pinball_loss(y_true, y_pred, alpha):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    diff = y_true - y_pred
    return np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff))


def run_quantile_and_shap():
    print("=" * 70)
    print("Starting Phase 6c Quantile Regression & SHAP Analysis")
    print("=" * 70)

    if not FEATURES_CSV_PATH.exists():
        raise FileNotFoundError(f"Feature dataset not found at {FEATURES_CSV_PATH}. Run 'make features' first.")

    df = pd.read_csv(FEATURES_CSV_PATH)
    df_valid = df[df["quality_flag"] != "excluded"].dropna(subset=["max_demand_met_mw"]).copy()

    train_df = df_valid[df_valid["is_holdout"] == 0].copy()
    holdout_df = df_valid[df_valid["is_holdout"] == 1].copy()

    X_train = train_df[FEATURE_COLS + ["state"]].copy()
    X_train["state"] = X_train["state"].astype("category")
    y_train = train_df["max_demand_met_mw"]

    X_holdout = holdout_df[FEATURE_COLS + ["state"]].copy()
    X_holdout["state"] = X_holdout["state"].astype("category")
    y_holdout = holdout_df["max_demand_met_mw"]

    # 1. Train Quantile Models (alpha = 0.10, 0.50, 0.90)
    print("\nTraining LightGBM Quantile Regressors (alpha = 0.10, 0.50, 0.90)...")
    alphas = [0.10, 0.50, 0.90]
    quantile_models = {}
    holdout_q_preds = {}
    pinball_losses = {}

    for a in alphas:
        print(f"  Fitting alpha={a:.2f}...")
        q_model = lgb.LGBMRegressor(
            objective="quantile",
            alpha=a,
            n_estimators=400,
            learning_rate=0.03,
            num_leaves=31,
            random_state=42,
            verbose=-1,
        )
        q_model.fit(X_train, y_train)
        quantile_models[a] = q_model
        joblib.dump(q_model, MODELS_DIR / f"lgbm_quantile_{int(a*100)}.joblib")

        preds = q_model.predict(X_holdout)
        holdout_q_preds[a] = preds
        loss = pinball_loss(y_holdout, preds, a)
        pinball_losses[f"pinball_loss_alpha_{int(a*100)}"] = round(float(loss), 2)
        print(f"    Holdout Pinball Loss (alpha={a:.2f}): {loss:.2f} MW")

    # Evaluate 80% Uncertainty Band Coverage on Holdout
    y_arr = np.array(y_holdout)
    lower = np.array(holdout_q_preds[0.10])
    upper = np.array(holdout_q_preds[0.90])
    inside = (y_arr >= lower) & (y_arr <= upper)
    empirical_coverage = np.mean(inside) * 100.0
    mean_interval_width = np.mean(upper - lower)

    print(f"\nEmpirical 80% Prediction Interval Coverage on Holdout: {empirical_coverage:.2f}% (Expected: ~80.0%)")
    print(f"Mean Prediction Interval Width:                     {mean_interval_width:.1f} MW")

    # Save holdout quantile predictions
    holdout_out_df = holdout_df[["date", "state", "max_demand_met_mw", "temperature_2m_max"]].copy()
    holdout_out_df["q10_lower_mw"] = lower
    holdout_out_df["q50_median_mw"] = holdout_q_preds[0.50]
    holdout_out_df["q90_upper_mw"] = upper
    holdout_out_df.to_csv(REPORTS_DIR / "holdout_quantile_forecasts.csv", index=False)
    print("Saved holdout quantile predictions to reports/holdout_quantile_forecasts.csv")

    # 2. SHAP Explainability on Point Meteorological Model
    print("\nComputing SHAP values on Holdout sample using TreeExplainer...")
    point_model_path = MODELS_DIR / "lgbm_meteo_point.joblib"
    if not point_model_path.exists():
        raise FileNotFoundError(f"Trained point model not found at {point_model_path}. Run 'make model' first.")

    point_model = joblib.load(point_model_path)
    explainer = shap.TreeExplainer(point_model)

    # Sample holdout for fast and comprehensive SHAP evaluation (e.g. 600 records)
    sample_size = min(600, len(X_holdout))
    shap_sample = X_holdout.sample(n=sample_size, random_state=42)
    shap_values = explainer.shap_values(shap_sample)

    # Compute mean absolute SHAP value per feature
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_importance = pd.DataFrame({"feature": shap_sample.columns, "mean_abs_shap_mw": mean_abs_shap}).sort_values(
        "mean_abs_shap_mw", ascending=False
    )

    shap_importance.to_csv(REPORTS_DIR / "shap_importance.csv", index=False)
    print("Saved SHAP feature importance to reports/shap_importance.csv")

    top_shap = shap_importance.head(10).to_dict("records")
    for r in top_shap[:5]:
        print(f"  Feature '{r['feature']}': Impact = {r['mean_abs_shap_mw']:.1f} MW")

    # 3. Update results.json
    results = {}
    if RESULTS_JSON_PATH.exists():
        try:
            results = json.loads(RESULTS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    results["quantile_and_shap"] = {
        "pinball_losses": pinball_losses,
        "empirical_80pct_coverage": round(float(empirical_coverage), 2),
        "mean_interval_width_mw": round(float(mean_interval_width), 1),
        "top_shap_features": top_shap,
    }

    RESULTS_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nUpdated results in {RESULTS_JSON_PATH}")

    print("\nPhase 6c Quantile & SHAP Pipeline Complete!")


if __name__ == "__main__":
    run_quantile_and_shap()
