import numpy as np
import pandas as pd
from typing import Any
from auditagent.ml.model_runner import model_runner
from auditagent.ml.explainer import explainer
from auditagent.data.database import db_manager

class FaithfulnessEvaluator:
    def evaluate_faithfulness(self, sample_size: int = 50) -> dict[str, Any]:
        """
        Evaluates SHAP explanation faithfulness via monotonicity checks and perturbation sensitivity.
        """
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute(f"SELECT customer_id FROM customers LIMIT {sample_size}").fetch_df()
            cust_ids = df["customer_id"].tolist()
        finally:
            conn.close()

        monotonic_passes = 0
        perturbation_passes = 0
        tested_count = 0
        evaluations = []

        for cid in cust_ids:
            try:
                base_exp = model_runner.predict_for_customer(cid)
            except Exception:
                continue

            tested_count += 1
            feat_dict = {f: float(v) for f, v in zip(base_exp["feature_names"], base_exp["feature_values"])}
            base_proba = base_exp["prediction_probability"]
            contributions = base_exp["contributions"]

            # 1. Monotonicity check on top risk driver
            top_driver = base_exp["top_risk_drivers"][0] if base_exp["top_risk_drivers"] else None
            mono_pass = True
            
            if top_driver:
                feat_name = top_driver["feature"]
                orig_val = feat_dict[feat_name]
                # Perturb upward by 15%
                perturbed_dict = feat_dict.copy()
                perturbed_dict[feat_name] = orig_val * 1.15 if orig_val != 0 else 1.0
                
                new_res = model_runner.predict_for_profile(perturbed_dict)
                new_proba = new_res["prediction_probability"]
                
                # Should either increase or stay equal
                if new_proba >= base_proba - 0.005:
                    mono_pass = True
                    monotonic_passes += 1
                else:
                    mono_pass = False

            # 2. Perturbation check: compare top-1 feature vs bottom-1 feature ablation
            top_feat = contributions[0]["feature"]
            bottom_feat = contributions[-1]["feature"]

            # Ablate top feature (reduce to median baseline)
            dict_ablate_top = feat_dict.copy()
            dict_ablate_top[top_feat] = 0.0
            p_ablate_top = model_runner.predict_for_profile(dict_ablate_top)["prediction_probability"]
            delta_top = abs(p_ablate_top - base_proba)

            # Ablate bottom feature
            dict_ablate_bottom = feat_dict.copy()
            dict_ablate_bottom[bottom_feat] = 0.0
            p_ablate_bottom = model_runner.predict_for_profile(dict_ablate_bottom)["prediction_probability"]
            delta_bottom = abs(p_ablate_bottom - base_proba)

            # Faithfulness condition: ablating high-SHAP feature creates larger impact than low-SHAP feature
            pert_pass = delta_top >= delta_bottom
            if pert_pass:
                perturbation_passes += 1

            evaluations.append({
                "customer_id": cid,
                "base_risk": round(base_proba, 4),
                "top_driver": top_driver["feature"] if top_driver else None,
                "top_driver_shap": round(top_driver["shap_value"], 4) if top_driver else 0.0,
                "monotonicity_passed": mono_pass,
                "delta_top_ablation": round(delta_top, 4),
                "delta_bottom_ablation": round(delta_bottom, 4),
                "sensitivity_passed": pert_pass
            })

        mono_rate = round((monotonic_passes / max(1, tested_count)) * 100, 2)
        pert_rate = round((perturbation_passes / max(1, tested_count)) * 100, 2)
        faithfulness_score = round((mono_rate + pert_rate) / 2.0, 2)

        return {
            "samples_evaluated": tested_count,
            "monotonicity_rate_pct": mono_rate,
            "sensitivity_rate_pct": pert_rate,
            "faithfulness_score_pct": faithfulness_score,
            "evaluations": evaluations[:15]
        }

faithfulness_evaluator = FaithfulnessEvaluator()

if __name__ == "__main__":
    res = faithfulness_evaluator.evaluate_faithfulness(sample_size=30)
    print(f"Evaluated Samples: {res['samples_evaluated']}")
    print(f"Monotonicity Rate: {res['monotonicity_rate_pct']}%")
    print(f"Perturbation Sensitivity Rate: {res['sensitivity_rate_pct']}%")
    print(f"Overall Faithfulness Score: {res['faithfulness_score_pct']}%")
