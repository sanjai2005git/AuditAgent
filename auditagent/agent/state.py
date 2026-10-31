from typing import Any, Optional, TypedDict

class AgentState(TypedDict):
    session_id: str
    trace_id: Optional[str]
    user_query: str
    sanitized_query: str
    pii_counts: dict[str, int]
    intent: str
    guardrail_status: dict[str, Any]
    tool_called: Optional[str]
    tool_args: dict[str, Any]
    generated_sql: Optional[str]
    executed_sql: Optional[str]
    query_result: list[dict[str, Any]]
    query_columns: list[str]
    row_count: int
    cost_units: int
    ml_prediction: Optional[float]
    risk_tier: Optional[str]
    shap_top_features: list[str]
    shap_explanation: dict[str, Any]
    raw_response: str
    verification_result: dict[str, Any]
    final_response: str
    execution_latency_ms: float
    approval_request_id: Optional[str]

