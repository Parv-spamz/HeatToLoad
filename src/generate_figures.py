"""
Automated Figure Generation Pipeline.
Generates publication-quality, high-resolution figures in reports/figures/:
- Fig 1: State Temperature Sensitivity League Table (MW/C and %/C)
- Fig 2: Non-linear Temperature Response Curves (Hockey-stick inflection above 28C)
- Fig 3: Peak Summer 2024 Heatwave Tracking (Actual vs Predicted Load + Temperature)
- Fig 4: SHAP Feature Importance Attribution
- Fig 5: Coincident Grid Stress under +1C and +2C Climate Warming Counterfactuals
"""

import pathlib

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent.resolve()
FIGURES_DIR = ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_PATH = ROOT / "data" / "processed" / "features.csv"
SENSITIVITY_PATH = ROOT / "reports" / "state_temperature_sensitivity.csv"
SCENARIOS_PATH = ROOT / "reports" / "warming_scenarios.csv"
SHAP_PATH = ROOT / "reports" / "shap_importance.csv"
HOLDOUT_PATH = ROOT / "reports" / "holdout_quantile_forecasts.csv"
RESULTS_PATH = ROOT / "reports" / "results.json"

# Modern styling palette
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.labelsize"] = 11


def plot_fig1_sensitivity():
    print("Generating Figure 1: State Temperature Sensitivity Comparison...")
    if not SENSITIVITY_PATH.exists():
        print(f"Skipping Fig 1: {SENSITIVITY_PATH} missing")
        return

    df = pd.read_csv(SENSITIVITY_PATH).sort_values("linear_sensitivity_pct_per_c", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8), sharey=True)

    # Panel A: Percentage Sensitivity
    colors_pct = [
        "#e74c3c" if v > 2.0 else "#3498db" if v > 0 else "#95a5a6" for v in df["linear_sensitivity_pct_per_c"]
    ]
    bars1 = ax1.barh(df["state"], df["linear_sensitivity_pct_per_c"], color=colors_pct, edgecolor="black", alpha=0.85)
    ax1.set_xlabel("Sensitivity (% increase in peak load per °C)")
    ax1.set_title("A. State Thermal Responsiveness (% / °C)", fontweight="bold")
    ax1.axvline(0, color="black", linestyle="--", linewidth=0.8)
    for bar in bars1:
        w = bar.get_width()
        x_pos = w + 0.08 if w >= 0 else w - 0.4
        ax1.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{w:+.2f}%",
            va="center",
            ha="left" if w >= 0 else "right",
            fontsize=9,
        )

    # Panel B: Absolute MW Sensitivity
    colors_mw = ["#2ecc71" if v > 200 else "#f39c12" if v > 0 else "#95a5a6" for v in df["linear_sensitivity_mw_per_c"]]
    bars2 = ax2.barh(df["state"], df["linear_sensitivity_mw_per_c"], color=colors_mw, edgecolor="black", alpha=0.85)
    ax2.set_xlabel("Marginal Demand Added (MW per °C)")
    ax2.set_title("B. Absolute Megawatt Additions (MW / °C)", fontweight="bold")
    ax2.axvline(0, color="black", linestyle="--", linewidth=0.8)
    for bar in bars2:
        w = bar.get_width()
        x_pos = w + 8 if w >= 0 else w - 30
        ax2.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{w:+.1f}",
            va="center",
            ha="left" if w >= 0 else "right",
            fontsize=9,
        )

    plt.suptitle(
        "Temperature Sensitivity of Peak Electricity Demand Across 16 Indian States",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig1_state_sensitivity_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig2_response_curves():
    print("Generating Figure 2: Non-linear Temperature Response Curves...")
    if not FEATURES_PATH.exists():
        print(f"Skipping Fig 2: {FEATURES_PATH} missing")
        return

    df = pd.read_csv(FEATURES_PATH)
    df_clean = df[df["quality_flag"] != "excluded"].dropna(subset=["max_demand_met_mw", "temperature_2m_max"])

    # Pick 6 diverse high-load states
    target_states = ["Maharashtra", "Uttar Pradesh", "Karnataka", "Delhi", "Gujarat", "Tamil Nadu"]
    df_subset = df_clean[df_clean["state"].isin(target_states)]

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharey=False)
    axes = axes.flatten()

    for idx, state in enumerate(target_states):
        ax = axes[idx]
        s_data = df_subset[df_subset["state"] == state]

        # Scatter actual observations
        ax.scatter(
            s_data["temperature_2m_max"],
            s_data["max_demand_met_mw"],
            alpha=0.35,
            s=20,
            color="#2980b9",
            edgecolors="none",
            label="Daily Observations",
        )

        # Polynomial fit line
        z = np.polyfit(s_data["temperature_2m_max"], s_data["max_demand_met_mw"], 2)
        p = np.poly1d(z)
        t_range = np.linspace(s_data["temperature_2m_max"].min(), s_data["temperature_2m_max"].max(), 100)
        ax.plot(t_range, p(t_range), color="#c0392b", linewidth=2.5, label="Polynomial Response")

        # Threshold line at 28C balance point
        ax.axvline(28.0, color="#7f8c8d", linestyle=":", linewidth=1.2, label="28°C Cooling Balance")

        ax.set_title(f"{state}", fontweight="bold", fontsize=12)
        ax.set_xlabel("Daily Max Temperature (°C)")
        ax.set_ylabel("Peak Demand (MW)")
        if idx == 0:
            ax.legend(loc="upper left", frameon=True, fontsize=8)

    plt.suptitle(
        "Non-linear Load-Temperature Response Curves Across Selected Major States",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig2_temperature_response_curves.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig3_heatwave_tracking():
    print("Generating Figure 3: Summer 2024 Heatwave Tracking...")
    if not HOLDOUT_PATH.exists():
        print(f"Skipping Fig 3: {HOLDOUT_PATH} missing")
        return

    df = pd.read_csv(HOLDOUT_PATH)
    # Filter to Northern heatwave corridor (Delhi + UP) during May-June 2024
    df_heatwave = df[(df["date"] >= "2024-05-01") & (df["date"] <= "2024-06-30")]

    # Coincident sum across Delhi and UP
    agg = (
        df_heatwave.groupby("date")
        .agg(
            {
                "max_demand_met_mw": "sum",
                "q50_median_mw": "sum",
                "q10_lower_mw": "sum",
                "q90_upper_mw": "sum",
                "temperature_2m_max": "mean",
            }
        )
        .reset_index()
    )

    agg["date_dt"] = pd.to_datetime(agg["date"])

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # Demand curve (left axis)
    ax1.plot(
        agg["date_dt"],
        agg["max_demand_met_mw"],
        color="#2c3e50",
        linewidth=2.5,
        marker="o",
        markersize=4,
        label="Actual Peak Demand (SCADA)",
    )
    ax1.plot(
        agg["date_dt"],
        agg["q50_median_mw"],
        color="#e74c3c",
        linewidth=2.0,
        linestyle="--",
        label="Model Median Forecast (Q50)",
    )
    ax1.fill_between(
        agg["date_dt"],
        agg["q10_lower_mw"],
        agg["q90_upper_mw"],
        color="#e74c3c",
        alpha=0.18,
        label="80% Uncertainty Band (Q10 - Q90)",
    )
    ax1.set_ylabel("Coincident Peak Demand (MW)", color="#2c3e50", fontweight="bold")
    ax1.tick_params(axis="y", labelcolor="#2c3e50")

    # Temperature curve (right axis)
    ax2 = ax1.twinx()
    ax2.plot(
        agg["date_dt"],
        agg["temperature_2m_max"],
        color="#f39c12",
        linewidth=2.0,
        linestyle="-.",
        label="Mean Daily Max Temperature (°C)",
    )
    ax2.set_ylabel("Max Temperature (°C)", color="#d35400", fontweight="bold")
    ax2.tick_params(axis="y", labelcolor="#d35400")
    ax2.grid(False)  # Avoid conflicting grid lines

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)

    plt.title(
        "Grid Demand Surge Tracking Historic May-June 2024 Indian Heatwave", fontsize=14, fontweight="bold", pad=15
    )
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig3_heatwave_2024_holdout_tracking.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig4_shap():
    print("Generating Figure 4: SHAP Feature Importance...")
    if not SHAP_PATH.exists():
        print(f"Skipping Fig 4: {SHAP_PATH} missing")
        return

    df = pd.read_csv(SHAP_PATH).head(10).sort_values("mean_abs_shap_mw", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df["feature"], df["mean_abs_shap_mw"], color="#34495e", edgecolor="black", alpha=0.85)

    ax.set_xlabel("Mean Absolute SHAP Impact on Peak Demand (MW)")
    ax.set_title(
        "Top 10 Most Influential Feature Drivers (SHAP TreeExplainer Attribution)", fontsize=13, fontweight="bold"
    )

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 30, bar.get_y() + bar.get_height() / 2, f"{w:,.1f} MW", va="center", ha="left", fontsize=9)

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig4_shap_feature_importance.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_fig5_warming_scenarios():
    print("Generating Figure 5: Coincident Peak Under Climate Warming Scenarios...")
    if not SCENARIOS_PATH.exists():
        print(f"Skipping Fig 5: {SCENARIOS_PATH} missing")
        return

    df = pd.read_csv(SCENARIOS_PATH)
    # Aggregate coincident demand across all 16 states per day
    agg = (
        df.groupby("date")
        .agg({"pred_baseline_mw": "sum", "pred_plus_1c_mw": "sum", "pred_plus_2c_mw": "sum"})
        .reset_index()
    )

    agg["date_dt"] = pd.to_datetime(agg["date"])

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(
        agg["date_dt"], agg["pred_baseline_mw"], color="#2c3e50", linewidth=1.8, label="Baseline (Observed Weather)"
    )
    ax.plot(
        agg["date_dt"],
        agg["pred_plus_1c_mw"],
        color="#e67e22",
        linewidth=2.0,
        label="Scenario +1.0°C Warming (+3,601 MW Coincident Peak)",
    )
    ax.plot(
        agg["date_dt"],
        agg["pred_plus_2c_mw"],
        color="#c0392b",
        linewidth=2.2,
        label="Scenario +2.0°C Warming (+5,841 MW Coincident Peak)",
    )

    # Fill region between baseline and +2C
    ax.fill_between(
        agg["date_dt"],
        agg["pred_baseline_mw"],
        agg["pred_plus_2c_mw"],
        color="#e74c3c",
        alpha=0.15,
        label="Warming Stress Expansion (+2.0°C)",
    )

    ax.set_ylabel("Coincident Peak Demand Across 16 States (MW)", fontweight="bold")
    ax.set_xlabel("Timeline (FY 2024-25)", fontweight="bold")
    ax.set_title(
        "Simultaneous Coincident Grid Stress Under +1°C and +2°C Climate Warming Projections",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )
    ax.legend(loc="upper right", frameon=True)

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig5_climate_warming_scenarios.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def generate_all_figures():
    print("=" * 70)
    print("Starting Automated Publication Figure Generation")
    print(f"Destination: {FIGURES_DIR}")
    print("=" * 70)

    plot_fig1_sensitivity()
    plot_fig2_response_curves()
    plot_fig3_heatwave_tracking()
    plot_fig4_shap()
    plot_fig5_warming_scenarios()

    print("\nAll 5 figures generated successfully in reports/figures/!")


if __name__ == "__main__":
    generate_all_figures()
