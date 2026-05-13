import pandas as pd
from pathlib import Path
import sys

# Đảm bảo output hỗ trợ UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Đường dẫn chính xác tới file loan.csv
raw_file = Path(r"f:\dw\Loan_Approval_DSS_Project\data\raw\loan.csv")

if not raw_file.exists():
    print(f"Error: Could not find file at {raw_file}")
else:
    print("Scanning 2.2 million rows... (please wait)")

    try:
        # Sử dụng low_memory=False để tránh cảnh báo dtype
        status_counts = pd.read_csv(raw_file, usecols=['loan_status'], low_memory=False)['loan_status'].value_counts()

        print("\n=== FULL DATASET LOAN STATUS COUNTS ===")
        print(status_counts)

        # Tính thêm tỷ lệ phần trăm cho trực quan
        print("\n=== PERCENTAGE (%) ===")
        print((status_counts / status_counts.sum() * 100).round(2))
    except Exception as e:
        print(f"Error reading file: {e}")
