# api_forecast.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os

import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model  # type: ignore

app = FastAPI(title="CO₂ Forecast API – Scenario 1 (GRU 5 years)")

# ====== CONSTANTS ======
MODELS_DIR = "Models"

# Danh sách feature giống FEATURE trong main.py
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
    Co2_MtCO2: Optional[float] = None
    Population: Optional[float] = None
    GDP: Optional[float] = None
    Industry_on_GDP: Optional[float] = None
    Government_Expenditure_on_Education: Optional[float] = None
    Global_Climate_Risk_Index: Optional[float] = None
    HDI: Optional[float] = None
    Renewable_Energy_Percent: Optional[float] = None
    Deforest_Percent: Optional[float] = None
    Energy_Capita_kWh: Optional[float] = None


class PredictRequest(BaseModel):
    country: str
    predict_year: int
    # Giữ lại field để tương thích, nhưng API hiện chỉ hỗ trợ GRU (Scenario 1)
    model_type: str = "gru"
    history: List[HistoryItem]


# ====== LOAD MODEL / SCALER / ENCODER ======
def _path(name: str) -> str:
    return os.path.join(MODELS_DIR, name)


print(">> Loading models & scalers from:", os.path.abspath(MODELS_DIR))

# Giống main.py: scaler_quantile + labelencoder_country + GRU5
labelencoder_country = joblib.load(_path("labelencoder_country.save"))
scaler = joblib.load(_path("scaler_quantile.save"))
model_gru5 = load_model(_path("best_model_gru5_final.keras"), compile=False)

print(">> Scenario 1 GRU-5Y model loaded successfully.")


# ====== HELPERS ======
def _predict_gru_5y(country: str, df_hist: pd.DataFrame) -> float:
    """
    Scenario 1:
    - Dùng 5 năm lịch sử (time-series).
    - Áp dụng log1p -> scaler_quantile -> GRU -> inverse_transform -> expm1
      giống hàm predict_co2 trong main.py.
    """

    # Sort theo Year và chắc chắn chỉ lấy đúng 5 năm gần nhất
    df_hist = df_hist.sort_values("Year").tail(5)

    # Lấy đúng 10 feature theo đúng thứ tự
    seq_df = df_hist[FEATURES_GRU].copy()

    # log1p giống main.py
    seq_df_log = np.log1p(seq_df)

    # scale bằng scaler_quantile
    seq_scaled = scaler.transform(seq_df_log)        # (5, F)
    X_new = np.expand_dims(seq_scaled, axis=0)       # (1, 5, F)

    # encode country
    if country not in labelencoder_country.classes_:
        raise ValueError(f"Country '{country}' not in label encoder.")

    country_code = labelencoder_country.transform([country])[0]
    X_country = np.array([[country_code]], dtype="int32")  # (1,1)

    # predict (scaled-log space)
    y_pred_scaled = model_gru5.predict([X_new, X_country], verbose=0)  # (1,1)

    # inverse scale: ghép y_pred_scaled + zeros rồi inverse_transform
    num_feature = len(FEATURES_GRU)
    padded = np.concatenate(
        [y_pred_scaled, np.zeros((1, num_feature - 1))],
        axis=1,
    )  # (1,F)
    y_pred_real_log = scaler.inverse_transform(padded)[0, 0]

    # expm1 để quay lại scale ban đầu
    y_pred_real = np.expm1(y_pred_real_log)

    # ép về float để tránh kiểu numpy scalar
    return float(y_pred_real)


# ====== API ENDPOINT ======
@app.post("/predict")
def predict_co2(req: PredictRequest):
    # Convert history sang DataFrame
    df_hist = pd.DataFrame([h.dict() for h in req.history])
    if df_hist.empty:
        return {"status": "error", "message": "History is empty."}

    # Sort theo Year
    df_hist = df_hist.sort_values("Year")

    # Chỉ hỗ trợ Scenario 1 = GRU (5-year time series)
    model_type = (req.model_type or "gru").lower()
    if model_type != "gru":
        return {
            "status": "error",
            "message": (
                f"This API currently supports only Scenario 1 (GRU 5 years). "
                f"Received model_type='{req.model_type}'. Please use 'gru'."
            ),
        }

    # Kiểm tra đủ cột cho GRU
    missing_cols = [c for c in FEATURES_GRU if c not in df_hist.columns]
    if missing_cols:
        return {
            "status": "error",
            "message": f"Missing columns for GRU: {', '.join(missing_cols)}",
        }

    # Kiểm tra đúng 5 dòng history (fit cứng với tab_forecast)
    n_rows = df_hist.shape[0]
    if n_rows != 5:
        return {
            "status": "error",
            "message": f"Scenario 1 requires EXACTLY 5 rows of history, got {n_rows}.",
        }

    # Nếu có ô trống thì báo FE fill hết
    if df_hist[FEATURES_GRU].isnull().any().any():
        return {
            "status": "error",
            "message": (
                "History has missing feature values. "
                "Please fill all empty cells before running prediction."
            ),
        }

    # ===== Chạy Scenario 1 – GRU 5 years =====
    try:
        pred = _predict_gru_5y(req.country, df_hist)

        # 🔴 chặn NaN / Inf để không trả về giá trị JSON không hợp lệ
        if np.isnan(pred) or np.isinf(pred):
            return {
                "status": "error",
                "message": (
                    "Model returned an invalid value (NaN or Inf). "
                    "Please double-check your input features."
                ),
            }

    except Exception as e:
        # mọi lỗi khác đều trả về dạng text bình thường
        return {"status": "error", "message": str(e)}

    return {
        "status": "ok",
        "scenario": "Scenario 1 – GRU (5-year time series)",
        "model": "GRU-5Y",
        "country": req.country,
        "predict_year": req.predict_year,
        "prediction": pred,
    }
