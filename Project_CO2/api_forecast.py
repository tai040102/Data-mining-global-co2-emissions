# api_forecast.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb  # cần import để joblib load model
from tensorflow.keras.models import load_model  # type: ignore

app = FastAPI(title="CO₂ Forecast API")

# ====== CONSTANTS ======
MODELS_DIR = "Models"

# GRU dùng đủ 10 feature (có cả Co2_MtCO2 trong scaler)
FEATURES_GRU = [
    "Co2_MtCO2",
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


# ====== PYDANTIC SCHEMAS ======
class HistoryItem(BaseModel):
    Year: int
    Co2_MtCO2: float
    Population: float
    GDP: float
    Industry_on_GDP: float
    Government_Expenditure_on_Education: float
    Global_Climate_Risk_Index: float
    HDI: float
    Renewable_Energy_Percent: float
    Deforest_Percent: float
    Energy_Capita_kWh: float


class PredictRequest(BaseModel):
    country: str
    predict_year: int
    model_type: str  # "gru" hoặc "xgb"
    history: List[HistoryItem]


# ====== LOAD MODEL / SCALER / ENCODER ======
def _path(name: str) -> str:
    return os.path.join(MODELS_DIR, name)


print(">> Loading models & scalers from:", os.path.abspath(MODELS_DIR))

labelencoder_country = joblib.load(_path("labelencoder_country.save"))
scaler = joblib.load(_path("scaler_minmax.save"))

# GRU models (compile=False để tránh lỗi metrics cũ)
model_gru3 = load_model(_path("best_model_gru3.keras"), compile=False)
model_gru5 = load_model(_path("best_model_gru5.keras"), compile=False)

# XGBoost model + danh sách feature đã train
model_xgb = joblib.load(_path("best_xgboost_co2.pkl"))
xgb_features = joblib.load(_path("model_features.pkl"))  # list[str]

print(">> Models loaded successfully.")


# ====== HELPERS ======
def _predict_gru(country: str, df_hist: pd.DataFrame) -> float:
    """
    Dự báo bằng GRU, dùng 3 hoặc 5 năm lịch sử.
    df_hist: DataFrame đã sort theo Year, chứa đủ FEATURES_GRU.
    """
    df_feat = df_hist[FEATURES_GRU].copy()
    values = df_feat.values  # (T, F)
    time_steps = values.shape[0]

    if time_steps == 3:
        model = model_gru3
    elif time_steps == 5:
        model = model_gru5
    else:
        raise ValueError(f"GRU only supports 3 or 5 time steps, got {time_steps}.")

    # scale input
    X_scaled = scaler.transform(values)  # (T, F)
    X_seq = np.expand_dims(X_scaled, axis=0)  # (1, T, F)

    # encode country
    if country not in labelencoder_country.classes_:
        raise ValueError(f"Country '{country}' not in label encoder.")
    country_code = labelencoder_country.transform([country])[0]
    X_country = np.array([[country_code]], dtype="int32")  # (1,1)

    # predict (scaled)
    y_scaled = model.predict([X_seq, X_country], verbose=0)  # (1,1)

    # inverse scale: nhét vào vị trí Co2_MtCO2, các feature khác = 0
    padded = np.concatenate(
        [y_scaled, np.zeros((1, len(FEATURES_GRU) - 1))], axis=1
    )  # (1,F)
    y_real = scaler.inverse_transform(padded)[0, 0]

    return float(y_real)


def _predict_xgb(df_hist: pd.DataFrame) -> float:
    """
    XGBoost tabular: chỉ dùng 1 row (row cuối cùng user nhập).
    Không phải time-series.
    """
    if df_hist.empty:
        raise ValueError("History dataframe is empty for XGBoost prediction.")

    row = df_hist.tail(1).copy()

    # XGBoost không dùng Year
    if "Year" in row.columns:
        row = row.drop(columns=["Year"])

    # Nếu có cột Co2_MtCO2 vẫn bỏ qua (target)
    if "Co2_MtCO2" in row.columns:
        row = row.drop(columns=["Co2_MtCO2"])

    missing = [c for c in xgb_features if c not in row.columns]
    if missing:
        raise ValueError(
            "Missing required XGBoost features: " + ", ".join(missing)
        )

    # Sắp xếp đúng thứ tự feature như lúc train
    X_input = row[xgb_features]

    y_pred = model_xgb.predict(X_input)[0]
    return float(y_pred)


# ====== API ENDPOINT ======
@app.post("/predict")
def predict_co2(req: PredictRequest):
    df_hist = pd.DataFrame([h.dict() for h in req.history])
    if df_hist.empty:
        return {"status": "error", "message": "History is empty."}

    df_hist = df_hist.sort_values("Year")
    model_type = req.model_type.lower()

    try:
        if model_type == "gru":
            # kiểm tra đủ cột cho GRU
            missing_cols = [c for c in FEATURES_GRU if c not in df_hist.columns]
            if missing_cols:
                return {
                    "status": "error",
                    "message": f"Missing columns for GRU: {', '.join(missing_cols)}",
                }

            n_rows = df_hist.shape[0]
            if n_rows not in (3, 5):
                return {
                    "status": "error",
                    "message": f"GRU needs 3 or 5 rows of history, got {n_rows}.",
                }

            pred = _predict_gru(req.country, df_hist)
            model_used = "GRU (time series)"

        elif model_type == "xgb":
            # XGBoost: chỉ cần >=1 row, chỉ dùng row cuối
            if df_hist.shape[0] < 1:
                return {
                    "status": "error",
                    "message": "XGBoost needs at least 1 row of features.",
                }

            pred = _predict_xgb(df_hist)
            model_used = "XGBoost (tabular)"

        else:
            return {
                "status": "error",
                "message": f"Unknown model_type '{req.model_type}', use 'gru' or 'xgb'.",
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {
        "status": "ok",
        "model": model_used,
        "country": req.country,
        "predict_year": req.predict_year,
        "prediction": pred,
    }
