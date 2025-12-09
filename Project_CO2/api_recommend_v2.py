# api_recommend_v2.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import joblib
import os
import traceback
import pandas as pd
import numpy as np

from es_optimizer import es_optimize_changes

app = FastAPI(title="CO₂ Recommendation API v2")

# ---------------------------
# Paths and artifacts
# ---------------------------
MODELS_DIR = "Models"
MODEL_FILE = "Model_XGBoost_Final.joblib"
DATA_FILE = "/root/Data-mining-global-co2-emissions/Project_CO2/data/historical_data.csv"
ENCODER_FILE = "Encoder_Country_Final.joblib"

def _path(name: str) -> str:
    return os.path.join(MODELS_DIR, name)

# Load model
try:
    model_xgb = joblib.load(_path(MODEL_FILE))
    print(f">> Loaded model: {_path(MODEL_FILE)}")
except Exception as e:
    model_xgb = None
    load_error = f"Failed to load model '{MODEL_FILE}': {e}"
    print(load_error)

# Load country encoder if exists
try:
    if os.path.exists(_path(ENCODER_FILE)):
        le_xgb = joblib.load(_path(ENCODER_FILE))
        print(f">> Loaded encoder: {_path(ENCODER_FILE)}")
    else:
        le_xgb = None
except Exception as e:
    le_xgb = None
    print(f"Warning: failed to load encoder '{ENCODER_FILE}': {e}")

# Example core features (the features user can change)
FEATURE_CORE = [
    "Population",
    "GDP",
    "Industry_on_GDP",
    "Government_Expenditure_on_Education",
    "Global_Climate_Risk_Index",
    "HDI",
    "Renewable_Energy_Percent",
    "Deforest_Percent",
    "Energy_Capita_kWh",
]

# ---------------------------
# Schemas
# ---------------------------
class FeatureChange(BaseModel):
    feature: str
    min_pct: float
    max_pct: float

class RecommendRequest(BaseModel):
    year: int
    country_name: str
    co2_target: float
    fixed_features: Dict[str, float]
    feature_selection: List[FeatureChange]

class RecommendResponse(BaseModel):
    status: str
    best_change_pct: Dict[str, float]
    predicted_co2: float
    fitness: float
    message: Optional[str] = None

# ---------------------------
# Predict function used in optimizer
# ---------------------------
import pandas as pd

# Giả sử bạn có file historical_data.csv với cột: Country, Year, FEATURE_CORE...

def load_sequence_data(country, target_year, seq_len=3):
    # Lấy dữ liệu seq_len năm trước target_year
    df = pd.read_csv(DATA_FILE)    
    years = [target_year - i - 1 for i in reversed(range(seq_len))]    
    seq_data = df[(df['Country'] == country) & (df['Year'].isin(years))].sort_values('Year')
    
    if len(seq_data) < seq_len:
        print("Không đủ dữ liệu sequence, chỉ sử dụng dữ liệu hiện có.")
    
    print("\nSequence data:")
    print(seq_data)
    return seq_data

def build_predict_fn(model, le, seq_data):
    def predict_fn(indiv_changes: Dict[str, float], fixed_features: Dict[str, float], country_name: str):
        x_values = {}
        x_full = []

        for f in FEATURE_CORE:
            if f in indiv_changes:
                original_val = seq_data[f].to_numpy()[-1]
                pct = indiv_changes[f] / 100.0
                new_val = original_val * (1 + pct)
                x_values[f] = new_val
                x_full.append(new_val)
            else:
                new_val = fixed_features[f]
                x_values[f] = new_val
                x_full.append(new_val)

        # Build dataframe in proper order
        x_df_scale = pd.DataFrame([x_full], columns=FEATURE_CORE)

        # Encode country if possible
        if le is not None and country_name in le.classes_:
            x_df_scale['Country_Encoded'] = le.transform([country_name])
        else:
            x_df_scale['Country_Encoded'] = -1

        # Predict
        pred = model.predict(x_df_scale)[0]

        return pred, x_values

    return predict_fn

# ---------------------------
# API endpoint
# ---------------------------
@app.post("/recommend_v2", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    if model_xgb is None:
        raise HTTPException(status_code=500, detail="Model not loaded.")

    # Validate fixed_features includes all FEATURE_CORE
    # missing = [f for f in FEATURE_CORE if f not in req.fixed_features]
    # if missing:
    #     raise HTTPException(status_code=400, detail=f"Missing fixed_features: {missing}")

    # Prepare feature selection dicts
    feature_selection = [{"feature": f.feature, "min_pct": f.min_pct, "max_pct": f.max_pct} for f in req.feature_selection]

    # seq_data can come from historical dataset; here we assume last value needed
    # In practice, load your time series data
    seq_data = load_sequence_data(req.country_name, req.year)
    # Build prediction function
    predict = build_predict_fn(model_xgb, le_xgb, seq_data)

    # Run evolutionary optimizer
    try:
        best_change, best_fitness, best_pred, best_x = es_optimize_changes(
            feature_selection=feature_selection,
            fixed_features=req.fixed_features,
            predict_fn=predict,
            co2_target=req.co2_target,
            country_name=req.country_name
        )
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Optimization error: {e}\n{tb}")

    return RecommendResponse(
        status="ok",
        best_change_pct=best_change,
        predicted_co2=float(best_pred),
        fitness=float(best_fitness),
        message="Optimization completed successfully."
    )

@app.get("/health")
def health():
    return {
        "status": "ok" if model_xgb else "error",
        "model_loaded": model_xgb is not None,
        "encoder_loaded": le_xgb is not None
    }
