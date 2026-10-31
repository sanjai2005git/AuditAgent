import pytest
from auditagent.ml.model_runner import model_runner
from auditagent.ml.explainer import explainer

def test_predict_for_customer():
    res = model_runner.predict_for_customer(1)
    assert "prediction_probability" in res
    assert 0.0 <= res["prediction_probability"] <= 1.0
    assert res["risk_tier"] in ["LOW RISK", "HIGH RISK"]
    assert "explanation_narrative" in res
    assert len(res["contributions"]) > 0
    assert len(res["top_risk_drivers"]) <= 3

def test_predict_for_custom_profile():
    profile = {
        "age": 35,
        "annual_income": 85000,
        "credit_score": 750,
        "debt_to_income": 0.20,
        "open_credit_lines": 5,
        "missed_payments_2yr": 0,
        "loan_amount": 15000,
        "interest_rate": 6.5,
        "employment_years": 8
    }
    res = model_runner.predict_for_profile(profile)
    assert res["prediction_probability"] < 0.40
    assert res["risk_tier"] == "LOW RISK"

def test_global_importance():
    imp = explainer.get_global_importance()
    assert len(imp) == 9
    assert all("feature" in item and "importance" in item for item in imp)
    # Check that it's sorted descending
    scores = [item["importance"] for item in imp]
    assert scores == sorted(scores, reverse=True)
