# Simulation workspace brief (read this first, every session)

## Goal
Add a "virtual patient simulation workspace" to an existing hackathon project (Happiest Health
Digital Twin challenge, India). The project predicts whether a Type 2 diabetes patient's glucose
will exceed 180 mg/dL within the next 2 hours. A real-data pipeline already exists and works.
We are adding a simulator-based workspace where a doctor can create virtual patients with full
data (sleep stages, steps, HRV, heart rate, CGM glucose, meals, labs, diagnoses, medications,
genetic markers), run simulations, and test what-if scenarios.

## Honesty rules (non-negotiable)
1. Everything the simulator produces is SIMULATED and must be labelled so: a column
   source="simulated" in files, a visible SIMULATED badge in the UI, and wording in reports.
2. Never attach simulated values to a real CGMacros participant. For real participants, fields the
   dataset lacks (sleep, steps, HRV, genetics, diagnoses, medications) show "NOT AVAILABLE".
3. Never mix simulated rows into real-data training or real-data metrics. The real-data headline
   results (AUC about 0.80 on unseen T2D patients) must stay untouched.
4. Every simulator assumption lives in ONE documented file, each with a one-line rationale and the
   note that effect sizes are assumptions, not learned from data.
5. Results on simulated data are "pipeline demonstration", never clinical accuracy.
6. The app is for simulated or anonymised patients only (show a banner).
7. Do not copy images or text from the web. All visuals are original, built with code.

## Existing project (do NOT modify these; add new files only)
src/load_cgmacros.py, src/features.py, src/train.py, src/train_meal.py, src/evaluate.py,
src/explain.py, src/ablation_fusion.py, src/indian_meals.py, src/generate_data.py (old toy
simulator, keep it), app/dashboard.py, models/*, docs/findings.md. README.md may only be
appended to when a part says so.

Data and models (all paths relative to repo root):
- data/processed/cgmacros_all.csv.gz: real CGMacros, 1-minute rows. Columns: subject, time, libre
  (glucose mg/dL), dexcom, hr, act_kcal, mets, meal_type, kcal, carbs, protein, fat, fiber,
  amount_consumed, age, gender, bmi, hba1c, fasting_glu, group (healthy / prediabetes / t2d).
- data/raw/cgmacros/**/bio.csv: real labs per participant (age, BMI, A1c, fasting glucose,
  insulin, triglycerides, cholesterol, HDL, LDL, ...). Column names have stray spaces.
- data/processed/features.csv.gz: 5-minute rows with the model features and future_max.
- data/indian_meals.csv: columns dish, indb_name, indb_code, serving, kcal, carbs, protein, fat,
  fiber (17 Indian dishes, per serving).
- models/xgb_spike_model.pkl: joblib dict {"model": XGBClassifier, "features": [...]}. Always read
  the feature order from the file, never hardcode it.
- models/meal_response_rf.pkl: same dict format. Features: carbs, protein, fat, fiber, glu0,
  hour, age, bmi, hba1c, fasting_glu, male. Predicts the 2-hour glucose rise after a meal.
- Real feature construction is the build() function in src/features.py: 5-minute resampling,
  glucose lags and rolling stats, heart rate / METs / activity kcal windows, 3-hour meal sums,
  minutes since meal, hour sin/cos, plus static age, bmi, hba1c, fasting_glu, male.
- Label: glucose above 180 mg/dL at any point in the next 2 hours, using only moments where
  current glucose is 180 or below. Per-meal caps: carbs 250, protein 150, fat 150, fiber 60.

Environment: Python 3.12 virtualenv in .venv. Packages: pandas, numpy, scikit-learn, xgboost,
shap, streamlit, matplotlib, joblib, openpyxl. Add pytest. No other dependency without
listing it in requirements.txt and giving the reason.

## New code layout
src/sim/        assumptions.py, profile.py, simulator.py, featurize.py, calibrate.py, cohort.py,
                store.py, scenarios.py
app/sim_workspace.py and app/sim_ui/ (small modules), tests/
data/simulated/ (generated, gitignored), data/virtual_patients/presets/ (committed),
data/virtual_patients/custom/ (gitignored)
Run the app with: streamlit run app/sim_workspace.py

## Working rules for the agent
- Work only on branch feature/virtual-patients. Commit at the end of each part: "Part N: <title>".
- Do only the part you are asked to do. At the end STOP and print: files created or changed,
  exact commands to run, test results, open questions. Do not start the next part.
- Keep files small and modular. Do not print large dataframes or logs. Cache expensive outputs.
  Training or generation runs should take minutes, not hours.
- Keep docs/SIM_PROGRESS.md updated: what is done, decisions made, tuned parameters. Read it at
  the start of every session.
- If a requirement is ambiguous, take the simplest reading and note it in SIM_PROGRESS.md. Ask
  only if blocked.
- Verify before claiming done: actually run the tests and commands.
- Never run git push, git reset, git clean, rm -rf, or any command that deletes files outside
   data/simulated/. Never touch the main branch. Never read or write files outside this repo.