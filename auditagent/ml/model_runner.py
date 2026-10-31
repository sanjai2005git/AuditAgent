from typing import Any, Optional
import pandas as pd
from auditagent.core.config import settings
from auditagent.data.database import db_manager
from auditagent.ml.explainer import explainer

class ModelRunner:
    def predict_for_customer(self, customer_id: int) -> dict[str, Any]:
        """
        Fetches borrower profile and active loan from DuckDB, runs XGBoost model,
        and computes SHAP local explanations.
        """
        conn = db_manager.get_connection(read_only=True)
        try:
            query = f"""
            SELECT 
                c.customer_id,
                c.full_name,
                c.age,
                c.annual_income,
                c.credit_score,
                c.employment_years,
                COALESCE(l.debt_to_income, 0.30) as debt_to_income,
                COALESCE(l.open_credit_lines, 5) as open_credit_lines,
                COALESCE(l.missed_payments_2yr, 0) as missed_payments_2yr,
                COALESCE(l.loan_amount, 25000) as loan_amount,
                COALESCE(l.interest_rate, 8.5) as interest_rate
            FROM customers c
            LEFT JOIN loans l ON c.customer_id = l.customer_id
            WHERE c.customer_id = {int(customer_id)}
            LIMIT 1
            """
            df = conn.execute(query).fetch_df()
            if df.empty:
                raise ValueError(f"Customer ID {customer_id} not found in database.")
            
            row = df.iloc[0].to_dict()
            features = {f: float(row[f]) for f in settings.feature_names}
            
            explanation = explainer.explain_instance(features)
            explanation["customer_id"] = customer_id
            explanation["full_name"] = row.get("full_name", "")
            return explanation
        finally:
            conn.close()

    def predict_for_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """
        Runs prediction and SHAP explanation for an ad-hoc or simulated borrower profile.
        """
        features = {}
        for f in settings.feature_names:
            if f not in profile:
                # Default fallback values
                defaults = {
                    "age": 40.0,
                    "annual_income": 65000.0,
                    "credit_score": 680.0,
                    "debt_to_income": 0.32,
                    "open_credit_lines": 6.0,
                    "missed_payments_2yr": 0.0,
                    "loan_amount": 20000.0,
                    "interest_rate": 8.0,
                    "employment_years": 8.0
                }
                features[f] = defaults.get(f, 0.0)
            else:
                features[f] = float(profile[f])
                
        explanation = explainer.explain_instance(features)
        return explanation

model_runner = ModelRunner()
