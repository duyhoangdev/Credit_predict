from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class LoanPrediction(Base):
    __tablename__ = "loan_predictions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Thông tin khoản vay (dạng thô)
    loan_amnt = Column(Float)
    int_rate = Column(Float)
    grade = Column(String(2))
    annual_inc = Column(Float)
    dti = Column(Float)
    home_ownership = Column(String(20))
    term_numeric = Column(Float)
    delinq_2yrs = Column(Float)
    total_acc = Column(Float)
    
    # Kết quả dự đoán
    prediction = Column(Integer)           # 0 = Tốt, 1 = Nợ xấu
    status_label = Column(String(20))      # "Trả tốt" / "Nợ xấu"
    confidence = Column(Float)             # Độ tin cậy cao nhất
    risk_probability = Column(Float)       # Xác suất nợ xấu
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
