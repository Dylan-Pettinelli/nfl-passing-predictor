# NFL QB Passing Yards Prediction System

A machine learning pipeline that predicts NFL quarterback passing yards using historical play-by-play data. Built as a portfolio project to demonstrate end-to-end ML development: data ingestion, feature engineering, model training, evaluation, and deployment.

---

## What this is

This project pulls historical NFL play-by-play data via the **nflfastR** R package, trains a regression model to predict QB passing yards for upcoming games, and surfaces predictions through both a desktop CLI and a mobile-accessible Streamlit dashboard.

The system retrains weekly on a rolling basis as new game results come in, allowing model performance to be tracked in real time across an entire season.

**Current performance:** 54.7% directional accuracy across 150 out-of-sample predictions (vs. 50% baseline)

---

## Project structure

```
nfl-passing-predictor/
├── src/
│   ├── train_pipeline.py       # Feature engineering + model training
│   └── update_actuals.R        # Fetch weekly results via nflfastR
├── data/
│   ├── *_logs.csv              # Historical NFL play-by-play logs
│   ├── passing-prop-predictions-2025.xlsx  # Prediction tracker
│   └── backups/                # Auto-generated backups
├── models/
│   └── *.pkl                   # Serialized trained model + scaler
├── batch-imports/              # CSV templates for batch prediction
├── predict_upcoming.py         # Generate predictions for upcoming games
├── diagnostics.py              # Model performance analysis
├── dashboard.py                # Generate visual HTML report
├── streamlit_app.py            # Mobile-accessible Streamlit UI
├── quick_actions.py            # All-in-one convenience menu
├── validate_setup.py           # Installation check
└── requirements.txt
```

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

R dependencies (for data ingestion):
```r
install.packages(c("nflfastR", "tidyverse", "dplyr"))
```

### 2. Fetch historical data and train

```bash
Rscript src/update_actuals.R 1    # Pull data through week 1
python -m src.train_pipeline      # Train model on historical data
```

### 3. Generate predictions

```bash
python predict_upcoming.py
```

### 4. Analyze performance

```bash
python diagnostics.py    # Full metrics: MAE, RMSE, directional accuracy
python dashboard.py      # Generate visual HTML report
```

### 5. Launch Streamlit dashboard

```bash
streamlit run streamlit_app.py
```

Opens at http://localhost:8501. Also deployable to Streamlit Cloud for mobile access.

---

## What the model does

**Data source:** nflfastR — play-by-play NFL data updated weekly

**Input features:**
- QB-level rolling averages (passing yards, attempts, completions)
- Opponent defensive pass metrics (yards allowed per game, pressure rate)
- Home/away indicator
- Week of season
- Opponent rank vs. the pass
- Lag features: last 3 games, season average, same matchup prior year

**Target:** Passing yards in the upcoming game

**Model:** Gradient Boosting Regressor (scikit-learn), tuned via cross-validation

**Evaluation:** Chronological train/test split — no lookahead bias

**Weekly retraining:** Model updates every week as actual results come in via `update_actuals.R`, ensuring it learns from the most recent data throughout the season

---

## Performance tracking

The system tracks predictions vs. actuals across the full season:

```
Overall directional accuracy:   54.7% (150 predictions)
Home games:                     57.3%
Away games:                     52.0%
Best edge range (5–20 yd gap):  60.0%
```

Players with consistently high error (70+ yd avg error) are flagged automatically in `diagnostics.py` for model review.

---

## Mobile deployment (Streamlit Cloud)

The Streamlit app supports:
- Predictions from phone or tablet
- Batch import via CSV
- Auto-save to Google Sheets
- Export to Excel

To deploy: push to GitHub, connect to [Streamlit Cloud](https://streamlit.io/cloud), and add Google Sheets credentials to `.streamlit/secrets.toml`.

---

## Weekly workflow

```
Monday:    Rscript src/update_actuals.R [week]   # Ingest latest results
Tuesday:   python -m src.train_pipeline           # Retrain model
Tuesday+:  python predict_upcoming.py             # Generate new predictions
Anytime:   python diagnostics.py                  # Review model performance
```

Total time: ~30 minutes per week.

---

## Skills demonstrated

- R data ingestion (nflfastR, tidyverse)
- Python ML pipeline (scikit-learn, pandas, numpy)
- Feature engineering for time-series sports data
- Rolling retraining and out-of-sample evaluation
- Streamlit dashboard development and cloud deployment
- Google Sheets API integration
- Multi-platform workflow (desktop + mobile)

---

*Built by Dylan Pettinelli — portfolio project demonstrating ML pipeline development and sports analytics*
