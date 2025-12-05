# api_recommend.py  
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import joblib
import numpy as np
import pandas as pd
import os

from es_optimizer import es_optimize_changes

app = FastAPI(title="CO₂ Recommendation API")

MODELS_DIR = "Models"

# ---- MODEL AND SCALER FOR RECOMMEND (must match 9 features!) ----
MODEL_FILE = "Model_XGBoost.joblib"
SCALER_FILE = "scaler_recommend.save"          # <<<< RECOMMEND SCALER ONLY
ENCODER_FILE = "labelencoder_country.save"


def _path(f):
    return os.path.join(MODELS_DIR, f)


# ============================================================
# Load Artifacts
# ============================================================
_model = None
_scaler = None
_encoder = None
_load_error = None

# ---- Load model ----
try:
    _model = joblib.load(_path(MODEL_FILE))
except Exception as e:
    _load_error = f"Failed to load model '{MODEL_FILE}': {e}"

# ---- Load label encoder ----
if _load_error is None:
    try:
        _encoder = joblib.load(_path(ENCODER_FILE))
    except Exception as e:
        _load_error = f"Failed to load encoder '{ENCODER_FILE}': {e}"

# ---- Load recommender scaler (OPTIONAL) ----
if _load_error is None:
    try:
        if os.path.exists(_path(SCALER_FILE)):
            _scaler = joblib.load(_path(SCALER_FILE))
        else:
            print("⚠ No scaler_recommend.save found → using raw values.")
            _scaler = None
    except Exception as e:
        print("⚠ Failed to load recommend scaler:", e)
        _scaler = None


# ============================================================
# FEATURES USED IN RECOMMEND API
# ============================================================
FEATURES = [
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

N_FEATURES = len(FEATURES)


# ============================================================
# Pydantic Schemas
# ============================================================

class FeatureChange(BaseModel):
    feature: str
    min_pct: float
    max_pct: float

class RecommendRequest(BaseModel):
    country: str
    year: int
    target: float
    base_values: Dict[str, float]
    selected_features: List[FeatureChange]

class RecommendResponse(BaseModel):
    status: str
    best_change_pct: Dict[str, float]
    predicted_co2: float
    fitness: float
    message: Optional[str] = None


# ============================================================
# Build Predict Function
# ============================================================
def build_predict_fn(country: str, base_values: Dict[str, float]):

    # --- encode country ---
    try:
        country_code = _encoder.transform([country])[0]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Country '{country}' not recognized."
        )

    # ------------------------------------------------------------
    # Predict function: input percent changes, output CO2 predicted
    # ------------------------------------------------------------
    def predict_fn(percent_change_dict, fixed_features):

        # ---- build feature vector with percent changes ----
        new_values = {}
        for feat, base_val in base_values.items():
            if feat in percent_change_dict:
                pct = percent_change_dict[feat]
                new_values[feat] = base_val * (1 + pct / 100)
            else:
                new_values[feat] = base_val

        try:
            row = [new_values[f] for f in FEATURES]
        except KeyError as e:
            raise HTTPException(status_code=400, detail=f"Missing feature {e}")

        x = np.array(row).reshape(1, -1)

        # --------------------------------------------------------
        # SAFETY: If scaler shape mismatch → disable scaler
        # --------------------------------------------------------
        global _scaler
        if _scaler is not None:
            try:
                if _scaler.n_features_in_ != N_FEATURES:
                    print(f"⚠ Scaler mismatch ({_scaler.n_features_in_} ≠ {N_FEATURES}) → DISABLED")
                    _scaler = None
                else:
                    x = _scaler.transform(x)
            except Exception as e:
                print(f"⚠ Scaler transform error → disabling scaler: {e}")
                _scaler = None

        # ---- predict ----
        try:
            pred = float(_model.predict(x)[0])
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Model prediction error: {e}"
            )

        return pred, x[0]

    return predict_fn


# ============================================================
# Main Endpoint
# ============================================================
@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):

    if _load_error:
        raise HTTPException(status_code=500, detail=_load_error)

    # Validate base_values
    missing = [f for f in FEATURES if f not in req.base_values]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing base_values for required features: {missing}"
        )

    # Validate selected features
    invalid = [fc.feature for fc in req.selected_features if fc.feature not in FEATURES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid features in selected_features: {invalid}"
        )

    feature_selection = [
        dict(feature=fc.feature, min_pct=fc.min_pct, max_pct=fc.max_pct)
        for fc in req.selected_features
    ]

    fixed_features = {
        f: v for f, v in req.base_values.items()
        if f not in [fc.feature for fc in req.selected_features]
    }

    predict_fn = build_predict_fn(req.country, req.base_values)

    # ---- Run Evolution Strategy Optimization ----
    try:
        best_change, best_fitness, best_pred, best_x = es_optimize_changes(
            feature_selection=feature_selection,
            fixed_features=fixed_features,
            predict_fn=predict_fn,
            co2_target=req.target,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization error: {e}")

    return RecommendResponse(
        status="ok",
        best_change_pct=best_change,
        predicted_co2=float(best_pred),
        fitness=float(best_fitness),
        message="Optimization completed successfully."
    )


# ============================================================
# Health Check
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "ok" if _load_error is None else "error",
        "load_error": _load_error,
        "scaler_active": _scaler is not None,
        "model_features": N_FEATURES
    }
