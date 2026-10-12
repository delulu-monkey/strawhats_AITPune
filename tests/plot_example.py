"""Generate example simulation plot for documentation."""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.sim.profile import VirtualPatient, GeneticMarkers, Lifestyle
from src.sim.simulator import simulate


def main():
    # Create an illustrative prediabetic patient
    patient = VirtualPatient(
        name="Priya_Sharma",
        age=48,
        sex="F",
        height_cm=158,
        weight_kg=72,
        hba1c=6.8,
        fasting_glucose=126,
        insulin=18,
        triglycerides=180,
        total_cholesterol=220,
        hdl=42,
        ldl=140,
        diagnoses=["prediabetes", "PCOS"],
        medications=[],
        genetic_markers=GeneticMarkers(genetic_risk_score=65),
        lifestyle=Lifestyle(
            typical_sleep_hours=6.5,
            sleep_variability_hours=0.8,
            bedtime_hour=23.5,
            steps_per_day=5000,
            resting_heart_rate=76,
        ),
        seed=42,
    )

    df, sleep_summary = simulate(patient, days=3, start_date=date(2025, 3, 10))

    # ── Plot ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.2, 1.2, 1.2]})
    fig.suptitle(
        f"Simulated Data: {patient.name}  |  HbA1c {patient.hba1c}%  |  BMI {patient.bmi}",
        fontsize=14, fontweight="bold", y=0.98,
    )

    hours = (df["time"] - df["time"].iloc[0]).dt.total_seconds() / 3600

    # --- Panel 1: Glucose + meals ---
    ax = axes[0]
    ax.plot(hours, df["libre"], color="#2563eb", linewidth=0.8, alpha=0.9, label="CGM glucose")
    ax.axhline(180, color="#ef4444", linestyle="--", linewidth=0.7, alpha=0.6, label="180 mg/dL")
    ax.axhline(70, color="#f59e0b", linestyle="--", linewidth=0.7, alpha=0.6, label="70 mg/dL")
    # Mark meals
    meal_mask = df["meal_name"] != ""
    if meal_mask.any():
        ax.scatter(
            hours[meal_mask], df.loc[meal_mask, "libre"],
            marker="v", s=60, color="#16a34a", zorder=5, label="Meals",
        )
        for _, row in df[meal_mask].iterrows():
            h = (row["time"] - df["time"].iloc[0]).total_seconds() / 3600
            ax.annotate(
                f"{row['meal_name']}\n({row['carbs']:.0f}g C)",
                xy=(h, row["libre"]),
                xytext=(0, 18), textcoords="offset points",
                fontsize=6, ha="center", color="#15803d",
                arrowprops=dict(arrowstyle="-", color="#15803d", lw=0.5),
            )
    ax.set_ylabel("Glucose (mg/dL)")
    ax.set_ylim(50, max(250, df["libre"].max() + 20))
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(alpha=0.2)

    # --- Panel 2: Sleep hypnogram ---
    ax = axes[1]
    stage_map = {"none": 0, "awake": 0.5, "rem": 1, "light": 2, "deep": 3}
    stage_num = df["sleep_stage"].map(stage_map).fillna(0)
    ax.fill_between(hours, stage_num, step="post", alpha=0.6, color="#7c3aed")
    ax.set_ylabel("Sleep stage")
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["Awake", "REM", "Light", "Deep"])
    ax.set_ylim(-0.2, 3.5)
    ax.grid(alpha=0.2)

    # --- Panel 3: Steps ---
    ax = axes[2]
    ax.bar(hours, df["steps"], width=5 / 60, color="#0d9488", alpha=0.7)
    ax.set_ylabel("Steps / 5 min")
    ax.grid(alpha=0.2)

    # --- Panel 4: HRV ---
    ax = axes[3]
    ax.plot(hours, df["hrv_rmssd"], color="#ea580c", linewidth=0.6, alpha=0.8)
    ax.set_ylabel("HRV RMSSD (ms)")
    ax.set_xlabel("Hours from start")
    ax.grid(alpha=0.2)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    os.makedirs("docs/results", exist_ok=True)
    out_path = "docs/results/sim_example_patient.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot to {out_path}")
    print(f"Mean glucose: {df['libre'].mean():.1f} mg/dL")
    print(f"Sleep summary:\n{sleep_summary.to_string(index=False)}")


if __name__ == "__main__":
    main()
