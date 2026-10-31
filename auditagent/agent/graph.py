import uuid
from typing import Any
from langgraph.graph import StateGraph, END
from auditagent.agent.state import AgentState
from auditagent.agent.nodes import (
    input_guardrail_node,
    router_node,
    sql_node,
    ml_node,
    pandas_node,
    hitl_node,
    self_verification_node,
    audit_logger_node
)

def route_intent(state: AgentState) -> str:
    intent = state.get("intent", "TEXT_TO_SQL")
    if intent == "HIGH_IMPACT_APPROVAL":
        return "hitl_agent"
    elif intent == "ML_PREDICT":
        return "ml_agent"
    elif intent == "PANDAS_ANALYSIS":
        return "pandas_agent"
    else:
        return "sql_agent"

def build_agent_graph():
    graph = StateGraph(AgentState)

    # Add processing nodes
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("router", router_node)
    graph.add_node("sql_agent", sql_node)
    graph.add_node("ml_agent", ml_node)
    graph.add_node("pandas_agent", pandas_node)
    graph.add_node("hitl_agent", hitl_node)
    graph.add_node("self_verifier", self_verification_node)
    graph.add_node("audit_logger", audit_logger_node)

    # Entry point
    graph.set_entry_point("input_guardrail")

    # Guardrails -> Intent Routing
    graph.add_edge("input_guardrail", "router")

    # Routing -> Specialized Tool Agents
    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "hitl_agent": "hitl_agent",
            "ml_agent": "ml_agent",
            "pandas_agent": "pandas_agent",
            "sql_agent": "sql_agent"
        }
    )

    # All execution paths converge to Self-Verification
    graph.add_edge("sql_agent", "self_verifier")
    graph.add_edge("ml_agent", "self_verifier")
    graph.add_edge("pandas_agent", "self_verifier")
    graph.add_edge("hitl_agent", "self_verifier")

    # Self-Verification -> Audit Logger -> END
    graph.add_edge("self_verifier", "audit_logger")
    graph.add_edge("audit_logger", END)

    return graph.compile()

audit_agent_app = build_agent_graph()

def run_agent_query(user_query: str, session_id: str = "default_session") -> AgentState:
    """
    Main invocation entrypoint for user queries.
    """
    trace_id = f"TRC-{uuid.uuid4().hex[:12].upper()}"
    initial_state: AgentState = {
        "session_id": session_id,
        "trace_id": trace_id,
        "user_query": user_query,
        "sanitized_query": "",
        "pii_counts": {},
        "intent": "UNKNOWN",
        "guardrail_status": {},
        "tool_called": None,
        "tool_args": {},
        "generated_sql": None,
        "executed_sql": None,
        "query_result": [],
        "query_columns": [],
        "row_count": 0,
        "cost_units": 0,
        "ml_prediction": None,
        "risk_tier": None,
        "shap_top_features": [],
        "shap_explanation": {},
        "raw_response": "",
        "verification_result": {},
        "final_response": "",
        "execution_latency_ms": 0.0,
        "approval_request_id": None
    }

    result = audit_agent_app.invoke(initial_state)
    return result
