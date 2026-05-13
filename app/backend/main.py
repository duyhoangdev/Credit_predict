from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import numpy as np
import json
import os
from typing import Optional
from sqlalchemy.orm import Session
from . import models, database

# Khởi tạo database tables
models.Base.metadata.create_all(bind=database.engine)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Loan Approval DSS API",
    description="Hệ thống Backend API cho Hệ Hỗ trợ Ra Quyết định Tín dụng (DSS)",
    version="2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# LOAD MÔ HÌNH VÀ PIPELINE
# =============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "../models")

def load_artifact(filename, loader="joblib"):
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        return None
    if loader == "joblib":
        return joblib.load(path)
    elif loader == "json":
        with open(path, 'r') as f:
            return json.load(f)
    return None

# Load tất cả artifacts
lr_model = load_artifact("lr_model.pkl")
scaler = load_artifact("scaler_lr.pkl")
# Bỏ qua ordinal_encoder vì bị lỗi StringDtype, dùng logic mapping thủ công bên dưới
ordinal_encoder = None # load_artifact("ordinal_encoder.pkl")
feature_names = load_artifact("feature_names.json", "json")
clip_params = load_artifact("clip_params.json", "json")

# Fallback: thử load model cũ nếu model mới chưa có
if lr_model is None:
    lr_model = load_artifact("loan_model.pkl")
    print("⚠️  Đang dùng model cũ (loan_model.pkl). Hãy chạy export_model.py từ notebook!")

# =============================================
# SCHEMA DỮ LIỆU ĐẦU VÀO (DẠNG THÔ - NGƯỜI DÙNG NHẬP)
# =============================================
class LoanApplication(BaseModel):
    loan_amnt: float = Field(..., gt=0, description="Số tiền vay ($)")
    int_rate: float = Field(..., gt=0, le=30, description="Lãi suất (%)")
    grade: str = Field(..., pattern="^[A-G]$", description="Hạng tín dụng (A-G)")
    annual_inc: float = Field(..., gt=0, description="Thu nhập hàng năm ($)")
    dti: float = Field(..., ge=0, description="Tỷ lệ nợ trên thu nhập")
    home_ownership: str = Field(..., description="Tình trạng nhà ở")
    verification_status: str = Field(..., description="Trạng thái xác minh thu nhập")
    emp_length: str = Field(default="Unknown", description="Thâm niên công tác")
    term_numeric: float = Field(default=36.0, description="Kỳ hạn vay (tháng)")
    delinq_2yrs: float = Field(default=0.0, ge=0, description="Số lần trễ hạn 2 năm gần đây")
    total_acc: float = Field(default=10.0, ge=0, description="Tổng số tài khoản tín dụng")

# =============================================
# PIPELINE TIỀN XỬ LÝ
# =============================================
def preprocess_input(data: LoanApplication) -> pd.DataFrame:
    """Chuyển đổi dữ liệu thô từ người dùng sang format mà model yêu cầu."""
    
    # Tạo DataFrame ban đầu
    raw = {
        'loan_amnt': data.loan_amnt,
        'int_rate': data.int_rate,
        'grade': data.grade,
        'delinq_2yrs': data.delinq_2yrs,
        'total_acc': data.total_acc,
        'term_numeric': data.term_numeric,
        'home_ownership': data.home_ownership,
        'verification_status': data.verification_status,
        'emp_length': data.emp_length,
    }
    
    # Feature Engineering: clip annual_inc và dti
    inc_clip = clip_params.get('INC_P99', 250000.0) if clip_params else 250000.0
    dti_clip = clip_params.get('DTI_P99', 39.99) if clip_params else 39.99
    raw['annual_inc_clipped'] = min(data.annual_inc, inc_clip)
    raw['dti_clipped'] = min(data.dti, dti_clip)
    
    df = pd.DataFrame([raw])
    
    # Ordinal Encoding cho grade
    if ordinal_encoder is not None:
        df = ordinal_encoder.transform(df)
    else:
        grade_map = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7}
        df['grade'] = df['grade'].map(grade_map).fillna(3)
    
    # One-Hot Encoding cho categorical
    ohe_cols = ['home_ownership', 'verification_status', 'emp_length']
    existing_ohe = [c for c in ohe_cols if c in df.columns]
    df = pd.get_dummies(df, columns=existing_ohe, drop_first=True, dtype=int)
    
    # Đảm bảo đủ cột giống lúc train
    if feature_names:
        for col in feature_names:
            if col not in df.columns:
                df[col] = 0
        df = df[feature_names]
    
    # Scale
    if scaler is not None:
        df_values = scaler.transform(df.values)
        df = pd.DataFrame(df_values, columns=df.columns)
    
    return df


# =============================================
# API ENDPOINTS
# =============================================
@app.get("/")
def read_root():
    model_status = "✅ Loaded" if lr_model is not None else "❌ Not found"
    scaler_status = "✅ Loaded" if scaler is not None else "⚠️ Not found"
    return {
        "service": "Loan Approval DSS API v2.0",
        "model_status": model_status,
        "scaler_status": scaler_status,
        "endpoints": ["/api/predict", "/api/health"]
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": lr_model is not None,
        "scaler_loaded": scaler is not None,
        "features_count": len(feature_names) if feature_names else 0
    }

@app.post("/api/predict")
def predict_loan_status(app_data: LoanApplication, db: Session = Depends(database.get_db)):
    if lr_model is None:
        raise HTTPException(status_code=500, detail="Chưa tìm thấy file mô hình AI! Hãy chạy export_model.py từ notebook.")
    
    try:
        # Tiền xử lý dữ liệu
        input_df = preprocess_input(app_data)
        
        # AI dự đoán
        prediction = int(lr_model.predict(input_df)[0])
        probability = lr_model.predict_proba(input_df)[0]
        risk_prob = float(probability[1])  # Xác suất nợ xấu
        confidence = float(probability.max())
        
        result = "Nợ xấu" if prediction == 1 else "Trả tốt"
        recommendation = "TỪ CHỐI" if prediction == 1 else "PHÊ DUYỆT"
        
        # Lưu vào Database
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
            risk_probability=risk_prob
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
                "annual_inc": app_data.annual_inc
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")
