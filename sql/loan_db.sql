USE Loan_Approval_DW;
GO

-- 1. Tạo các Schema theo chuẩn
CREATE SCHEMA stg;
GO
CREATE SCHEMA dw;
GO

-- Chuyển bảng vừa import vào schema stg (Giả định bạn đã import data gốc vào dbo.Loan_Raw)
ALTER SCHEMA stg TRANSFER dbo.Loan_Raw;
GO

-- =========================================================
-- 2. TẠO CÁC BẢNG DIMENSION (BẢNG CHIỀU)
-- =========================================================

-- Bảng Chiều Đặc điểm Khách hàng
CREATE TABLE dw.Dim_Borrower (
    Borrower_ID INT IDENTITY(1,1) PRIMARY KEY,
    emp_length NVARCHAR(50),      -- Chuyển sang NVARCHAR để có thể điền chữ 'Unknown'
    home_ownership NVARCHAR(50),
    annual_inc FLOAT,
    income_bin NVARCHAR(50),      -- CỘT MỚI: Dùng cho Data Binning (vẽ Histogram PowerBI)
    dti FLOAT,
    delinq_2yrs FLOAT,
    total_acc FLOAT
);
GO

-- Bảng Chiều Thông tin khoản vay
CREATE TABLE dw.Dim_Loan_Info (
    Loan_Info_ID INT IDENTITY(1,1) PRIMARY KEY,
    term NVARCHAR(50),
    grade NVARCHAR(50),
    verification_status NVARCHAR(50)
);
GO

-- =========================================================
-- 3. TẠO BẢNG FACT (BẢNG SỰ KIỆN) TRUNG TÂM
-- =========================================================
CREATE TABLE dw.Fact_Loan (
    Fact_ID INT IDENTITY(1,1) PRIMARY KEY,
    Borrower_ID INT NOT NULL,
    Loan_Info_ID INT NOT NULL,
    loan_amnt FLOAT,
    int_rate FLOAT,
    installment FLOAT,
    loan_status_raw NVARCHAR(50), -- Trạng thái gốc (vd: Fully Paid, Charged Off) để PowerBI dễ đọc
    loan_status_bin INT,          -- Trạng thái ML: 1 (Nợ xấu), 0 (Trả tốt)
    CONSTRAINT FK_Fact_Borrower FOREIGN KEY (Borrower_ID) REFERENCES dw.Dim_Borrower(Borrower_ID),
    CONSTRAINT FK_Fact_LoanInfo FOREIGN KEY (Loan_Info_ID) REFERENCES dw.Dim_Loan_Info(Loan_Info_ID)
);
GO

-- =========================================================
-- 4. QUÁ TRÌNH ETL: ÁP DỤNG BUSINESS LOGIC & NẠP DỮ LIỆU
-- =========================================================

-- 4.1. Nạp dữ liệu vào Dim_Borrower (Điền khuyết & Phân thùng Data Binning)
INSERT INTO dw.Dim_Borrower (emp_length, home_ownership, annual_inc, income_bin, dti, delinq_2yrs, total_acc)
SELECT DISTINCT 
    ISNULL(CAST(emp_length AS NVARCHAR(50)), 'Unknown') AS emp_length, -- Điền khuyết Unknown
    CAST(home_ownership AS NVARCHAR(50)),
    annual_inc,
    -- LOGIC DATA BINNING (Phân thùng thu nhập)
    CASE 
        WHEN annual_inc < 50000 THEN 'Low Income (<50k)'
        WHEN annual_inc >= 50000 AND annual_inc <= 100000 THEN 'Medium Income (50k-100k)'
        WHEN annual_inc > 100000 THEN 'High Income (>100k)'
        ELSE 'Unknown'
    END AS income_bin,
    dti, 
    delinq_2yrs, 
    total_acc
FROM stg.Loan_Raw
WHERE loan_status != 'Current'  -- Loại bỏ nhiễu 'Current' ngay từ đầu
  AND annual_inc > 0;           -- Loại bỏ lỗi logic (thu nhập âm hoặc bằng 0)

-- 4.2. Nạp dữ liệu vào Dim_Loan_Info
INSERT INTO dw.Dim_Loan_Info (term, grade, verification_status)
SELECT DISTINCT 
    CAST(term AS NVARCHAR(50)), 
    CAST(grade AS NVARCHAR(50)), 
    CAST(verification_status AS NVARCHAR(50))
FROM stg.Loan_Raw
WHERE loan_status != 'Current'
  AND annual_inc > 0;

-- 4.3. Nạp dữ liệu vào Fact_Loan (Áp dụng Transformation chuyển nhãn 0/1)
INSERT INTO dw.Fact_Loan (Borrower_ID, Loan_Info_ID, loan_amnt, int_rate, installment, loan_status_raw, loan_status_bin)
SELECT 
    b.Borrower_ID,
    l.Loan_Info_ID,
    r.loan_amnt,
    r.int_rate,
    r.installment,
    r.loan_status AS loan_status_raw,
    -- LOGIC CHUYỂN ĐỔI BIẾN MỤC TIÊU (0: Tốt, 1: Xấu)
    CASE 
        WHEN r.loan_status = 'Fully Paid' THEN 0
        WHEN r.loan_status IN ('Charged Off', 'Default') OR r.loan_status LIKE '%Late%' THEN 1
        ELSE NULL
    END AS loan_status_bin
FROM stg.Loan_Raw r
JOIN dw.Dim_Borrower b 
    ON ISNULL(CAST(r.emp_length AS NVARCHAR(50)), 'Unknown') = b.emp_length 
    AND CAST(r.home_ownership AS NVARCHAR(50)) = b.home_ownership 
    AND r.annual_inc = b.annual_inc
JOIN dw.Dim_Loan_Info l 
    ON CAST(r.term AS NVARCHAR(50)) = l.term 
    AND CAST(r.grade AS NVARCHAR(50)) = l.grade 
    AND CAST(r.verification_status AS NVARCHAR(50)) = l.verification_status
WHERE r.loan_status != 'Current'
  AND r.annual_inc > 0;
GO

PRINT N'✅ Đã xây dựng xong Data Warehouse + Tích hợp thành công Data Binning & Target Transformation!';