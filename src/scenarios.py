"""
Climate Warming Counterfactual Scenarios (Phase 6d).
Simulates electrical grid peak load impacts under +1°C and +2°C climate warming:
- Baseline FY 2024-25 weather trajectory.
- Counterfactual +1.0°C and +2.0°C uniform daily warming shifts.
- Dynamic recalculation of non-linear degree days (CDD), thermal inertia lags, and Heat Index.
- Predicts state-by-state peak demand surge and system-wide simultaneous stress.
- Saves results to reports/warming_scenarios.csv and updates reports/results.json.
"""

import json
import pathlib
import sys

import joblib
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.features import calculate_heat_index

CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

FEATURES_CSV_PATH = ROOT / "data" / "processed" / "features.csv"
RESULTS_JSON_PATH = ROOT / "reports" / "results.json"
MODELS_DIR = ROOT / "models"
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


def simulate_warming():
    print("=" * 70)
    print("Starting Phase 6d Climate Warming Scenario Simulations (+1°C and +2°C)")
    print("=" * 70)

    point_model_path = MODELS_DIR / "lgbm_meteo_point.joblib"
    if not point_model_path.exists():
        raise FileNotFoundError(f"Trained model not found at {point_model_path}. Run 'make model' first.")

    model = joblib.load(point_model_path)
    df = pd.read_csv(FEATURES_CSV_PATH)

    # We simulate scenarios on FY 2024-25 (2024-04-01 to 2025-03-31)
    eval_df = df[df["date"] >= "2024-04-01"].copy().sort_values(["state", "date"]).reset_index(drop=True)
    print(f"Simulating counterfactual scenarios on {len(eval_df)} state-day observations (FY 2024-25).")

    # Baseline Prediction
    X_base = eval_df[FEATURE_COLS + ["state"]].copy()
    X_base["state"] = X_base["state"].astype("category")
    eval_df["pred_baseline_mw"] = model.predict(X_base)

    # Scenarios +1C and +2C
    scenarios_shifts = [1.0, 2.0]
    scenario_summaries = {}

    for delta_t in scenarios_shifts:
        tag = f"plus_{int(delta_t)}c"
        print(f"\nEvaluating Scenario +{delta_t:.1f}°C...")

        state_dfs = []
        for state, grp in eval_df.groupby("state"):
            g = grp.copy().sort_values("date")

            # Apply warming shift
            g["temperature_2m_max"] += delta_t
            g["temperature_2m_min"] += delta_t
            g["temperature_2m_mean"] += delta_t
            g["apparent_temperature_max"] += delta_t

            # Recalculate derived features
            g["cdd_18"] = (g["temperature_2m_mean"] - 18.0).clip(lower=0.0)
            g["cdd_24"] = (g["temperature_2m_mean"] - 24.0).clip(lower=0.0)
            g["hdd_18"] = (18.0 - g["temperature_2m_mean"]).clip(lower=0.0)
            g["temp_max_sq"] = g["temperature_2m_max"] ** 2

            g["heat_index"] = [
                calculate_heat_index(t, rh) for t, rh in zip(g["temperature_2m_max"], g["relative_humidity_2m_mean"])
            ]

            g["temp_max_lag1"] = g["temperature_2m_max"].shift(1).bfill()
            g["temp_max_lag2"] = g["temperature_2m_max"].shift(2).bfill()
            g["temp_max_lag3"] = g["temperature_2m_max"].shift(3).bfill()

            g["temp_max_roll3"] = g["temperature_2m_max"].rolling(window=3, min_periods=1).mean()
            g["temp_max_roll7"] = g["temperature_2m_max"].rolling(window=7, min_periods=1).mean()

            state_dfs.append(g)

        scen_df = pd.concat(state_dfs, ignore_index=True)
        X_scen = scen_df[FEATURE_COLS + ["state"]].copy()
        X_scen["state"] = X_scen["state"].astype("category")

        preds_scen = model.predict(X_scen)
        eval_df[f"pred_{tag}_mw"] = preds_scen
        eval_df[f"surge_{tag}_mw"] = eval_df[f"pred_{tag}_mw"] - eval_df["pred_baseline_mw"]
        eval_df[f"surge_{tag}_pct"] = (eval_df[f"surge_{tag}_mw"] / eval_df["pred_baseline_mw"]) * 100.0

        # State-level summary
        state_surge = {}
        for s, grp in eval_df.groupby("state"):
            base_peak = grp["pred_baseline_mw"].max()
            scen_peak = grp[f"pred_{tag}_mw"].max()
            mean_surge = grp[f"surge_{tag}_mw"].mean()
            state_surge[s] = {
                "baseline_peak_mw": round(float(base_peak), 1),
                "scenario_peak_mw": round(float(scen_peak), 1),
                "peak_increment_mw": round(float(scen_peak - base_peak), 1),
                "mean_daily_surge_mw": round(float(mean_surge), 1),
                "mean_surge_pct": round(float(grp[f"surge_{tag}_pct"].mean()), 2),
            }

        # System-level coincident peak stress
        date_coincident_base = eval_df.groupby("date")["pred_baseline_mw"].sum()
        date_coincident_scen = eval_df.groupby("date")[f"pred_{tag}_mw"].sum()
        coincident_base_peak = date_coincident_base.max()
        coincident_scen_peak = date_coincident_scen.max()
        coincident_surge_mw = coincident_scen_peak - coincident_base_peak

        scenario_summaries[tag] = {
            "temperature_shift_c": delta_t,
            "all_india_coincident_baseline_peak_mw": round(float(coincident_base_peak), 1),
            "all_india_coincident_scenario_peak_mw": round(float(coincident_scen_peak), 1),
            "all_india_coincident_surge_mw": round(float(coincident_surge_mw), 1),
            "all_india_coincident_surge_pct": round(float((coincident_surge_mw / coincident_base_peak) * 100.0), 2),
            "state_surges": state_surge,
        }
        print(f"  System-wide 16-State Coincident Peak under +{delta_t:.1f}°C:")
        print(f"    Baseline Peak: {coincident_base_peak:,.1f} MW  -->  Scenario Peak: {coincident_scen_peak:,.1f} MW")
        print(
            f"    Simultaneous Surge: +{coincident_surge_mw:,.1f} MW (+{(coincident_surge_mw / coincident_base_peak) * 100.0:.2f}%)"
        )

    # Export Scenario Daily CSV
    out_scen_csv = REPORTS_DIR / "warming_scenarios.csv"
    export_cols = [
        "date",
        "state",
        "pred_baseline_mw",
        "pred_plus_1c_mw",
        "surge_plus_1c_mw",
        "surge_plus_1c_pct",
        "pred_plus_2c_mw",
        "surge_plus_2c_mw",
        "surge_plus_2c_pct",
    ]
    eval_df[export_cols].to_csv(out_scen_csv, index=False)
    print(f"\nSaved daily scenario projections to {out_scen_csv}")

    # Update results.json
    results = {}
    if RESULTS_JSON_PATH.exists():
        try:
            results = json.loads(RESULTS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    results["warming_scenarios"] = scenario_summaries
    RESULTS_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Updated results in {RESULTS_JSON_PATH}")

    print("\nPhase 6d Climate Warming Scenarios Complete!")


if __name__ == "__main__":
    simulate_warming()
