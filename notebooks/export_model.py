"""
Export the trained AI model and preprocessing pipeline for the web app.

Run this script as the final notebook cell after lr_model has been trained.
lr_model is expected to be a sklearn Pipeline:
preprocessor -> LogisticRegression.
"""
import json
from pathlib import Path

import joblib


base_dir = Path.cwd().parents[0] if Path.cwd().name == "notebooks" else Path.cwd()
export_dir = base_dir / "app" / "models"
export_dir.mkdir(parents=True, exist_ok=True)

print("Exporting model and preprocessing pipeline...")

loan_pipeline = lr_model
joblib.dump(loan_pipeline, export_dir / "loan_pipeline.pkl")
print(f"   Saved Logistic Regression pipeline -> {export_dir / 'loan_pipeline.pkl'}")

# Keep separate artifacts for report/backward compatibility.
joblib.dump(lr_model.named_steps["model"], export_dir / "lr_model.pkl")
joblib.dump(lr_model.named_steps["preprocessor"], export_dir / "preprocessor_lr.pkl")
print(f"   Saved classifier and preprocessor separately -> {export_dir}")

if "rf_best" in globals():
    joblib.dump(rf_best, export_dir / "rf_tuned_pipeline.pkl")
    print(f"   Saved tuned Random Forest pipeline -> {export_dir / 'rf_tuned_pipeline.pkl'}")

feature_names = list(lr_model.named_steps["preprocessor"].get_feature_names_out())
with open(export_dir / "feature_names.json", "w", encoding="utf-8") as f:
    json.dump(feature_names, f, indent=2, ensure_ascii=False)
print(f"   Saved transformed feature names ({len(feature_names)} features)")

with open(export_dir / "model_input_features.json", "w", encoding="utf-8") as f:
    json.dump(model_input_features, f, indent=2, ensure_ascii=False)
print(f"   Saved raw input feature names ({len(model_input_features)} features)")

clip_params = {
    "INC_P99": float(INC_P99) if "INC_P99" in globals() else 250000.0,
    "DTI_P99": float(DTI_P99) if "DTI_P99" in globals() else 39.99,
}
with open(export_dir / "clip_params.json", "w", encoding="utf-8") as f:
    json.dump(clip_params, f, indent=2, ensure_ascii=False)
print(f"   Saved clip params -> {export_dir / 'clip_params.json'}")

print("\n" + "=" * 60)
print("Done. Files are ready at:", export_dir)
for artifact in sorted(export_dir.glob("*")):
    print(f"   {artifact.name} ({artifact.stat().st_size:,} bytes)")
