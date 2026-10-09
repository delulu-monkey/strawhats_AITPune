# Findings (updated 9 Oct 2026)

## Setup
- Data: CGMacros (PhysioNet), 45 participants: 15 healthy, 16 prediabetes, 14 T2D.
  Groups defined by HbA1c (T2D = 6.5 or above).
- Glucose sensor: Libre (no missing data). The Dexcom sensor reads higher
  (T2D time above 180: 29% vs 16% on Libre) and has about 8% missing readings.
- Target: will glucose exceed 180 mg/dL in the next 2 hours?
  Only moments where glucose is currently 180 or below are used (predicting NEW spikes).
- Rows: 128,006, spike rate 6.8% (15.9% in T2D). 22 features, 5-minute resolution.
- Features: current glucose and its recent change, heart rate, activity, food eaten
  in the last 3 hours, time of day (dynamic); age, sex, BMI, HbA1c, fasting glucose (static).
- Validation: 5-fold split BY PERSON, so every test person is unseen in training.

## Results (T2D patients only, unseen people)
| Model | AUC (95% interval) | PR-AUC |
|---|---|---|
| Logistic regression | 0.800 (0.766-0.838) | 0.484 |
| XGBoost | 0.787 (0.744-0.830) | 0.465 |
| Simple rule "high and rising" | 0.733 (0.701-0.756) | n/a |
Spike base rate in T2D: 0.159.
Intervals come from resampling the 14 people, not the rows.

## Key points
- Logistic regression beats the simple rule: difference +0.031 to +0.111, excludes 0.
- Logistic and XGBoost are statistically tied. We report both.
- Wearable (heart rate + activity): T2D AUC 0.770 -> 0.787. Difference interval
  -0.004 to +0.035 includes 0, so the benefit is small and NOT statistically clear with 14 patients.
- Per-person AUC (people with both outcomes, 29 of 45): T2D median 0.82, worst 0.66.
  Every T2D patient scores above chance.

## Alert levels (T2D, logistic model)
- Precision at least 40%: catches 56% of spikes
- Precision at least 50%: catches 39% of spikes
- Precision at least 60%: catches 26% of spikes
Dashboard will show Low / Watch / High, not a raw percentage (scores are inflated by class weighting).

## Limitations
- Only 14 T2D participants, about 10 days each. Results are a proof of concept.
- Mostly US participants and US meals. Not validated on Indian patients or diets.
- Unlogged snacks and drinks are invisible to the model.
- Real data has no step count and no sleep. We use heart rate, METs and activity calories.
- Metrics are per 5-minute row; neighbouring rows are near-copies. Episode-level
  evaluation (was each spike warned in advance?) is not done yet.
- Synthetic Day-1 data is used only for demos, never for reported results.
- Indian dish nutrition comes from recipe-based database estimates. Deep-fried and rich   dishes show implausible fat values (for example 83 g fat per samosa) and were excluded. Portion sizes are approximate and adjustable in the dashboard.

## Open issues
- What-if check on the logistic model: activity behaves correctly (risk falls as
  activity rises) but meal carbs barely change risk (0.57-0.61 from 0 to 100 g).
  Plan: separate meal-response model, and test it against a predict-the-average baseline.
- Weights chart is misleading because glu_now and glu_mean_60m overlap. Use SHAP instead.

## Meal-response model (what-if tool)
- Target: highest glucose rise within 2 hours of a meal. 1,246 isolated meals
  (no other meal within 2 hours), 44 people, 388 meals from T2D participants.
- Average 2-hour rise: healthy 33, prediabetes 45, T2D 62 mg/dL.
- Unseen people, T2D: random forest MAE 31.5 (R2 +0.30), Ridge MAE 34.5 (R2 +0.19),
  predict-the-average MAE 39.0 (R2 -0.12).
- Ridge effect per gram: carbs +0.37 mg/dL, fiber -0.65 mg/dL.
- Limits: explains roughly 30% of variation; typical error about 30 mg/dL; trained on
  US participants and meals; dish nutrition for Indian foods is approximate.

## Resolved
- Impossible meal values (fiber up to 2,830 g) were capped. This removed a spurious
  fiber effect in the logistic weights (-2.60 -> -0.21).

- What-if check, random forest (typical T2D patient): predicted rise grows with carbs
  (0 g: 21, 30 g: 22, 60 g: 39, 100 g: 57 mg/dL) and falls with fiber at 60 g carbs
  (0 g: 44, 10 g: 37, 20 g: 36). Ridge agrees on direction but predicts larger rises
  (100 g: +83). The dashboard uses the random forest and shows a range.

## Activity what-if (negative result)
- Multiplying recorded activity in the XGBoost risk model, on 4,000 T2D moments:
  mean risk 0.336 (x0), 0.368 (x0.5), 0.426 (x1), 0.446 (x2), 0.431 (x3).
  Risk rises from zero to recorded activity, the opposite of the expected direction.
  The model captures association, not the causal effect of activity.
- Activity what-if removed from the dashboard. The meal what-if is kept (direction
  checked: carbs raise and fiber lowers the predicted peak) but is also an
  association-based estimate.

## Meal what-if check (3,000 T2D moments, random forest)
- Mean predicted 2-hour rise: 55.6 (0 g carbs), 55.7 (20 g), 62.9 (50 g), 75.5 (100 g), 75.5 (150 g).
  100 g gave a higher peak than 20 g in 100% of moments. Flat above ~100 g (little training data).
- Starting glucose does not inflate the rise (50 g meal: 57 mg/dL when starting at 80 or below,
  61-67 otherwise).
- The carbs effect is modest (about +20 mg/dL from 0 to 100 g) compared with the typical error (about 30 mg/dL),
  so the tool is for comparing meals directionally, not for exact prediction.
