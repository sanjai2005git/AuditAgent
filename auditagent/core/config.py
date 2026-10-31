import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "auditagent" / "ml" / "models"
AUDIT_LOG_DIR = BASE_DIR / "audit_logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "enterprise_audit.duckdb")
MODEL_FILE = str(MODELS_DIR / "loan_risk_xgb.json")
BACKGROUND_DATA_FILE = str(MODELS_DIR / "shap_background.parquet")

class Settings(BaseModel):
    # Database
    db_path: str = DB_PATH
    
    # Guardrails
    max_query_cost_units: int = 10000
    max_result_rows: int = 500
    query_timeout_seconds: float = 3.0
    strict_read_only: bool = True
    mask_pii_in_results: bool = True
    mask_pii_in_prompts: bool = True
    
    # HITL Thresholds
    high_impact_row_threshold: int = 250
    high_impact_keywords: list[str] = [
        "override", "delete", "drop", "update", "truncate",
        "alter", "grant", "revoke", "approve_credit_limit_increase",
        "waive_penalty", "export_all_records"
    ]
    
    # Self-Verification
    verification_enabled: bool = True
    numeric_tolerance_pct: float = 0.02  # 2% tolerance
    
    # Model config
    feature_names: list[str] = [
        "age",
        "annual_income",
        "credit_score",
        "debt_to_income",
        "open_credit_lines",
        "missed_payments_2yr",
        "loan_amount",
        "interest_rate",
        "employment_years"
    ]
    risk_threshold: float = 0.50

settings = Settings()
