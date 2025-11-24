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
<img width="1908" height="790" alt="image" src="https://github.com/user-attachments/assets/e12ebf52-d88b-46dd-8de5-cb579d4b4caf" />

---

### ✔ **Recommendation Engine**
- Select Country + Target Year
- Adjust Feature Impact (example: GDP)
- Cost Level slider for policy scenarios
- Display simulated recommendations

📸 **Screenshot**
![Recommendation]
<img width="1916" height="711" alt="image" src="https://github.com/user-attachments/assets/57d5c275-4ed4-4fed-a7e9-89e4d0d0a440" />

---

## 🏗 Project Structure
├── t_main_app.py # Main file (routing + layout)
├── tab_dashboard.py # Dashboard tab
├── tab_forecast.py # Forecast tab
├── tab_recommendation.py # Recommendation tab
├── df_continent.csv # Dataset
