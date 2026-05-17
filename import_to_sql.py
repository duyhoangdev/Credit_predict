import pandas as pd
from sqlalchemy import create_engine
import urllib
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

base_dir = Path(__file__).resolve().parent
preferred_file = base_dir / 'data' / 'processed' / 'living_sample_100k.csv'
fallback_file = base_dir / 'data' / 'raw' / 'loan_dw.csv'
input_file = preferred_file if preferred_file.exists() else fallback_file

print(f"1. Đang đọc dữ liệu DWH từ file {input_file.relative_to(base_dir)}...")
# Ưu tiên dùng output ETL cho DWH/Power BI; fallback sang loan_dw.csv nếu chưa chạy notebook.
df = pd.read_csv(input_file, low_memory=False)

print(f"   -> Đã đọc xong {len(df):,} dòng dữ liệu!")

print("2. Đang kết nối và bơm dữ liệu vào SQL Server...")
# ====================================================
# ĐIỀN TÊN SERVER CỦA BẠN VÀO ĐÂY (Tên lúc bạn đăng nhập SSMS)
# ====================================================
ten_server = 'localhost' 
# Nếu bị lỗi kết nối, hãy đổi thành: ten_server = r'localhost\SQLEXPRESS' hoặc tên máy của bạn

# Tạo chuỗi kết nối an toàn với pyodbc
params = urllib.parse.quote_plus(
    f"Driver={{ODBC Driver 17 for SQL Server}};"
    f"Server={ten_server};"
    f"Database=Loan_Approval_DW;"
    f"Trusted_Connection=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

try:
    # Đẩy thẳng vào bảng Loan_Raw (nếu có rồi thì ghi đè)
    df.to_sql('Loan_Raw', con=engine, schema='dbo', if_exists='replace', index=False)
    print("✅ THÀNH CÔNG! Toàn bộ dữ liệu đã được đẩy thẳng vào bảng dbo.Loan_Raw trong SQL Server!")
    print("👉 Bây giờ bạn có thể mở SSMS, chạy file loan_db.sql để nó tự động chia Data Warehouse nhé!")
except Exception as e:
    print("❌ LỖI KẾT NỐI:", str(e))
    print("Mẹo: Hãy kiểm tra lại biến 'ten_server' trong code xem đã đúng tên Server trong SSMS chưa.")
