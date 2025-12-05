# api_XGBoost.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Optional, List
import os
import joblib
import numpy as np
import pandas as pd

app = FastAPI(title="CO2 XGBoost API")

MODELS_DIR = "Models"
MODEL_NAME = "Model_XGBoost.joblib"      # chỉnh nếu cần
FEATURES_NAME = "model_features.joblib"  # hoặc model_features.pkl
# optional scaler names (nếu bạn đã lưu scaler cho XGB)
SCALER_MINMAX = "scaler_minmax.save"
SCALER_QUANTILE = "scaler_quantile.save"

def _path(filename: str) -> str:
    return os.path.join(MODELS_DIR, filename)

# ---------- Pydantic schema ----------
class PredictXGBRequest(BaseModel):
    country: Optional[str] = None
    # features: dict mapping feature name -> numeric value
    features: Dict[str, float]

class PredictXGBResponse(BaseModel):
    status: str
    prediction: float
    country: Optional[str] = None
    message: Optional[str] = None

# ---------- Load artifacts (once) ----------
_model = None
_model_feature_names = None
_scaler = None
_load_error = None

try:
    _model = joblib.load(_path(MODEL_NAME))
except Exception as e:
    _load_error = f"Failed to load model '{MODEL_NAME}': {e}"

# load feature list (joblib or pickle)
if _load_error is None:
    try:
        _model_feature_names = joblib.load(_path(FEATURES_NAME))
        if not isinstance(_model_feature_names, (list, tuple)):
            _model_feature_names = list(_model_feature_names)
    except Exception as e:
        # try .pkl fallback
        try:
            import pickle
            with open(_path(FEATURES_NAME), "rb") as f:
                _model_feature_names = pickle.load(f)
            if not isinstance(_model_feature_names, (list, tuple)):
                _model_feature_names = list(_model_feature_names)
        except Exception as e2:
            _load_error = f"Failed to load feature list '{FEATURES_NAME}': {e2}"

# optional scaler (prefer minmax then quantile)
if _load_error is None:
    try:
        if os.path.exists(_path(SCALER_MINMAX)):
            _scaler = joblib.load(_path(SCALER_MINMAX))
        elif os.path.exists(_path(SCALER_QUANTILE)):
            _scaler = joblib.load(_path(SCALER_QUANTILE))
        else:
            _scaler = None
    except Exception as e:
        # don't fail the whole service because scaler missing; just warn
        _scaler = None
        print("Warning: failed to load scaler:", e)

if _load_error:
    print("api_XGBoost load error:", _load_error)
else:
    print("api_XGBoost loaded model and features.")

# ---------- Helper: prepare input ----------
def _prepare_input_dict(feature_names: List[str], input_features: Dict[str, float]) -> pd.DataFrame:
    """
    Given required feature_names and a dict input_features,
    return a DataFrame (1 row) with columns in correct order and numeric dtype.
    Missing columns are filled with 0.0.
    """
    df = pd.DataFrame([input_features])
    # add any missing columns as 0.0
    missing = [c for c in feature_names if c not in df.columns]
    for c in missing:
        df[c] = 0.0
    # reorder columns
    df = df[feature_names]
    # convert to float
    df = df.astype(float)
    return df

# ---------- Endpoint ----------
@app.post("/predict_xgboost", response_model=PredictXGBResponse)
def predict_xgboost(req: PredictXGBRequest):
    # check model loaded
    if _load_error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_load_error)
    if _model is None or _model_feature_names is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model or features not loaded.")

    # basic validation
    if not isinstance(req.features, dict) or len(req.features) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="`features` must be a non-empty dict.")

    # prepare DataFrame (1 row)
    try:
        input_df = _prepare_input_dict(_model_feature_names, req.features)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to prepare input: {e}")

    # optional scaling
    try:
        if _scaler is not None:
            # scaler might expect 2D array
            X_in = _scaler.transform(input_df)
        else:
            X_in = input_df.values
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to scale input: {e}")

    # predict
    try:
        # some xgboost wrappers accept DataFrame directly, some need numpy
        # try model.predict(X_in) and fallback to model.predict(pd.DataFrame(...))
        try:
            pred = _model.predict(X_in)
        except Exception:
            pred = _model.predict(pd.DataFrame(X_in, columns=_model_feature_names))

        # get scalar float
        pred_val = float(np.asarray(pred).reshape(-1)[0])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Model prediction error: {e}")

    return PredictXGBResponse(status="ok", prediction=pred_val, country=req.country)


# health endpoint
@app.get("/health")
def health():
    ok = (_load_error is None) and (_model is not None) and (_model_feature_names is not None)
    return {"status": "ok" if ok else "error", "load_error": _load_error}
