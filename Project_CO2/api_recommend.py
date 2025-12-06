# api_recommend.py (robust version)
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional
import joblib
import numpy as np
import os
import traceback

from es_optimizer import es_optimize_changes

app = FastAPI(title="CO₂ Recommendation API")

MODELS_DIR = "Models"
MODEL_FILE = "Model_XGBoost.joblib"
FEATURES_FILE = "model_features.joblib"      # list of feature names used by the XGBoost model
SCALER_FILE = "scaler_quantile.save"         # optional scaler (may or may not exist)
ENCODER_FILE = "labelencoder_country.save"

def _path(name: str) -> str:
    return os.path.join(MODELS_DIR, name)

# ---------------------------------------------------------
# Load artifacts (model, feature-list, scaler, encoder)
# ---------------------------------------------------------
_model = None
_model_feature_names = None
_scaler = None
_encoder = None
_load_error = None

# load model
try:
    _model = joblib.load(_path(MODEL_FILE))
    print(f">> Loaded model: {_path(MODEL_FILE)}")
except Exception as e:
    _load_error = f"Failed to load model '{MODEL_FILE}': {e}"
    print(_load_error)

# load feature list if present (very important)
if _load_error is None:
    try:
        if os.path.exists(_path(FEATURES_FILE)):
            _model_feature_names = joblib.load(_path(FEATURES_FILE))
            if not isinstance(_model_feature_names, (list, tuple)):
                _model_feature_names = list(_model_feature_names)
            print(f">> Loaded model feature list ({len(_model_feature_names)} features).")
        else:
            print(f">> No feature-list file found at {_path(FEATURES_FILE)} — will attempt best-effort.")
            _model_feature_names = None
    except Exception as e:
        _load_error = f"Failed to load feature list '{FEATURES_FILE}': {e}"
        print(_load_error)

# load scaler if present
if _load_error is None:
    try:
        if os.path.exists(_path(SCALER_FILE)):
            _scaler = joblib.load(_path(SCALER_FILE))
            print(f">> Loaded scaler: {_path(SCALER_FILE)}")
        else:
            _scaler = None
            print(">> No scaler file for recommend (ok).")
    except Exception as e:
        print(f"Warning: failed to load scaler '{SCALER_FILE}': {e}")
        _scaler = None

# load encoder if present
if _load_error is None:
    try:
        if os.path.exists(_path(ENCODER_FILE)):
            _encoder = joblib.load(_path(ENCODER_FILE))
            print(f">> Loaded encoder: {_path(ENCODER_FILE)}")
        else:
            _encoder = None
            print(">> No encoder file found (country encoding will be skipped).")
    except Exception as e:
        print(f"Warning: failed to load encoder '{ENCODER_FILE}': {e}")
        _encoder = None

if _load_error:
    print("api_recommend load error:", _load_error)

