from pathlib import Path
from typing import Any, Optional
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from auditagent.core.config import settings, MODEL_FILE, BACKGROUND_DATA_FILE

class ModelExplainer:
    def __init__(self):
        self.model = None
        self.background_data = None
        self.explainer = None
        self._load()

    def _load(self):
        if not Path(MODEL_FILE).exists() or not Path(BACKGROUND_DATA_FILE).exists():
            return
        self.model = xgb.XGBClassifier()
        self.model.load_model(MODEL_FILE)
        self.background_data = pd.read_parquet(BACKGROUND_DATA_FILE)
        
        # TreeExplainer is exact and fast for tree models
        self.explainer = shap.TreeExplainer(self.model, data=self.background_data)

    def explain_instance(self, features_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Computes exact local SHAP values and translates them into auditable explanations.
        """
        if self.explainer is None:
            self._load()
            if self.explainer is None:
                raise RuntimeError("Explainer model or background data not found.")

        feature_order = settings.feature_names
        row_values = [float(features_dict.get(f, 0.0)) for f in feature_order]
        df_row = pd.DataFrame([row_values], columns=feature_order)

        # Predict probability
        pred_proba = float(self.model.predict_proba(df_row)[0, 1])
        risk_tier = "HIGH RISK" if pred_proba >= settings.risk_threshold else "LOW RISK"

        # Calculate SHAP values
        # For XGBClassifier, shap_values can be 1D or 2D
        shap_res = self.explainer(df_row)
        shap_vals = shap_res.values[0]
        base_val = float(shap_res.base_values[0]) if hasattr(shap_res.base_values, "__len__") else float(shap_res.base_values)
        
        # If output was in log-odds margin space, compute sigmoid approximation or direct probability attribution
        # Logistic sigmoid
        def sigmoid(x):
            return 1.0 / (1.0 + np.exp(-x))

        # Base probability vs predicted probability
        base_prob = sigmoid(base_val) if abs(base_val) > 1.0 else max(0.01, min(0.99, base_val))
        
        contributions = []
        for feat, val, s_val in zip(feature_order, row_values, shap_vals):
            contributions.append({
                "feature": feat,
                "feature_value": val,
                "shap_value": float(s_val),
                "abs_shap": abs(float(s_val)),
                "impact": "INCREASES_RISK" if s_val > 0 else "REDUCES_RISK"
            })

        # Sort by absolute attribution
        contributions.sort(key=lambda x: x["abs_shap"], reverse=True)
        
        # Separate positive (risk increasing) and negative (protective)
        risk_drivers = [c for c in contributions if c["shap_value"] > 0]
        protective_factors = [c for c in contributions if c["shap_value"] < 0]

        # Natural language summary
        driver_phrases = []
        for c in risk_drivers[:3]:
            feat = c["feature"].replace("_", " ").title()
            val = c["feature_value"]
            if "income" in c["feature"] or "amount" in c["feature"]:
                val_str = f"${val:,.0f}"
            elif "rate" in c["feature"] or "dti" in c["feature"] or "income" in c["feature"]:
                val_str = f"{val:.1f}%" if "rate" in c["feature"] else f"{val:.2f}"
            else:
                val_str = f"{val}"
            driver_phrases.append(f"{feat} ({val_str}, attribution: +{c['shap_value']:.3f})")

        protective_phrases = []
        for c in protective_factors[:2]:
            feat = c["feature"].replace("_", " ").title()
            val = c["feature_value"]
            if "income" in c["feature"] or "amount" in c["feature"]:
                val_str = f"${val:,.0f}"
            else:
                val_str = f"{val}"
            protective_phrases.append(f"{feat} ({val_str}, attribution: {c['shap_value']:.3f})")

        drivers_text = ", ".join(driver_phrases) if driver_phrases else "None significant"
        protective_text = ", ".join(protective_phrases) if protective_phrases else "None significant"

        explanation_narrative = (
            f"Loan default prediction is {pred_proba * 100:.1f}% ({risk_tier}). "
            f"Baseline portfolio expectation is {base_prob * 100:.1f}%. "
            f"Primary factors elevating risk: [{drivers_text}]. "
            f"Compensating protective factors: [{protective_text}]."
        )

        return {
            "prediction_probability": pred_proba,
            "risk_tier": risk_tier,
            "base_value": base_val,
            "base_probability": base_prob,
            "contributions": contributions,
            "top_risk_drivers": risk_drivers[:3],
            "top_protective_factors": protective_factors[:2],
            "explanation_narrative": explanation_narrative,
            "feature_names": feature_order,
            "feature_values": row_values,
            "shap_values": [float(s) for s in shap_vals]
        }

    def get_global_importance(self) -> list[dict[str, Any]]:
        """
        Computes global mean absolute SHAP value for all features across background dataset.
        """
        if self.explainer is None:
            self._load()
        shap_vals = self.explainer(self.background_data).values
        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        
        res = []
        for feat, imp in zip(settings.feature_names, mean_abs):
            res.append({"feature": feat, "importance": float(imp)})
        res.sort(key=lambda x: x["importance"], reverse=True)
        return res

explainer = ModelExplainer()

