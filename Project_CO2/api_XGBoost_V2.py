# api_XGBoost.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Optional, List
import os
import joblib
import numpy as np
import pandas as pd

app = FastAPI(title="CO2 XGBoost API (Final)")


# 1. CẤU HÌNH 
MODELS_DIR = "Models"
MODEL_NAME = "Model_XGBoost_Final.joblib"
ENCODER_NAME = "Encoder_Country_Final.joblib"
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

def _path(filename: str) -> str:
    return os.path.join(MODELS_DIR, filename)

# ---------- Pydantic schema ----------
class PredictXGBRequest(BaseModel):
    country: str
    features: Dict[str, float]

class PredictXGBResponse(BaseModel):
    status: str
    prediction: float
    country: Optional[str] = None
    message: Optional[str] = None

# ---------- Load artifacts ----------
_model = None
_encoder = None
_load_error = None

print(">> Loading XGBoost artifacts...")

# 1. Load Model
try:
    _model = joblib.load(_path(MODEL_NAME))
    print(f"Loaded model: {MODEL_NAME}")
except Exception as e:
    _load_error = f"Failed to load model '{MODEL_NAME}': {e}"

# 2. Load Country Encoder
if _load_error is None:
    try:
        if os.path.exists(_path(ENCODER_NAME)):
            _encoder = joblib.load(_path(ENCODER_NAME))
            print(f"Loaded encoder: {ENCODER_NAME}")
        else:
            _load_error = f"Encoder file '{ENCODER_NAME}' not found!"
    except Exception as e:
        _load_error = f"Failed to load encoder '{ENCODER_NAME}': {e}"

if _load_error:
    print(f"Error: {_load_error}")

# ---------- Helper Function ----------
def _prepare_input_df(input_features: Dict[str, float], country_name: str) -> pd.DataFrame:
    """
    Tạo DataFrame đúng thứ tự cột: [FEATURE_CORE] + [Country_Encoded]
    """
    # 1. Lấy dữ liệu theo đúng thứ tự FEATURE_CORE
    # Nếu thiếu feature nào thì điền 0.0
    data_ordered = {}
    for feat in FEATURE_CORE:
        data_ordered[feat] = input_features.get(feat, 0.0)
    
    # 2. Tạo DataFrame từ list feature cơ bản
    df = pd.DataFrame([data_ordered])
    
    # 3. Xử lý Encode Country (Thêm vào cuối DataFrame)
    # Logic: Model train = [Features...] + [Country_Encoded]
    if _encoder is not None:
        try:
            if hasattr(_encoder, 'classes_') and country_name in _encoder.classes_:
                encoded_val = _encoder.transform([country_name])[0]
                df['Country_Encoded'] = encoded_val
            else:
                df['Country_Encoded'] = -1
        except:
            df['Country_Encoded'] = -1
    else:
        df['Country_Encoded'] = 0

    return df

# ---------- Endpoint ----------
@app.post("/predict_xgboost_v2", response_model=PredictXGBResponse)
def predict_xgboost(req: PredictXGBRequest):
    if _load_error:
        raise HTTPException(status_code=500, detail=_load_error)
    
    try:
        # 1. Chuẩn bị dữ liệu
        input_df = _prepare_input_df(req.features, req.country)
        
        # 2. Dự báo 
        pred = _model.predict(input_df)
        
        # 3. Kết quả
        pred_val = float(pred[0])
        
        return PredictXGBResponse(
            status="ok", 
            prediction=pred_val, 
            country=req.country,
            message="Success"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Prediction error: {str(e)}")

# Health Check
@app.get("/health")
def health():
    return {
        "status": "ok" if _load_error is None else "error",
        "model_loaded": _model is not None,
        "encoder_loaded": _encoder is not None,
        "features_used": FEATURE_CORE
    }