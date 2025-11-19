from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import joblib
import os
import numpy as np
from sklearn.inspection import permutation_importance
from typing import Dict

app = FastAPI(title="CO2 Prediction API")

# --- Paths ---
MODEL_PATH = "CO2_model_Random_Forest.pkl"
DATA_PATH = "filled_dataset1.csv"

# --- Load model ---
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
model = joblib.load(MODEL_PATH)

# --- Load dataset (for feature names and sensitivity) ---
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)

# Drop unwanted columns if present (match how you trained)
for c in ['Co2_Capita_tCO2','Forest_Area_Percent','Deforest_Percent','Energy_Capita_kWh','Renewable_Energy_Percent']:
    if c in df.columns:
        df = df.drop(columns=[c])

# Target and feature setup (should match training)
TARGET = 'Co2_MtCO2'
if TARGET not in df.columns:
    raise ValueError(f"Target column {TARGET} not found in dataset.")

# Build X used for training (training code removed Year column before preprocess)
X_all = df.drop(columns=[TARGET, 'Year']) if 'Year' in df.columns else df.drop(columns=[TARGET])
y_all = df[TARGET]

# get feature names (raw)
feature_names = list(X_all.columns)

# --- Precompute permutation importance on training set (do once) ---
# This can be expensive depending on data size; we run with n_repeats=5 for speed.
def compute_sensitivity():
    try:
        print("Computing permutation importance (sensitivity) on training set... (may take a while)")
        res = permutation_importance(model, X_all, y_all, n_repeats=5, random_state=42, n_jobs=-1)
        importances = res.importances_mean
        # map to feature names (if pipeline transformed features into many, fallback to raw)
        # We return importance per raw feature (approx) by using ColumnTransformer.get_feature_names_out if available
        try:
            pre = model.named_steps['preprocessor']
            # attempt to get output feature names (sklearn >=1.0)
            out_names = pre.get_feature_names_out(feature_names)
            # If out_names length > len(feature_names) then we need to aggregate
            # Fallback: aggregate by prefix (like num__col or cat__onehot__col)
            importances_map = {}
            if len(out_names) == len(importances):
                # attempt to aggregate to raw features by splitting on '__' or first token
                for out_name, imp in zip(out_names, importances):
                    # try to map back to raw feature by splitting
                    raw = out_name.split('__')[0]
                    importances_map.setdefault(raw, 0.0)
                    importances_map[raw] += float(imp)
            else:
                # fallback to raw feature list
                for i, fn in enumerate(feature_names):
                    importances_map[fn] = float(importances[i]) if i < len(importances) else 0.0
        except Exception:
            # fallback: map directly to raw feature_names (truncate if needed)
            importances_map = {}
            for i, fn in enumerate(feature_names):
                importances_map[fn] = float(importances[i]) if i < len(importances) else 0.0

        # normalize to relative importance
        total = sum(abs(v) for v in importances_map.values()) or 1.0
        importances_norm = {k: float(v / total) for k, v in importances_map.items()}
        return importances_norm
    except Exception as e:
        print("Error computing sensitivity:", e)
        return {fn: 0.0 for fn in feature_names}

SENSITIVITY = compute_sensitivity()

# ---- Pydantic model for input ----
class CO2Input(BaseModel):
    Country: str
    ISO_Code: str | None = None
    Year: int
    GDP: float
    Population: float
    Industry_on_GDP: float
    HDI: float
    Government_Expenditure_on_Education: float
    Global_Climate_Risk_Index: float
    Area_ha: float
    Forest_Area_ha: float
    Deforest_Area_ha: float
    Energy_MWh: float
    Renewable_Energy_MWh: float

@app.post("/predict")
def predict(input_data: CO2Input):
    # convert to DataFrame, drop Year if model doesn't expect it
    df_in = pd.DataFrame([input_data.dict()])
    if 'Year' in df_in.columns:
        df_in = df_in.drop(columns=['Year'])
    # ensure columns order contains all feature_names, fill missing with nan
    for col in feature_names:
        if col not in df_in.columns:
            df_in[col] = np.nan
    df_in = df_in[feature_names]
    pred = model.predict(df_in)[0]
    return {"CO2_pred": float(pred)}

@app.post("/sensitivity")
def sensitivity(_: dict = None) -> Dict[str, float]:
    # return precomputed sensitivity
    return SENSITIVITY

@app.get("/features")
def features():
    return {"features": feature_names}
