"""
Compile Web Dashboard Data Package.
Exports structured JSON payload for the frontend web application in web/data.json.
"""

import json
import pathlib

import numpy as np
import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).parent.parent.resolve()
WEB_DIR = ROOT / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = ROOT / "config.yaml"
cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

RESULTS_PATH = ROOT / "reports" / "results.json"
SENSITIVITY_PATH = ROOT / "reports" / "state_temperature_sensitivity.csv"
SCENARIOS_PATH = ROOT / "reports" / "warming_scenarios.csv"
SHAP_PATH = ROOT / "reports" / "shap_importance.csv"
HOLDOUT_PATH = ROOT / "reports" / "holdout_quantile_forecasts.csv"
FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"


def export_web_data():
    print("Compiling web data package...")

    # 1. Base Results & Metadata
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    states_cfg = cfg["states"]

    # 2. State Sensitivity Table
    df_sens = pd.read_csv(SENSITIVITY_PATH)
    states_list = []
    for _, r in df_sens.iterrows():
        s_name = r["state"]
        c_info = states_cfg.get(s_name, {})
        states_list.append(
            {
                "state": s_name,
                "code": c_info.get("code", ""),
                "region": c_info.get("region", ""),
                "city": c_info.get("city", ""),
                "lat": c_info.get("lat", 0.0),
                "lon": c_info.get("lon", 0.0),
                "mean_demand_mw": float(r["mean_demand_mw"]),
                "mw_per_c": float(r["linear_sensitivity_mw_per_c"]),
                "pct_per_c": float(r["linear_sensitivity_pct_per_c"]),
                "cdd_slope_mw": float(r.get("cooling_slope_cdd24_mw", 0.0)),
                "holdout_mape": float(r["holdout_mape_pct"]),
                "holdout_r2": float(r["holdout_r2"]),
            }
        )

    # Sort states by percentage sensitivity descending
    states_list.sort(key=lambda x: x["pct_per_c"], reverse=True)

    # 3. Summer 2024 Heatwave Time Series (Holdout May-June 2024)
    df_holdout = pd.read_csv(HOLDOUT_PATH)
    df_heatwave = df_holdout[(df_holdout["date"] >= "2024-05-01") & (df_holdout["date"] <= "2024-06-30")].copy()

    # Aggregate coincident sum across all states
    heatwave_timeline = []
    for dt, grp in df_heatwave.groupby("date"):
        heatwave_timeline.append(
            {
                "date": dt,
                "actual_mw": round(float(grp["max_demand_met_mw"].sum()), 1),
                "q50_pred_mw": round(float(grp["q50_median_mw"].sum()), 1),
                "q10_lower_mw": round(float(grp["q10_lower_mw"].sum()), 1),
                "q90_upper_mw": round(float(grp["q90_upper_mw"].sum()), 1),
                "mean_tmax_c": round(float(grp["temperature_2m_max"].mean()), 1),
            }
        )
    heatwave_timeline.sort(key=lambda x: x["date"])

    # 4. State Response Curve Samples
    df_feat = pd.read_csv(FEATURES_PATH)
    df_feat_valid = df_feat[df_feat["quality_flag"] != "excluded"].dropna(
        subset=["max_demand_met_mw", "temperature_2m_max"]
    )

    state_curves = {}
    for s_name in states_cfg.keys():
        s_data = df_feat_valid[df_feat_valid["state"] == s_name]
        if len(s_data) < 20:
            continue

        # Sample up to 120 points for smooth charting
        sample_pts = s_data.sample(n=min(120, len(s_data)), random_state=42)
        points = [
            {"t": round(float(r["temperature_2m_max"]), 1), "mw": round(float(r["max_demand_met_mw"]), 1)}
            for _, r in sample_pts.iterrows()
        ]

        # Fit polynomial
        z = np.polyfit(s_data["temperature_2m_max"], s_data["max_demand_met_mw"], 2)
        t_min = float(s_data["temperature_2m_max"].min())
        t_max = float(s_data["temperature_2m_max"].max())
        t_grid = np.linspace(t_min, t_max, 30)
        fit_line = [{"t": round(float(t), 1), "mw": round(float(z[0] * t**2 + z[1] * t + z[2]), 1)} for t in t_grid]

        state_curves[s_name] = {
            "points": points,
            "fit_line": fit_line,
            "t_min": round(t_min, 1),
            "t_max": round(t_max, 1),
        }

    # 5. SHAP Drivers
    df_shap = pd.read_csv(SHAP_PATH).head(8)
    shap_drivers = [
        {"feature": r["feature"], "impact_mw": round(float(r["mean_abs_shap_mw"]), 1)} for _, r in df_shap.iterrows()
    ]

    # 6. Scenarios Summary
    scen_data = results.get("warming_scenarios", {})

    payload = {
        "summary": results.get("baseline_models", {}).get("overall_summary", {}),
        "holdout_metrics": {
            "meteo": results.get("gbm_point_model", {}).get("holdout_pure_meteorological", {}),
            "operational": results.get("gbm_point_model", {}).get("holdout_operational_autoregressive", {}),
        },
        "states": states_list,
        "heatwave_timeline": heatwave_timeline,
        "state_curves": state_curves,
        "shap_drivers": shap_drivers,
        "scenarios": scen_data,
    }

    out_json = WEB_DIR / "data.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported web package: {out_json} ({out_json.stat().st_size:,} bytes)")


if __name__ == "__main__":
    export_web_data()
