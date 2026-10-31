import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
import xgboost as xgb
from auditagent.core.config import settings, MODELS_DIR, MODEL_FILE, BACKGROUND_DATA_FILE
from auditagent.data.database import db_manager

def train_and_save_model():
    print("Fetching training data from DuckDB...")
    query = """
    SELECT 
        c.age,
        c.annual_income,
        c.credit_score,
        l.debt_to_income,
        l.open_credit_lines,
        l.missed_payments_2yr,
        l.loan_amount,
        l.interest_rate,
        c.employment_years,
        l.is_default
    FROM loans l
    JOIN customers c ON l.customer_id = c.customer_id
    """
    conn = db_manager.get_connection(read_only=True)
    try:
        df = conn.execute(query).fetch_df()
    finally:
        conn.close()

    features = settings.feature_names
    X = df[features]
    y = df["is_default"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training XGBoost classifier on {len(X_train)} samples, testing on {len(X_test)} samples...")
    
    scale_pos = (len(y_train) - sum(y_train)) / max(1, sum(y_train))
    
    model = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        random_state=42
    )
    
    model.fit(X_train, y_train)

    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= settings.risk_threshold).astype(int)
    
    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Training Results -> ROC-AUC: {auc:.4f}, Accuracy: {acc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(MODEL_FILE)
    print(f"Model successfully saved to: {MODEL_FILE}")

    # Save SHAP background data (100 k-means or random samples)
    background_sample = X_train.sample(n=min(100, len(X_train)), random_state=42)
    background_sample.to_parquet(BACKGROUND_DATA_FILE, index=False)
    print(f"SHAP background dataset saved to: {BACKGROUND_DATA_FILE}")

    # Save metadata
    meta = {
        "features": features,
        "auc": float(auc),
        "accuracy": float(acc),
        "risk_threshold": settings.risk_threshold,
        "samples_trained": len(X_train),
        "default_rate": float(y.mean())
    }
    with open(MODELS_DIR / "model_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return model

if __name__ == "__main__":
    train_and_save_model()
