"""
Script xuất mô hình AI + Pipeline tiền xử lý cho Web App.
Chạy script này SAU KHI đã chạy toàn bộ notebook 02_ETL_and_Model_Traing.ipynb
(tức là các biến lr_model, scaler_lr, ordinal_encoder đã tồn tại trong memory).

Cách dùng: Chạy script này như một cell cuối cùng trong notebook.
"""
import joblib
from pathlib import Path
import json

# Xác định thư mục lưu
base_dir = Path.cwd().parents[0] if Path.cwd().name == 'notebooks' else Path.cwd()
export_dir = base_dir / 'app' / 'models'
export_dir.mkdir(parents=True, exist_ok=True)

print("⏳ Đang xuất mô hình và pipeline tiền xử lý...")

# 1. Lưu mô hình Logistic Regression (mô hình chính)
joblib.dump(lr_model, export_dir / 'lr_model.pkl')
print(f"   ✅ Đã lưu Logistic Regression → {export_dir / 'lr_model.pkl'}")

# 2. Lưu Scaler (đã fit trên tập Train)
joblib.dump(scaler_lr, export_dir / 'scaler_lr.pkl')
print(f"   ✅ Đã lưu StandardScaler → {export_dir / 'scaler_lr.pkl'}")

# 3. Lưu danh sách cột (feature names) sau encoding
feature_names = list(X_train.columns)
with open(export_dir / 'feature_names.json', 'w') as f:
    json.dump(feature_names, f, indent=2)
print(f"   ✅ Đã lưu Feature Names ({len(feature_names)} features) → {export_dir / 'feature_names.json'}")

# 4. Lưu Ordinal Encoder
joblib.dump(ordinal_encoder, export_dir / 'ordinal_encoder.pkl')
print(f"   ✅ Đã lưu Ordinal Encoder → {export_dir / 'ordinal_encoder.pkl'}")

# 5. Lưu thông số clipping
clip_params = {
    'INC_P99': float(INC_P99) if 'INC_P99' in dir() else 250000.0,
    'DTI_P99': float(DTI_P99) if 'DTI_P99' in dir() else 39.99
}
with open(export_dir / 'clip_params.json', 'w') as f:
    json.dump(clip_params, f, indent=2)
print(f"   ✅ Đã lưu Clip Params → {export_dir / 'clip_params.json'}")

print("\n" + "=" * 60)
print("🎉 HOÀN TẤT! Tất cả file đã sẵn sàng tại:", export_dir)
print("Danh sách file:")
for f in sorted(export_dir.glob('*')):
    print(f"   📄 {f.name} ({f.stat().st_size:,} bytes)")
