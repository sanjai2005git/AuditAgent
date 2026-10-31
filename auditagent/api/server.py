from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from auditagent.agent.graph import run_agent_query
from auditagent.ml.model_runner import model_runner
from auditagent.audit.logger import audit_logger
from auditagent.audit.replayer import trace_replayer
from auditagent.guardrails.human_approval import human_approval
from auditagent.benchmarks.runner import get_cached_or_run_benchmarks, run_all_benchmarks
from auditagent.data.database import db_manager

app = FastAPI(
    title="AuditAgent API",
    description="Explainable Enterprise Data Agent with AST SQL Guardrails, SHAP Interpretability, Replayable Audit Logging, and Numeric Self-Verification.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language enterprise business question or predictive request")
    session_id: Optional[str] = Field("api_session", description="Session identifier for thread continuity")

class PredictRequest(BaseModel):
    customer_id: Optional[int] = Field(None, description="Customer ID to look up from database")
    profile: Optional[dict[str, Any]] = Field(None, description="Ad-hoc or hypothetical applicant profile features")

class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="'APPROVED' or 'REJECTED'")
    reviewer: str = Field("Risk_Compliance_Officer", description="Name of the administrator/reviewer")

@app.get("/api/health")
def health():
    counts = db_manager.table_row_counts()
    return {
        "status": "healthy",
        "service": "AuditAgent Enterprise Backend",
        "duckdb_connected": True,
        "tables": counts
    }

@app.post("/api/query")
def execute_query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    result = run_agent_query(user_query=req.query, session_id=req.session_id)
    return {
        "trace_id": result.get("trace_id"),
        "session_id": result.get("session_id"),
        "intent": result.get("intent"),
        "tool_called": result.get("tool_called"),
        "generated_sql": result.get("generated_sql"),
        "executed_sql": result.get("executed_sql"),
        "row_count": result.get("row_count"),
        "cost_units": result.get("cost_units"),
        "pii_counts": result.get("pii_counts"),
        "ml_prediction": result.get("ml_prediction"),
        "risk_tier": result.get("risk_tier"),
        "shap_top_features": result.get("shap_top_features"),
        "shap_explanation": result.get("shap_explanation"),
        "verification_status": result.get("verification_result", {}).get("status"),
        "verification_discrepancy": result.get("verification_result", {}).get("discrepancy"),
        "final_response": result.get("final_response"),
        "query_result": result.get("query_result", [])[:50],
        "query_columns": result.get("query_columns", []),
        "latency_ms": round(result.get("execution_latency_ms", 0.0), 2),
        "approval_request_id": result.get("approval_request_id")
    }

@app.post("/api/ml/predict")
def predict_ml(req: PredictRequest):
    if req.customer_id is not None:
        try:
            return model_runner.predict_for_customer(req.customer_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    elif req.profile is not None:
        return model_runner.predict_for_profile(req.profile)
    else:
        raise HTTPException(status_code=400, detail="Must provide either customer_id or profile.")

@app.get("/api/audit")
def list_audit_traces(limit: int = Query(50, ge=1, le=200)):
    traces = audit_logger.get_recent_traces(limit=limit)
    return {"count": len(traces), "traces": traces}

@app.get("/api/audit/{trace_id}")
def get_audit_trace(trace_id: str):
    trace = audit_logger.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found.")
    return trace

@app.post("/api/audit/{trace_id}/replay")
def replay_audit_trace(trace_id: str):
    replay_res = trace_replayer.replay_trace(trace_id)
    if not replay_res["success"]:
        raise HTTPException(status_code=400, detail=replay_res.get("error"))
    return replay_res

@app.get("/api/approvals")
def get_approvals():
    pending = human_approval.get_pending_requests()
    all_reqs = human_approval.get_all_requests()
    return {
        "pending_count": len(pending),
        "pending": pending,
        "all_requests": all_reqs
    }

@app.post("/api/approvals/{request_id}/decide")
def decide_approval(request_id: str, req: ApprovalDecisionRequest):
    try:
        success = human_approval.decide_request(request_id, req.decision, req.reviewer)
        if not success:
            raise HTTPException(status_code=404, detail="Request ID not found.")
        return {"success": True, "request_id": request_id, "decision": req.decision, "reviewer": req.reviewer}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.get("/api/benchmarks")
def get_benchmarks(refresh: bool = False):
    if refresh:
        return run_all_benchmarks()
    return get_cached_or_run_benchmarks()
