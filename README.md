# Type 2 Diabetes Digital Twin: 2-Hour Glucose Spike Warning

**Team:** strawhats | **College / incubator:** Army Institute of Technology, Pune
**Team leader:** Adarsh Singh Bhadauriya | **Members:** Prabhat Ranjan, Pawan Singh Kunwar, Sumit Kumar
**Video (unlisted YouTube):** LINK | **Slides:** `docs/presentation.pdf` | **Architecture:** `docs/architecture.pdf`

## Problem and use case
Type 2 diabetes is widespread in India, and glucose spikes after meals are invisible until a
check-up. This proof of concept builds a "digital twin" of a Type 2 diabetes patient that fuses
two data streams (static health record and wearable time series) to warn a doctor when
glucose is likely to exceed 180 mg/dL in the next 2 hours, and lets the doctor test what-if
meals using common Indian dishes.

## What it does
1. **Spike warning:** predicts whether glucose will exceed 180 mg/dL within 2 hours
   (Low / Watch / High, with plain-language reasons).
2. **Meal what-if:** choose Indian dishes and portions to see the predicted peak glucose
   with a typical-error range.
3. **Doctor dashboard** (Streamlit) combining the patient record, glucose timeline,
   risk level and what-if tool.

## Data (all public or synthetic; no private patient data)
- **CGMacros** (PhysioNet), 45 participants: 15 healthy, 16 prediabetes, 14 Type 2 diabetes
  (group by HbA1c). Continuous glucose (Libre), heart rate, activity, meals with macros,
  and a clinical profile (our EHR stream). License: CC BY-NC-SA 4.0. Not included in this repo;
  download from PhysioNet (see "How to run").
- **Indian Nutrient Databank (INDB)**, Vijayakumar et al., Current Developments in Nutrition, 2024:
  recipe-level nutrition for Indian dishes. License: LICENSE FROM THE PAPER. 17 dishes selected;
  deep-fried and rich dishes excluded because of implausible fat values.
- **Synthetic generator** (`src/generate_data.py`): simulated patients, used for early
  prototyping only. No reported results use synthetic data.

## Method
- Data fusion: 1-minute data resampled to 5 minutes. Dynamic features (current glucose,
  recent change, heart rate, activity, food eaten in the last 3 hours, time of day)
  plus static features (age, sex, BMI, HbA1c, fasting glucose).
- Target: glucose above 180 mg/dL at any point in the next 2 hours, using only moments
  where glucose is currently at or below 180 (new spikes).
- Models: logistic regression and XGBoost (risk), random forest (meal response).
- Validation: 5-fold split by person, so every test person is unseen in training.
  Confidence intervals come from resampling people, not rows.
- Per-meal values were capped (carbs 250 g, protein 150 g, fat 150 g, fiber 60 g) because
  the raw data contains impossible entries.

## Results (Type 2 diabetes participants, unseen people)
| Model | AUC (95% interval) | PR-AUC |
|---|---|---|
| Logistic regression | 0.800 (0.766-0.839) | 0.484 |
| XGBoost | 0.787 (0.744-0.830) | 0.465 |
| Simple rule "high and rising" | 0.733 (0.701-0.756) | n/a |

Spike base rate in this group: 15.9%.
- The models beat the simple rule (difference +0.031 to +0.111 for logistic).
- Logistic and XGBoost are statistically tied. XGBoost is used in the dashboard for explanations.
- Adding heart rate and activity: AUC 0.770 to 0.787, but the difference interval
  (-0.004 to +0.035) includes zero, so the benefit is not statistically clear.
- Per-person AUC (people with both outcomes): median 0.82, lowest 0.66 among Type 2 diabetes participants.
- Dashboard alert levels (XGBoost): WATCH catches about 52% of spikes with about 40% of
  alerts correct; HIGH catches about 27% with about 60% correct.
- Meal model (unseen people, Type 2 diabetes): error about 31 mg/dL vs 39 for predicting the average;
  carbs raise and fiber lowers the predicted peak.

## Limitations (please read)
- Only 14 Type 2 diabetes participants with about 10 days each. This is a proof of concept.
- Mostly US participants and US meals. Not validated on Indian patients; Indian dish
  nutrition values are database estimates and portions are approximate.
- Unlogged snacks and drinks are invisible to the model.
- No step count or sleep data in the real dataset (heart rate and activity are used).
- Metrics are per 5-minute row. Episode-level evaluation is not done.
- The activity what-if was tested and removed because the model learned the wrong direction.
  The meal what-if is an association-based estimate with about 30 mg/dL typical error and
  little data above about 100 g of carbs.
- The model predicts high glucose only, not low glucose.
- The dashboard patients were part of training; reported accuracy comes from held-out tests.
- Research prototype, not a medical device.

## How to run
```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
# 1. download CGMacros from PhysioNet into data/raw/cgmacros/ and unzip
# 2. download INDB into data/raw/indb/
python src/load_cgmacros.py && python src/features.py
python src/train.py && python src/train_meal.py && python src/indian_meals.py
python src/evaluate.py
streamlit run app/dashboard.py
```

## Tech stack
Python 3.12, pandas, NumPy, scikit-learn, XGBoost, SHAP, Streamlit, Matplotlib.

## License
Code: MIT (see `LICENSE`). Datasets keep their original licenses (see Data).

## References
- CGMacros dataset, PhysioNet. CITATION FROM THE PHYSIONET PAGE.
- Vijayakumar A, Dubasi HB, Awasthi A, Jaacks LM. Development of an Indian Food
  Composition Database. Current Developments in Nutrition, 2024.
