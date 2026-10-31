from typing import Any, Optional
from auditagent.ml.model_runner import model_runner
from auditagent.ml.explainer import explainer

class MLTool:
    def predict_risk(
        self,
        customer_id: Optional[int] = None,
        profile: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Executes XGBoost loan default prediction and generates local SHAP attributions.
        """
        if customer_id is not None:
            result = model_runner.predict_for_customer(int(customer_id))
        elif profile is not None:
            result = model_runner.predict_for_profile(profile)
        else:
            # Default sample customer 1
            result = model_runner.predict_for_customer(1)

        return result

    def get_feature_governance(self) -> list[dict[str, Any]]:
        """
        Returns global SHAP importance for model auditability.
        """
        return explainer.get_global_importance()

ml_tool = MLTool()
