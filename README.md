# Type 2 Diabetes Digital Twin: 2-Hour Glucose Spike Warning

A research prototype that combines clinical-record features, continuous glucose monitoring (CGM), wearable signals, and meal information to estimate the risk of a new glucose spike within the next two hours.

**Built by Team Strawhats · Army Institute of Technology (AIT), Pune**

[Project repository](https://github.com/delulu-monkey/strawhats_AITPune) · [Presentation](docs/presentation.pdf) · [Architecture](docs/architecture.pdf)

> **Important:** This is an experimental proof of concept for education and research. It is not a medical device and must not be used to diagnose, treat, or make clinical decisions.

## Table of contents

- [Overview](#overview)
- [Why this project](#why-this-project)
- [Features](#features)
- [How it works](#how-it-works)
- [Data sources](#data-sources)
- [Machine-learning approach](#machine-learning-approach)
- [Evaluation](#evaluation)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Running the application](#running-the-application)
- [Reproducing the pipeline](#reproducing-the-pipeline)
- [Limitations](#limitations)
- [Team](#team)
- [References and data licensing](#references-and-data-licensing)
- [License](#license)

## Overview

Glucose levels can rise after meals, and those changes may not be obvious from an occasional measurement. This project explores whether a patient-specific digital-twin-style view—combining a clinical profile with recent glucose, activity, heart-rate, and meal signals—can help surface a possible glucose spike early enough for a clinician to review.

The prototype focuses on two connected workflows:

1. **Two-hour spike warning:** estimates whether glucose may exceed **180 mg/dL** at any point during the following two hours, when the current glucose reading is at or below that threshold.
2. **Meal what-if exploration:** estimates a possible glucose peak for selected Indian dishes and portions, using nutrition data and a learned meal-response model.

A Streamlit dashboard brings the patient profile, glucose history, risk category, and meal scenario into one interface.

## Why this project

The project investigates how two complementary streams can be combined:

- **Static/historical clinical features:** age, sex, BMI, HbA1c, and fasting glucose.
- **Dynamic observations:** recent CGM readings and trends, heart rate, activity, and recently logged meal macronutrients.

The intended user is a clinician reviewing a patient's trends—not a patient making treatment decisions from an automated alert.

## Features

### 1. Glucose-spike risk estimation

- Estimates the likelihood of glucose crossing 180 mg/dL in the next two hours.
- Focuses on **new spikes**: observations where current glucose is at or below 180 mg/dL.
- Presents Low / Watch / High alert categories with plain-language explanations in the dashboard.
- Uses an XGBoost classifier for the dashboard risk workflow; logistic regression is also evaluated as a baseline.

### 2. Meal what-if scenarios

- Lets the user choose a dish and portion.
- Uses recipe-level nutrition information to estimate a possible peak glucose response.
- Displays an uncertainty/error range to discourage interpreting the estimate as an exact forecast.

These estimates are observational and approximate. They are not a guarantee of an individual's response to a meal.

### 3. Clinician-oriented dashboard

The Streamlit interface is designed to bring together a patient record, glucose timeline, risk estimate, and meal what-if workflow.

## How it works

```text
CGMacros CGM + heart rate + activity + meal logs
                         │
                         ▼
              Data loading and cleaning
                         │
                         ▼
        Resampling and feature engineering
            (one row every 5 minutes)
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
 Static clinical profile          Dynamic signals
 age, sex, BMI, HbA1c,             glucose trends,
 fasting glucose                   HR, activity, meals
          └──────────────┬──────────────┘
                         ▼
              Two-hour spike target
        future glucose maximum > 180 mg/dL
                         │
                         ▼
       Logistic Regression / XGBoost training
             grouped by participant
                         │
                         ▼
          Saved model and feature metadata
                         │
                         ▼
             Streamlit clinician dashboard

Indian Nutrient Databank ──► meal-response model ──► meal what-if estimate
```

### Feature engineering

The pipeline resamples the source signals to **five-minute intervals**. Features include:

- Current glucose and changes over the previous 15, 30, and 60 minutes.
- Rolling glucose mean, variability, and recent maximum.
- Recent heart-rate and activity summaries.
- Carbohydrate, protein, fat, and fibre logged during the preceding three hours.
- Time since the last logged meal and time-of-day encodings.
- Static clinical fields: age, sex, BMI, HbA1c, and fasting glucose.

The prediction target is whether the **maximum glucose in the next 120 minutes** exceeds 180 mg/dL. Rows where glucose is already above 180 mg/dL are excluded from spike training so the model focuses on new threshold crossings rather than identifying an already-high reading.

## Data sources

### CGMacros (PhysioNet)

The glucose-risk pipeline uses the CGMacros dataset, which includes CGM measurements and associated physiological, activity, meal, and clinical-profile information. The project groups participants into healthy, prediabetes, and type 2 diabetes cohorts using HbA1c-based criteria.

The repository documentation reports **45 participants** in total: 15 healthy, 16 with prediabetes, and 14 with type 2 diabetes.

The dataset is not bundled with this repository. Obtain it from [PhysioNet](https://physionet.org/) and follow its access, citation, and license requirements. The project documentation identifies the CGMacros data license as **CC BY-NC-SA 4.0**; verify the dataset's current terms on its official page before using or redistributing it.

### Indian Nutrient Databank (INDB)

The meal scenario workflow uses recipe-level nutrition data from the Indian Nutrient Databank described by Vijayakumar and colleagues (2024). The project selects 17 dishes for its demonstration. Dish nutrition values and serving sizes are estimates, not personalized measurements.

Check the original paper and dataset terms before reusing or redistributing the data.

### Synthetic data

`src/generate_data.py` provides simulated data for early development and prototyping. The reported model metrics in this project's documentation are based on CGMacros participant data, not on the synthetic generator.

**Privacy note:** the project describes its inputs as public or synthetic and states that no private patient data is included in the repository. Do not commit identifiable health information or credentials.

## Machine-learning approach

### Glucose-spike classifier

Two classifiers are evaluated:

- **Logistic Regression:** interpretable baseline with imputation, feature scaling, and class weighting.
- **XGBoost:** tree-based classifier used by the dashboard and for feature-based explanations.

The code uses five-fold `GroupKFold` validation with participant identity as the grouping variable. This is important because observations from one person should not appear in both the training and test folds.

### Meal-response model

A Random Forest model estimates the glucose peak associated with meal scenarios. It is evaluated on participants held out from training. The estimate is association-based and should not be interpreted as a causal or clinical prediction.

### Data quality handling

The feature pipeline caps implausible meal entries to reduce the influence of obvious source-data errors: carbohydrates at 250 g, protein at 150 g, fat at 150 g, and fibre at 60 g per meal record. This is a pragmatic preprocessing step, not a substitute for validating the original records.

## Evaluation

The repository's documented results for the **type 2 diabetes subgroup**, evaluated on held-out participants, are:

| Model / baseline | ROC-AUC | 95% interval | PR-AUC |
|---|---:|---:|---:|
| Logistic Regression | 0.800 | 0.766–0.839 | 0.484 |
| XGBoost | 0.787 | 0.744–0.830 | 0.465 |
| “High and rising” rule | 0.733 | 0.701–0.756 | Not reported |

The documented spike base rate in this subgroup is **15.9%**. Logistic Regression and XGBoost perform similarly in these experiments; the reported results do not establish that one is universally better.

The project documentation also reports a typical meal-model error of approximately **31 mg/dL**, compared with approximately 39 mg/dL when predicting the average. Treat this as an experimental result on a small dataset, not a guarantee of performance for new people or meals.

### Interpreting the numbers

- **ROC-AUC** measures how well a model ranks positive cases above negative cases across thresholds.
- **PR-AUC** summarizes precision-recall performance and is especially useful when positive cases are relatively uncommon.
- A good aggregate score does not mean every alert is correct or that the model is suitable for clinical use.

Results are dependent on this dataset, preprocessing, validation design, and threshold. They require independent external validation before any real-world use.

## Technology stack

- **Language:** Python 3.12
- **Data processing:** pandas, NumPy
- **Machine learning:** scikit-learn, XGBoost
- **Model interpretation:** SHAP
- **Dashboard:** Streamlit
- **Visualization:** Matplotlib
- **Notebook / analysis tooling:** Jupyter

## Repository structure

The repository is organized around the following areas:

```text
strawhats_AITPune/
├── app/                  # Streamlit dashboard
├── data/
│   ├── raw/              # Downloaded source datasets (not committed)
│   └── processed/        # Cleaned data and engineered features
├── docs/
│   ├── presentation.pdf  # Project presentation
│   └── architecture.pdf  # System architecture
├── models/               # Trained model artifacts
├── src/
│   ├── generate_data.py  # Synthetic data generator
│   ├── load_cgmacros.py  # CGMacros loading/preprocessing
│   ├── features.py       # Resampling and feature engineering
│   ├── train.py          # Spike classifier training/evaluation
│   ├── train_meal.py     # Meal-response model training
│   ├── indian_meals.py   # Indian meal data preparation
│   └── evaluate.py       # Evaluation workflow
├── requirements.txt
├── LICENSE
└── README.md
```

Some generated files and filenames may vary as the project evolves. Refer to the current repository tree if a path differs.

## Getting started

### Prerequisites

- Git
- Python **3.12**
- `uv` package manager (recommended by the project workflow)
- The required source datasets downloaded separately

### 1. Clone the repository

```bash
git clone https://github.com/delulu-monkey/strawhats_AITPune.git
cd strawhats_AITPune
```

### 2. Create and activate a virtual environment

```bash
uv venv --python 3.12
source .venv/bin/activate
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
uv pip install -r requirements.txt
```

The repository's `requirements.txt` pins many packages. If installation fails on your platform, check that you are using Python 3.12 and review the package error before changing pinned versions.

### 4. Download and place the datasets

Download CGMacros from its official PhysioNet record, review its access and citation requirements, and place the extracted source files under:

```text
data/raw/cgmacros/
```

Obtain the Indian Nutrient Databank data required by the meal workflow and place it under:

```text
data/raw/indb/
```

The datasets are not included in this Git repository. The exact source archive structure may require matching the expected filenames in the loader scripts.

## Running the application

After the required processed data and model artifacts have been generated, launch the dashboard from the repository root:

```bash
streamlit run app/dashboard.py
```

Streamlit will print a local URL in the terminal. Open that URL in your browser.

If the dashboard reports missing files, confirm that you have completed the preprocessing and training steps below and that the expected files exist in `data/processed/` and `models/`.

## Reproducing the pipeline

Run the commands from the repository root, in order:

```bash
# 1. Load and preprocess CGMacros
python src/load_cgmacros.py

# 2. Build five-minute features and prediction targets
python src/features.py

# 3. Train/evaluate the glucose-spike classifiers
python src/train.py

# 4. Train the meal-response model
python src/train_meal.py

# 5. Prepare Indian meal scenarios
python src/indian_meals.py

# 6. Run the evaluation workflow
python src/evaluate.py

# 7. Launch the dashboard
streamlit run app/dashboard.py
```

The exact order and expected input/output files are determined by the scripts; if a step fails, check the paths and filenames expected by that script. Do not skip dataset preparation.

## Limitations

Please read these limitations before interpreting the dashboard:

- **Small cohort:** the type 2 diabetes subgroup contains only 14 participants, with roughly ten days of observations per participant. This is a proof of concept.
- **Limited external validity:** the source cohort is predominantly US-based. The system has not been validated on an Indian patient cohort.
- **Approximate meal data:** Indian dish nutrition and portions are database-based estimates; actual recipes and servings vary.
- **Unlogged intake:** snacks, drinks, and meals that are not recorded are invisible to the model.
- **Restricted wearable signals:** the real dataset includes heart-rate and activity signals, but not step-count or sleep data.
- **Row-level metrics:** reported metrics are calculated per five-minute observation. Episode-level performance has not been established.
- **Meal what-if uncertainty:** meal estimates are association-based, with limited training examples for very high carbohydrate quantities. They are not causal simulations.
- **High-glucose focus only:** the model does not predict hypoglycaemia (low glucose).
- **Demonstration patients:** patients shown in the dashboard may have contributed to model training. The held-out validation results are separate from the dashboard demonstration.
- **No clinical validation:** the prototype has not established clinical safety, regulatory approval, or improved patient outcomes.

### Intended use and safety

Use this project for learning, research, and demonstration only. Do not use its predictions to change medication, insulin dosage, diet, or treatment. Real-world clinical use would require appropriate consent and privacy protections, prospective and independent validation, clinical oversight, and relevant regulatory review.

## Team

**Team Strawhats — Army Institute of Technology, Pune**

- **Adarsh Singh Bhadauriya** — Team Lead
- **Prabhat Ranjan**
- **Pawan Singh Kunwar**
- **Sumit Kumar**

Project materials:
- [Presentation slides](docs/presentation.pdf)
- [Architecture document](docs/architecture.pdf)

Add the public demonstration video URL here when it is available; the previous README contained a placeholder rather than a working link.

## References and data licensing

1. **CGMacros dataset.** PhysioNet. Use the official dataset record for the current citation, access instructions, and terms: [PhysioNet](https://physionet.org/).
2. **Vijayakumar A, Dubasi HB, Awasthi A, Jaacks LM.** *Development of an Indian Food Composition Database.* Current Developments in Nutrition, 2024. Consult the publication for the formal citation and data-use terms.

Dataset licenses are separate from the license for this repository's source code. Verify and follow the original terms before redistributing data or derived files.

## License

The source code in this repository is distributed under the **MIT License**. See [`LICENSE`](LICENSE) for the full text. The MIT license for code does not override the separate licenses or terms governing third-party datasets.
