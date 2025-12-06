# 🌍 CO₂ Emission Dashboard

The **CO₂ Emission Dashboard** is an interactive data analytics application built with **Panel**, **Bokeh**, **Pandas**, and **FastAPI**.  
It allows users to explore **CO₂ emission statistics**, visualize trends, perform **time-series forecasting**, and simulate **policy recommendations** for different countries.

---

## ✨ Main Features

### 1. Dashboard – Explore Global CO₂ Emissions
<img width="1881" height="863" alt="image" src="https://github.com/user-attachments/assets/9163ee4f-49b4-4f99-b2f5-d0d1c69842a5" />

Interactive analytics view for exploring historical CO₂ data:

- **Filters**
  - Continent
  - Country
  - Year range
- **Key indicators (KPIs)**
  - Total CO₂ emissions (MtCO₂)
  - CO₂ emissions per capita (tCO₂/person)
  - GDP (human-readable format)
  - Human Development Index (HDI)
  - Energy use per capita (kWh)
- **Visualizations**
  - CO₂ per capita trend
  - Total CO₂ emissions trend
  - Hover tooltips for exact values
  - Global and continent-level comparison

> _This tab is implemented in `tab_dashboard.py`._

---

### 2. Forecast – Predict Future CO₂ Emissions
<img width="1740" height="580" alt="image" src="https://github.com/user-attachments/assets/ce545880-0742-4874-bf13-0fab1cc756d2" />

Time-series forecasting using a GRU neural network:

- **Inputs**
  - Country
  - Target year to forecast
  - A sliding **history window** (e.g. last 3 years) of:
    - CO₂ emissions (MtCO₂)
    - Population
    - GDP
    - Industry on GDP
    - Government expenditure on education
    - Global Climate Risk Index
    - HDI
    - Renewable energy percent
    - Deforestation percent
    - Energy use per capita (kWh)
- **UI**
  - Editable grid built with **Tabulator**
  - Historical rows inside the dataset range are auto-filled and locked
  - Years outside the dataset range can be edited manually
- **Backend**
  - FastAPI endpoint `/predict`
  - Uses a pre-trained GRU model to forecast total CO₂ emissions for the selected year

> _This tab is implemented in `tab_forecast.py`, backed by `api_forecast.py` and pre-trained models in `Models/`._

---

### 3. Recommendation Engine – Simulate Policy Scenarios
<img width="1872" height="864" alt="image" src="https://github.com/user-attachments/assets/2b8f3fdd-47bc-4200-9272-e735ecdcf6c9" />

Optimization-based recommendation system to test “what-if” scenarios:

- **Inputs**
  - Country and year
  - Target CO₂ emission level
  - Current (base) values of key features (GDP, energy, renewables, deforestation, etc.)
  - A subset of **selected features** with allowed change ranges (min/max %)
- **Optimization**
  - Uses an **evolution strategy** to search for the best percentage changes to the selected features
  - Objective: get model-predicted CO₂ as close as possible to the user-defined target
- **Outputs**
  - Recommended % change for each selected feature
  - Predicted CO₂ emissions after applying those changes
  - Fitness score (how close the recommendation is to the target)

> _This tab is implemented in `tab_recommendation.py`, backed by `api_recommend.py` and an XGBoost model stored in `Models/`._

---

## 🧱 Project Structure

```text
Project_CO2/
├─ Models/
│  ├─ GRU models for forecasting (*.keras)
│  ├─ XGBoost model for recommendation (e.g. Model_XGBoost.joblib)
│  ├─ Scalers (e.g. scaler_quantile.save)
│  └─ Label encoder for countries (e.g. labelencoder_country.save)
├─ df_continent.csv          # Cleaned dataset with country/continent/year features
├─ main_app.py               # Panel application entry point (tabs, layout, routing)
├─ tab_dashboard.py          # Dashboard tab
├─ tab_forecast.py           # Forecast tab (GRU time-series)
├─ tab_recommendation.py     # Recommendation / optimization tab
├─ api_forecast.py           # FastAPI service for CO₂ forecasting
└─ api_recommend.py          # FastAPI service for recommendation engine
```
---

## 🚀 Getting Started
1. Create Environment & Install Dependencies

From the Project_CO2/ directory:

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```
pip install -r requirements.txt  # if available
# or:
# pip install panel bokeh pandas fastapi uvicorn tensorflow xgboost joblib
```

Make sure the Models/ folder contains all required models, scalers, and encoders.

2. Run the Backend APIs

In one terminal, start the forecast API (update port if needed to match API_URL in tab_forecast.py):
```
uvicorn api_forecast:app --host 0.0.0.0 --port 8001 --reload
```

In another terminal, start the recommendation API (update port to match API_URL in tab_recommendation.py):
```
uvicorn api_recommend:app --host 0.0.0.0 --port 8002 --reload
```
3. Run the Dashboard (Panel App)

In a third terminal:
```
panel serve main_app.py \
  --port 5006 \
  --autoreload \
  --show
```

This will open the CO₂ Emission Dashboard in your browser (usually at http://localhost:5006).

## 🧭 How to Use

**Dashboard tab**

- Select a continent, country, and year range.

- Explore KPIs and trends for total CO₂ and CO₂ per capita.

- Compare countries or regions over time.

**Forecast tab**

- Choose a country and predict year.

- Check the auto-filled historical window (e.g. last 3 years).

- For years not in the dataset, manually enter feature values.

- Click “Run Prediction” to get the forecasted CO₂ emissions.

**Recommendation tab**

- Select country and year, and set a target CO₂ emission.

- Define base values and choose which features can be changed.

- Set min/max percentage change for each selected feature.

- Run the optimizer to get recommended adjustments and the corresponding predicted CO₂.
