import joblib
import numpy as np
import pandas as pd
import shap
import streamlit as st
import matplotlib.pyplot as plt
from datetime import timedelta

THR, WATCH, HIGH, MEAL_ERR = 180, 0.75, 0.91, 30   # alert cutoffs come from held-out T2D results
CAPS = {"carbs": 250, "protein": 150, "fat": 150, "fiber": 60}
st.set_page_config(page_title="T2D Digital Twin", layout="wide")


@st.cache_resource
def load_models():
    risk = joblib.load("models/xgb_spike_model.pkl")
    meal = joblib.load("models/meal_response_rf.pkl")
    return risk, meal, shap.TreeExplainer(risk["model"])


@st.cache_data
def load_data():
    feats = pd.read_csv("data/processed/features.csv.gz", parse_dates=["time"])
    raw = pd.read_csv("data/processed/cgmacros_all.csv.gz", parse_dates=["time"],
                      usecols=["subject", "time", "carbs"])
    return feats, raw[raw.carbs.notna()], pd.read_csv("data/indian_meals.csv")


NAMES = {
    "glu_now": ("Current glucose", "{:.0f} mg/dL"),
    "glu_chg_15m": ("Glucose change, last 15 min", "{:+.0f} mg/dL"),
    "glu_chg_30m": ("Glucose change, last 30 min", "{:+.0f} mg/dL"),
    "glu_chg_60m": ("Glucose change, last hour", "{:+.0f} mg/dL"),
    "glu_mean_60m": ("Average glucose, last hour", "{:.0f} mg/dL"),
    "glu_std_60m": ("Glucose variability, last hour", "{:.0f} mg/dL"),
    "glu_max_120m": ("Highest glucose, last 2 hours", "{:.0f} mg/dL"),
    "hr_mean_30m": ("Heart rate, last 30 min", "{:.0f} bpm"),
    "mets_mean_30m": ("Activity intensity, last 30 min", "{:.1f} METs"),
    "act_kcal_60m": ("Activity energy, last hour", "{:.0f} kcal"),
    "carbs_3h": ("Carbs eaten, last 3 hours", "{:.0f} g"),
    "protein_3h": ("Protein eaten, last 3 hours", "{:.0f} g"),
    "fat_3h": ("Fat eaten, last 3 hours", "{:.0f} g"),
    "fiber_3h": ("Fiber eaten, last 3 hours", "{:.0f} g"),
    "min_since_meal": ("Time since last meal", "{:.0f} min"),
    "age": ("Age", "{:.0f}"), "bmi": ("BMI", "{:.1f}"),
    "hba1c": ("HbA1c", "{:.1f}%"), "fasting_glu": ("Fasting glucose", "{:.0f} mg/dL"),
    "male": ("Sex", None), "time_of_day": ("Time of day", None),
}


def level(p):
    return "HIGH" if p >= HIGH else "WATCH" if p >= WATCH else "LOW"


def show_level(lv, text):
    {"HIGH": st.error, "WATCH": st.warning, "LOW": st.success}[lv](text)


risk, meal, explainer = load_models()
feats, meals, foods = load_data()
FEAT = risk["features"]

st.title("Digital twin: Type 2 diabetes spike warning")
st.caption("Research prototype built on public data. Not a medical device and not for clinical use.")

# ---------------- Sidebar: choose patient and moment ----------------
grp = feats.groupby("subject").group.first()
subjects = list(grp.index)
default = subjects.index(grp[grp == "t2d"].index[0])
subj = st.sidebar.selectbox("Patient", subjects, index=default,
                            format_func=lambda s: f"Patient {s} ({grp[s]})")
p = feats[feats.subject == subj]
day = st.sidebar.selectbox("Day", sorted(p.time.dt.date.unique()))
dd = p[p.time.dt.date == day]
tmin, tmax = dd.time.min().to_pydatetime(), dd.time.max().to_pydatetime()
t = st.sidebar.slider("Time", min_value=tmin, max_value=tmax,
                      value=tmin + (tmax - tmin) / 2, step=timedelta(minutes=5), format="HH:mm")
pos = (dd.time - pd.Timestamp(t)).abs().argmin()
row, t0 = dd.iloc[pos], dd.iloc[pos].time
x = dd.iloc[[pos]][FEAT].astype(float)

st.sidebar.markdown("**Patient profile (from the record)**")
st.sidebar.write(f"Age {row.age:.0f}, {'male' if row.male else 'female'}, BMI {row.bmi:.1f}")
st.sidebar.write(f"HbA1c {row.hba1c:.1f}%, fasting glucose {row.fasting_glu:.0f} mg/dL")

# ---------------- Main: timeline + risk ----------------
left, right = st.columns([3, 2])

