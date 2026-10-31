import pytest
from fastapi.testclient import TestClient
from auditagent.api.server import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["tables"]["customers"] >= 1000

def test_api_query_sql():
    res = client.post("/api/query", json={"query": "What is the total number of customers?"})
    assert res.status_code == 200
    data = res.json()
    assert "trace_id" in data
    assert data["intent"] == "TEXT_TO_SQL"
    assert "final_response" in data

def test_api_query_ml():
    res = client.post("/api/query", json={"query": "Predict credit risk for customer #5"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "ML_PREDICT"
    assert "shap_top_features" in data
    assert data["risk_tier"] in ["LOW RISK", "HIGH RISK"]

def test_api_query_guardrail_block():
    res = client.post("/api/query", json={"query": "DROP TABLE loans"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "HIGH_IMPACT_APPROVAL"
    assert data["approval_request_id"] is not None

def test_api_predict():
    res = client.post("/api/ml/predict", json={"customer_id": 10})
    assert res.status_code == 200
    data = res.json()
    assert "prediction_probability" in data
    assert "contributions" in data

def test_api_audit_and_replay():
    # Fetch recent traces
    res = client.get("/api/audit?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    tid = data["traces"][0]["trace_id"]

    # Replay trace
    rep_res = client.post(f"/api/audit/{tid}/replay")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["success"] is True

def test_api_benchmarks():
    res = client.get("/api/benchmarks")
    assert res.status_code == 200
    data = res.json()
    assert "headline_metrics" in data
    assert "sql_gold_questions_evaluated" in data["headline_metrics"]