# ---------------------------------------------------------
# Default FEATURES used inside recommendation UI (9 features)
# This should match the features you display in tab_recommendation.
# ---------------------------------------------------------
BASE_FEATURES = [
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

# helper to determine model expected features list (if available)
def _get_model_feature_list():
    # priority: model_features.joblib (explicit)
    if _model_feature_names is not None:
        return list(_model_feature_names)
    # else try model.n_features_in_ and guess names
    try:
        n = getattr(_model, "n_features_in_", None)
        if n is not None:
            # If n == len(BASE_FEATURES): we assume those
            if n == len(BASE_FEATURES):
                return list(BASE_FEATURES)
            # if n == len(BASE_FEATURES)+1 and includes Co2 -> include it as first
            if n == len(BASE_FEATURES) + 1:
                return ["Co2_MtCO2"] + list(BASE_FEATURES)
            # fallback: return BASE_FEATURES (best-effort) but warn
            print(f"⚠ Model reports n_features_in_={n} — fallback to BASE_FEATURES")
            return list(BASE_FEATURES)
    except Exception:
        pass
    # default fallback
    return list(BASE_FEATURES)

_model_expected_features = _get_model_feature_list()
_model_n_features = len(_model_expected_features)
print(f">> Model expected features (inferred): {_model_expected_features} (n={_model_n_features})")

# ---------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------
class FeatureChange(BaseModel):
    feature: str
    min_pct: float
    max_pct: float

class RecommendRequest(BaseModel):
    country: str
    year: int
    target: float                        # co2 target (MtCO2)
    base_values: Dict[str, float]        # current year values for features (can include Co2_MtCO2 or not)
    selected_features: List[FeatureChange]

class RecommendResponse(BaseModel):
    status: str
    best_change_pct: Dict[str, float]
    predicted_co2: float
    fitness: float
    message: Optional[str] = None

# ---------------------------------------------------------
# Build predict function used by es_optimizer
# - It will construct the feature vector matching model's expected features.
# - If model expects Co2_MtCO2 and base_values does not include it, we'll use req.target.
# - Scaler will be applied only if its n_features_in_ matches vector length.
# ---------------------------------------------------------
def build_predict_fn(country: str, base_values: Dict[str, float], co2_target_in_req: float):
    # optional: check/encode country (not used directly in prediction here, left for completeness)
    if _encoder is not None:
        try:
            _encoder.transform([country])
        except Exception:
            # don't fail here; just warn and continue
            print(f"⚠ Country '{country}' not recognized by encoder (continuing).")

    # prepare a canonical base_values mapping (use float)
    # copy to avoid mutating caller
    base_vals = {k: float(v) for k, v in base_values.items()}

    # If model expects Co2_MtCO2 as feature and base_values doesn't include it,
    # use co2_target_in_req as the Co2_MtCO2 value (per your note).
    expects_co2 = "Co2_MtCO2" in _model_expected_features
    if expects_co2 and ("Co2_MtCO2" not in base_vals):
        base_vals["Co2_MtCO2"] = float(co2_target_in_req)

    # inner predict_fn signature matches es_optimizer.predict_fn(percent_change_dict, fixed_features)
    def predict_fn(percent_change_dict, fixed_features):
        # build new_values by applying percent changes to base_vals
        new_values = {}
        # Use union of keys: ensure all expected model features exist
        for feat in _model_expected_features:
            # base value retrieval: if provided in base_vals use it, else try fixed_features, else error
            if feat in base_vals:
                base_val = base_vals[feat]
            elif feat in fixed_features:
                base_val = fixed_features[feat]
            else:
                raise ValueError(f"Missing base value for model feature '{feat}'")

            if feat in percent_change_dict:
                pct = percent_change_dict[feat]
                # percent is expected as e.g. -10 .. 10 (not fraction)
                new_values[feat] = base_val * (1.0 + float(pct) / 100.0)
            else:
                new_values[feat] = base_val

        # create row in model's expected column order
        row = [new_values[f] for f in _model_expected_features]
        x = np.array(row, dtype=float).reshape(1, -1)

        # optionally apply scaler if present and matches shape
        if _scaler is not None:
            try:
                n_in = getattr(_scaler, "n_features_in_", None)
                if n_in is None:
                    # unknown scaler input size: try transform but catch shape errors
                    x_scaled = _scaler.transform(x)
                else:
                    if n_in != x.shape[1]:
                        # mismatch -> disable scaler for future calls and use raw x
                        print(f"⚠ Scaler expects {n_in} features but input has {x.shape[1]}. Disabling scaler.")
                        # disable scaler globally to avoid repeated errors
                        # (note: this mutates module-level _scaler)
                        globals()["_scaler"] = None
                        x_scaled = x
                    else:
                        x_scaled = _scaler.transform(x)
            except Exception as e:
                print(f"⚠ Scaler transform error: {e}. Disabling scaler.")
                globals()["_scaler"] = None
                x_scaled = x
        else:
            x_scaled = x

        # final prediction using model
        try:
            # many xgboost wrappers accept numpy array of shape (1,n)
            pred_raw = _model.predict(x_scaled)
            pred_val = float(np.asarray(pred_raw).reshape(-1)[0])
        except Exception as e:
            # raise to be caught by endpoint and returned nicely
            tb = traceback.format_exc()
            raise RuntimeError(f"Model prediction error: {e}\n{tb}")

        return pred_val, x_scaled[0].tolist()

    return predict_fn

# ---------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------
@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    # early load error
    if _load_error:
        raise HTTPException(status_code=500, detail=_load_error)

    # Input validation: base_values must contain values for all model-expected features except possibly Co2_MtCO2
    missing = []
    for feat in _model_expected_features:
        # if model expects Co2 and it's ok to miss (we will use req.target) then skip
        if feat == "Co2_MtCO2" and "Co2_MtCO2" not in req.base_values:
            # allowed: will substitute by req.target
            continue
        if feat not in req.base_values:
            missing.append(feat)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing base_values for required features: {missing}")

    # validate selected features: they must be subset of BASE_FEATURES (the features user can modify)
    invalid = [fc.feature for fc in req.selected_features if fc.feature not in BASE_FEATURES and fc.feature != "Co2_MtCO2"]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid features in selected_features: {invalid}")

    # prepare feature_selection and fixed_features for ES optimizer
    feature_selection = [{"feature": fc.feature, "min_pct": float(fc.min_pct), "max_pct": float(fc.max_pct)} for fc in req.selected_features]

    fixed_features = {}
    # fixed_features are base_values not selected for change; pass only keys the model expects (and convert to float)
    for k, v in req.base_values.items():
        if k not in [fs["feature"] for fs in feature_selection]:
            fixed_features[k] = float(v)

    # build predict function (note: passes co2 target in case model expects Co2_MtCO2 feature)
    predict_fn = build_predict_fn(req.country, req.base_values, req.target)

    # call evolutionary optimizer
    try:
        best_change, best_fitness, best_pred, best_x = es_optimize_changes(
            feature_selection=feature_selection,
            fixed_features=fixed_features,
            predict_fn=predict_fn,
            co2_target=req.target
        )
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Optimization error: {e}\n{tb}")

    # success
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
        "status": "ok" if _load_error is None else "error",
        "load_error": _load_error,
        "model_expected_features": _model_expected_features,
        "model_n_features": _model_n_features,
        "scaler_active": _scaler is not None
    }
