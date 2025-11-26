# 🌍 CO₂ Emission Dashboard

The **CO₂ Emission Dashboard** is an interactive data analytics application built using **Panel**, **Bokeh**, and **Pandas**.  
It allows users to explore **CO₂ emission statistics**, visualize trends, perform **forecasting**, and simulate **recommendation-based scenarios**.

---

## 🚀 Features

### ✔ **Dashboard**
- Filter by **Continent**, **Country**, and **Year Range**
- Display KPIs:
  - Total CO₂ Emission (Mt)
  - CO₂ per Capita (t)
  - GDP (human-readable format)
  - HDI
  - Energy per Capita (kWh)
- Interactive charts:
  - CO₂ per Capita Trend
  - Total CO₂ Trend
- Hover tooltips for exact data values

📸 **Screenshot**
![Dashboard]
<img width="1907" height="889" alt="image" src="https://github.com/user-attachments/assets/2298f1a8-f919-488a-aef0-9d42c42f267b" />

---

### ✔ **Forecast CO₂ Emission**
- Editable input grid using **Tabulator**
- Parameters:
  - Country
  - Historical Data Window (3 or 5 years)
  - Forecast Year
- "Run Prediction" button (ML-ready: GRU/LSTM integration available)

📸 **Screenshot**
![Forecast]
<img width="1795" height="851" alt="image" src="https://github.com/user-attachments/assets/30f0ebe7-c219-4a05-9ad0-35a04a5c2dd8" />


---

### ✔ **Recommendation Engine**
- Select Country + Target Year
- Adjust Feature Impact (example: GDP)
- Cost Level slider for policy scenarios
- Display simulated recommendations

📸 **Screenshot**
![Recommendation]
<img width="1906" height="467" alt="image" src="https://github.com/user-attachments/assets/69a7d085-6f96-4dbe-bd3a-352a350fd9ed" />


---

## 🏗 Project Structure
```text
Project_CO2/
├─ Models/
│   ├─ best_model_gru3.keras
│   ├─ best_model_gru5.keras
│   ├─ labelencoder_country.save
│   ├─ scaler_minmax.save
│   ├─ model_features.pkl
│   └─ best_xgboost_co2.pkl
├─ df_continent.csv
├─ main_app.py # Main file (routing + layout)
├─ tab_dashboard.py # Dashboard tab
├─ tab_forecast.py # Forecast tab
├─ tab_recommendation.py # Recommendation tab
```

## Command run web on local 
```text
python -m uvicorn main:app --port 8000 --reload &
python -m panel serve dashboard.py --port 5006 --autoreload --show