with left:
    st.subheader(f"Glucose around {t0:%d %b, %H:%M}")
    win = p[(p.time >= t0 - timedelta(hours=6)) & (p.time <= t0 + timedelta(hours=2))]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    past, fut = win[win.time <= t0], win[win.time >= t0]
    ax.plot(past.time, past.glu_now, color="tab:blue", label="Glucose so far")
    ax.plot(fut.time, fut.glu_now, color="tab:blue", alpha=0.4, ls="--",
            label="What actually happened next")
    ax.axhline(THR, color="red", ls="--", lw=1)
    ax.axvline(t0, color="gray", lw=1)
    for mt in meals[(meals.subject == subj) & meals.time.between(win.time.min(), win.time.max())].time:
        ax.axvline(mt, color="orange", alpha=0.6, lw=1)
    ax.plot([], [], color="orange", label="Meal logged")
    ax.set_ylabel("mg/dL"); ax.legend(loc="upper left", fontsize=8)
    fig.autofmt_xdate(); st.pyplot(fig)

with right:
    st.subheader("Spike risk, next 2 hours")
    if row.glu_now < 70:
        st.warning("Glucose is below 70 mg/dL (low). This tool predicts high spikes only, "
                   "so a LOW spike risk does not mean the patient is safe.")
    if row.glu_now > THR:
        st.info(f"Glucose is already {row.glu_now:.0f} mg/dL, above {THR}. "
                "The model predicts new spikes only.")
    else:
        prob = float(risk["model"].predict_proba(x)[0, 1])
        show_level(level(prob), f"Risk level: {level(prob)}")
        
        sv = explainer.shap_values(x)
        sv = sv[1] if isinstance(sv, list) else sv
        groups = {f: f for f in FEAT}
        groups["hour_sin"] = groups["hour_cos"] = "time_of_day"
        contrib = pd.Series(sv[0], index=FEAT).groupby(groups).sum().sort_values()
        contrib = contrib.drop(["age", "bmi", "male"], errors="ignore")

        def describe(f):
            name, fmt = NAMES[f]
            if f == "male":
                return f"{name}: {'male' if row.male else 'female'}"
            if f == "time_of_day":
                return f"{name}: {t0:%H:%M}"
            return f"{name}: {fmt.format(row[f])}"

        st.markdown("**Why**")
        for f in contrib[contrib > 0].tail(3)[::-1].index:
            st.write(f"▲ raises risk: {describe(f)}")
        for f in contrib[contrib < 0].head(2).index:
            st.write(f"▼ lowers risk: {describe(f)}")
        st.caption("Levels are tuned on held-out Type 2 diabetes data: WATCH catches more spikes "
                   "with more false alarms, HIGH fewer of each.")

# ---------------- Meal what-if ----------------
st.divider()
st.subheader("Meal what-if: what if this patient eats this now?")
chosen = st.multiselect("Choose dishes", foods.dish.tolist())
tot = {"carbs": 0.0, "protein": 0.0, "fat": 0.0, "fiber": 0.0}
cols = st.columns(max(len(chosen), 1))
for c, d in zip(cols, chosen):
    n = c.number_input(f"{d}: portions", 0.5, 4.0, 1.0, 0.5, key=d)
    r = foods[foods.dish == d].iloc[0]
    for k in tot:
        tot[k] += n * r[k]

if chosen:
    capped = {k: min(v, CAPS[k]) for k, v in tot.items()}
    st.write(f"Meal total: {tot['carbs']:.0f} g carbs, {tot['protein']:.0f} g protein, "
             f"{tot['fat']:.0f} g fat, {tot['fiber']:.0f} g fiber")
    if capped != tot:
        if tot["carbs"] > 100:
            st.caption("Above about 100 g of carbs the model has little data, "
                       "so treat this estimate as a minimum.")
        st.caption("Values above the range the model saw in training were capped.")
    mrow = pd.DataFrame([{**capped, "glu0": row.glu_now, "hour": t0.hour + t0.minute / 60,
                          "age": row.age, "bmi": row.bmi, "hba1c": row.hba1c,
                          "fasting_glu": row.fasting_glu, "male": row.male}])[meal["features"]]
    rise = float(meal["model"].predict(mrow)[0])
    peak = row.glu_now + rise
    st.metric("Predicted peak glucose within 2 hours", f"{peak:.0f} mg/dL",
              f"typical range {peak - MEAL_ERR:.0f} to {peak + MEAL_ERR:.0f}", delta_color="off")
    if peak - MEAL_ERR > THR:
        st.error(f"Likely to go above {THR} mg/dL.")
    elif peak + MEAL_ERR > THR:
        st.warning(f"Could go above {THR} mg/dL.")
    else:
        st.success(f"Unlikely to go above {THR} mg/dL.")
    st.caption("Estimate from a model trained on 44 mostly US participants eating US meals. "
               "Dish nutrition is a database estimate. Typical error is about 30 mg/dL.")

st.divider()
st.caption("The risk model was trained on all 45 participants, so the patients shown here were seen "
           "in training. Accuracy figures come from held-out testing (see docs/findings.md).")
