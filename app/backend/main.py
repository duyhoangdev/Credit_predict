import json
import os

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import database, models


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Loan Approval DSS API",
    description="Backend API for the Loan Approval Decision Support System",
    version="2.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "../models")


def load_artifact(filename, loader="joblib"):
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None

    if loader == "joblib":
        return joblib.load(path)

    if loader == "json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


# Preferred artifact: full sklearn Pipeline with preprocessing + model.
loan_pipeline = load_artifact("loan_pipeline.pkl")

# Backward-compatible artifacts for older exports.
legacy_lr_model = None if loan_pipeline is not None else load_artifact("lr_model.pkl")
legacy_preprocessor = None if loan_pipeline is not None else load_artifact("preprocessor_lr.pkl")
legacy_scaler = None if loan_pipeline is not None else load_artifact("scaler_lr.pkl")
feature_names = load_artifact("feature_names.json", "json")
model_input_features = load_artifact("model_input_features.json", "json")
clip_params = load_artifact("clip_params.json", "json")

if loan_pipeline is None and legacy_lr_model is None:
    legacy_lr_model = load_artifact("loan_model.pkl")
    if legacy_lr_model is not None:
        print("Using legacy loan_model.pkl. Re-export loan_pipeline.pkl from the notebook when possible.")


class LoanApplication(BaseModel):
    loan_amnt: float = Field(..., gt=0, description="Loan amount")
    int_rate: float = Field(..., gt=0, le=30, description="Interest rate")
    grade: str = Field(..., pattern="^[A-G]$", description="Credit grade")
    annual_inc: float = Field(..., gt=0, description="Annual income")
    dti: float = Field(..., ge=0, description="Debt-to-income ratio")
    home_ownership: str = Field(..., description="Home ownership status")
    verification_status: str = Field(..., description="Income verification status")
    emp_length: str = Field(default="Unknown", description="Employment length")
    term_numeric: float = Field(default=36.0, description="Loan term in months")
    delinq_2yrs: float = Field(default=0.0, ge=0, description="Delinquencies in last 2 years")
    total_acc: float = Field(default=10.0, ge=0, description="Total credit accounts")


DEFAULT_MODEL_INPUT_FEATURES = [
    "loan_amnt",
    "int_rate",
    "grade",
    "emp_length",
    "home_ownership",
    "verification_status",
    "delinq_2yrs",
    "total_acc",
    "term_numeric",
    "annual_inc_clipped",
    "dti_clipped",
]


def build_raw_input(data: LoanApplication) -> pd.DataFrame:
    """Build the raw model input expected by the exported sklearn Pipeline."""
    inc_clip = clip_params.get("INC_P99", 250000.0) if clip_params else 250000.0
    dti_clip = clip_params.get("DTI_P99", 39.99) if clip_params else 39.99

    raw = {
        "loan_amnt": data.loan_amnt,
        "int_rate": data.int_rate,
        "grade": data.grade,
        "emp_length": data.emp_length,
        "home_ownership": data.home_ownership,
        "verification_status": data.verification_status,
        "delinq_2yrs": data.delinq_2yrs,
        "total_acc": data.total_acc,
        "term_numeric": data.term_numeric,
        "annual_inc_clipped": min(data.annual_inc, inc_clip),
        "dti_clipped": min(data.dti, dti_clip),
    }

    df = pd.DataFrame([raw])
    expected_features = model_input_features or DEFAULT_MODEL_INPUT_FEATURES

    for col in expected_features:
        if col not in df.columns:
            df[col] = 0

    return df[expected_features]


def build_legacy_scaled_input(data: LoanApplication) -> pd.DataFrame:
    """Fallback for old exports that saved encoder/scaler/model as separate files."""
    df = build_raw_input(data)

    if legacy_preprocessor is not None:
        transformed = legacy_preprocessor.transform(df)
        return pd.DataFrame(transformed)

    grade_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
    df["grade"] = df["grade"].map(grade_map).fillna(3)
    df = pd.get_dummies(
        df,
        columns=[c for c in ["home_ownership", "verification_status", "emp_length"] if c in df.columns],
        drop_first=True,
        dtype=int,
    )

    if feature_names:
        for col in feature_names:
            if col not in df.columns:
                df[col] = 0
        df = df[feature_names]

    if legacy_scaler is not None:
        df = pd.DataFrame(legacy_scaler.transform(df.values), columns=df.columns)

    return df


def get_active_model():
    if loan_pipeline is not None:
        return loan_pipeline
    return legacy_lr_model


@app.get("/")
def read_root():
    active_model = get_active_model()
    return {
        "service": "Loan Approval DSS API v2.1",
        "model_status": "Loaded" if active_model is not None else "Not found",
        "pipeline_loaded": loan_pipeline is not None,
        "endpoints": ["/api/predict", "/api/health"],
    }


@app.get("/api/health")
def health_check():
    active_model = get_active_model()
    return {
        "status": "healthy",
        "model_loaded": active_model is not None,
        "pipeline_loaded": loan_pipeline is not None,
        "features_count": len(model_input_features or feature_names or []),
    }


@app.post("/api/predict")
def predict_loan_status(app_data: LoanApplication, db: Session = Depends(database.get_db)):
    active_model = get_active_model()
    if active_model is None:
        raise HTTPException(
            status_code=500,
            detail="AI model artifact not found. Run the notebook export cell to create loan_pipeline.pkl.",
        )

    try:
        if loan_pipeline is not None:
            input_df = build_raw_input(app_data)
        else:
            input_df = build_legacy_scaled_input(app_data)

        prediction = int(active_model.predict(input_df)[0])
        probability = active_model.predict_proba(input_df)[0]
        risk_prob = float(probability[1])
        confidence = float(probability.max())

        result = "No xau" if prediction == 1 else "Tra tot"
        recommendation = "TU CHOI" if prediction == 1 else "PHE DUYET"

        db_record = models.LoanPrediction(
            loan_amnt=app_data.loan_amnt,
            int_rate=app_data.int_rate,
            grade=app_data.grade,
            annual_inc=app_data.annual_inc,
            dti=app_data.dti,
            home_ownership=app_data.home_ownership,
            term_numeric=app_data.term_numeric,
            delinq_2yrs=app_data.delinq_2yrs,
            total_acc=app_data.total_acc,
            prediction=prediction,
            status_label=result,
            confidence=confidence,
            risk_probability=risk_prob,
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        return {
            "status_code": 200,
            "id": db_record.id,
            "prediction": prediction,
            "status_label": result,
            "recommendation": recommendation,
            "risk_probability": round(risk_prob, 4),
            "confidence": round(confidence, 4),
            "input_summary": {
                "loan_amnt": app_data.loan_amnt,
                "grade": app_data.grade,
                "int_rate": app_data.int_rate,
                "annual_inc": app_data.annual_inc,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(exc)}") from exc
