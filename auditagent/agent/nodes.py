import re
import time
from typing import Any
import pandas as pd
from auditagent.agent.state import AgentState
from auditagent.guardrails.pii_masker import pii_masker
from auditagent.guardrails.human_approval import human_approval
from auditagent.tools.sql_tool import sql_tool
from auditagent.tools.pandas_tool import pandas_tool
from auditagent.tools.ml_tool import ml_tool
from auditagent.verification.self_verifier import self_verifier
from auditagent.audit.logger import audit_logger

def input_guardrail_node(state: AgentState) -> dict[str, Any]:
    start_time = time.perf_counter()
    user_q = state.get("user_query", "")

    # 1. PII Masking on input
    sanitized, pii_counts = pii_masker.mask_text(user_q)

    # 2. Check for mutation / write / high impact
    eval_res = human_approval.evaluate_action(
        action_type="USER_PROMPT_INSPECTION",
        details=user_q
    )

    guardrail_status = {
        "pii_masked": sum(pii_counts.values()) > 0,
        "pii_details": pii_counts,
        "requires_hitl_approval": eval_res["requires_approval"],
        "hitl_reasons": eval_res["reasons"]
    }

    return {
        "sanitized_query": sanitized,
        "pii_counts": pii_counts,
        "guardrail_status": guardrail_status,
        "execution_latency_ms": (time.perf_counter() - start_time) * 1000
    }

def router_node(state: AgentState) -> dict[str, Any]:
    guardrail_status = state.get("guardrail_status", {})
    if guardrail_status.get("requires_hitl_approval"):
        return {"intent": "HIGH_IMPACT_APPROVAL"}

    q = state.get("sanitized_query", "").lower()

    # Explicit ML predictive keywords
    predict_keywords = [
        "predict", "prediction", "forecast", "what is the default probability",
        "calculate risk for customer", "score customer", "credit risk assessment",
        "churn risk for", "will customer default"
    ]
    if any(k in q for k in predict_keywords):
        return {"intent": "ML_PREDICT"}

    # Single customer predictive risk inquiry (e.g. "risk for customer 14", "evaluate customer 45")
    if re.search(r"\b(risk|assess|score|evaluate)\b.*customer\s*#?\d+", q) or \
       re.search(r"customer\s*#?\d+.*(risk|default probability)", q):
        return {"intent": "ML_PREDICT"}

    # Advanced Pandas analysis intent keywords
    if any(k in q for k in ["correlation matrix", "quantile distribution", "portfolio breakdown", "correlations with default"]):
        return {"intent": "PANDAS_ANALYSIS"}

    # Default to text-to-sql for all tabular, lookup, aggregation, and filtering questions
    return {"intent": "TEXT_TO_SQL"}

def sql_node(state: AgentState) -> dict[str, Any]:
    start_t = time.perf_counter()
    q = state["sanitized_query"]
    
    # Generate SQL
    gen_sql = sql_tool.generate_sql(q)
    
    # Execute query (with AST read-only & cost guardrails & PII masking)
    exec_res = sql_tool.execute_query(gen_sql)

    if not exec_res["success"]:
        err_msg = exec_res["error"]
        return {
            "tool_called": "sql_tool",
            "tool_args": {"query": q},
            "generated_sql": gen_sql,
            "executed_sql": None,
            "query_result": [],
            "query_columns": [],
            "row_count": 0,
            "cost_units": exec_res.get("cost_units", 0),
            "raw_response": f"[GUARDRAIL BLOCKED] {err_msg}",
            "execution_latency_ms": state.get("execution_latency_ms", 0.0) + (time.perf_counter() - start_t) * 1000
        }

    df_masked = exec_res["df_masked"]
    row_count = exec_res["row_count"]
    
    # Build natural language response from query result
    if df_masked.empty:
        ans = "The query executed safely against the enterprise database but returned 0 matching records."
    else:
        sample_rows = df_masked.head(10).to_dict(orient="records")
        cols = list(df_masked.columns)
        
        # Summary synthesis
        if len(cols) <= 4 and row_count <= 5:
            # Inline list
            lines = [f"Found {row_count} record(s):"]
            for r in sample_rows:
                items = [f"{k}: **{v}**" for k, v in r.items()]
                lines.append(" - " + ", ".join(items))
            ans = "\n".join(lines)
        elif len(sample_rows) == 1 and ("count" in cols[0].lower() or "avg" in cols[0].lower() or "sum" in cols[0].lower()):
            # Single aggregate row
            r = sample_rows[0]
            items = [f"{k}: **{v}**" for k, v in r.items()]
            ans = f"Calculated enterprise metrics: {', '.join(items)}."
        else:
            ans = f"Query executed successfully, returning {row_count} row(s). Displaying top {min(row_count, 10)} records with sensitive fields masked."

    return {
        "tool_called": "sql_tool",
        "tool_args": {"query": q},
        "generated_sql": gen_sql,
        "executed_sql": exec_res["executed_sql"],
        "query_result": df_masked.to_dict(orient="records"),
        "query_columns": list(df_masked.columns),
        "row_count": row_count,
        "cost_units": exec_res["cost_units"],
        "raw_response": ans,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0) + (time.perf_counter() - start_t) * 1000
    }

def ml_node(state: AgentState) -> dict[str, Any]:
    start_t = time.perf_counter()
    q = state["sanitized_query"]

    # Extract customer_id if present
    cust_match = re.search(r"customer\s*#?(\d+)", q, re.IGNORECASE)
    cust_id = int(cust_match.group(1)) if cust_match else 1

    # Run ML prediction with SHAP local explanation
    ml_res = ml_tool.predict_risk(customer_id=cust_id)

    top_drivers = [f"{d['feature']} (+{d['shap_value']:.2f})" for d in ml_res["top_risk_drivers"]]
    protective = [f"{d['feature']} ({d['shap_value']:.2f})" for d in ml_res["top_protective_factors"]]

    narrative = ml_res["explanation_narrative"]
    cust_name = ml_res.get("full_name", f"Customer {cust_id}")

    response = (
        f"### Explainable Credit Risk Assessment for {cust_name} (ID: {cust_id})\n\n"
        f"- Predicted Default Probability: {ml_res['prediction_probability'] * 100:.2f}%\n"
        f"- Risk Classification: {ml_res['risk_tier']}\n"
        f"- Baseline Population Expectation: {ml_res['base_probability'] * 100:.2f}%\n\n"
        f"SHAP Attribution Breakdown (Why this prediction was made):\n"
        f"- Top Risk Elevators: {', '.join(top_drivers) if top_drivers else 'None'}\n"
        f"- Top Protective Factors: {', '.join(protective) if protective else 'None'}\n\n"
        f"> Audit Note: {narrative}"
    )

    return {
        "tool_called": "ml_tool",
        "tool_args": {"customer_id": cust_id},
        "generated_sql": f"-- Feature retrieval for customer {cust_id}",
        "executed_sql": f"SELECT * FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE c.customer_id = {cust_id}",
        "query_result": [],
        "query_columns": [],
        "row_count": 1,
        "cost_units": 150,
        "ml_prediction": ml_res["prediction_probability"],
        "risk_tier": ml_res["risk_tier"],
        "shap_top_features": [d["feature"] for d in ml_res["top_risk_drivers"]],
        "shap_explanation": ml_res,
        "raw_response": response,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0) + (time.perf_counter() - start_t) * 1000
    }

def pandas_node(state: AgentState) -> dict[str, Any]:
    start_t = time.perf_counter()
    report = pandas_tool.analyze_portfolio_risk()

    lines = [
        "### Portfolio Tabular Analytics & Correlation Summary\n",
        f"- Total Active Loans Analyzed: {report['total_loans']:,}",
        f"- Total Portfolio Principal: ${report['total_exposure']:,.2f}",
        f"- Portfolio Default Rate: {report['overall_default_rate_pct']}% ({report['total_defaults']:,} defaults)\n",
        "Key Default Correlation Factors (Pandas Pearson Analysis):"
    ]
    for feat, corr in report["correlations_with_default"].items():
        direction = "Positive (Risk Increasing)" if corr > 0 else "Negative (Protective)"
        lines.append(f" - `{feat}`: {corr:+.4f} ({direction})")

    response = "\n".join(lines) + f"\n\n> {report['narrative']}"

    return {
        "tool_called": "pandas_tool",
        "tool_args": {"mode": "portfolio_risk"},
        "generated_sql": "-- Aggregation executed via Pandas DataFrame memory engine",
        "executed_sql": "SELECT * FROM loans l JOIN customers c ON l.customer_id = c.customer_id",
        "query_result": report["by_loan_type"],
        "query_columns": list(report["by_loan_type"][0].keys()) if report["by_loan_type"] else [],
        "row_count": len(report["by_loan_type"]),
        "cost_units": 450,
        "raw_response": response,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0) + (time.perf_counter() - start_t) * 1000
    }

def hitl_node(state: AgentState) -> dict[str, Any]:
    start_t = time.perf_counter()
    reasons = state.get("guardrail_status", {}).get("hitl_reasons", ["High-impact enterprise action"])
    
    # Register approval request
    req_id = human_approval.create_request(
        trace_id=state.get("trace_id", "PENDING_TRACE"),
        action_type="HIGH_IMPACT_MUTATION_OR_WRITE",
        details=f"Prompt: {state.get('user_query')} | Intercepted: {'; '.join(reasons)}"
    )

    response = (
        f"### High-Impact Guardrail Interception\n\n"
        f"The requested operation requires Human Approval (HITL) before execution.\n\n"
        f"- Approval Request ID: {req_id}\n"
        f"- Status: PENDING REVIEW\n"
        f"- Safety Trigger: {'; '.join(reasons)}\n"
        f"- Enforcement Policy: Enterprise strict read-only and write-prevention rules are active. "
        f"A designated administrator must review and approve this request via the Guardrail Inspector tab before any database modifications can proceed."
    )

    return {
        "tool_called": "hitl_approval_guard",
        "tool_args": {"request_id": req_id},
        "approval_request_id": req_id,
        "raw_response": response,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0) + (time.perf_counter() - start_t) * 1000
    }

def self_verification_node(state: AgentState) -> dict[str, Any]:
    raw_ans = state.get("raw_response", "")
    exec_sql = state.get("executed_sql")
    query_res = state.get("query_result", [])
    df = pd.DataFrame(query_res) if query_res else None

    # Run verification check
    verif = self_verifier.verify_numeric_claim(
        draft_response=raw_ans,
        primary_sql=exec_sql,
        primary_df=df
    )

    return {
        "verification_result": verif,
        "final_response": verif["final_response"]
    }

def audit_logger_node(state: AgentState) -> dict[str, Any]:
    trace_id = audit_logger.log_trace(
        session_id=state.get("session_id", "default_session"),
        trace_id=state.get("trace_id"),
        user_query=state.get("user_query", ""),
        sanitized_query=state.get("sanitized_query", ""),
        intent=state.get("intent", "UNKNOWN"),
        tool_called=state.get("tool_called"),
        tool_args=state.get("tool_args"),
        generated_sql=state.get("generated_sql"),
        executed_sql=state.get("executed_sql"),
        row_count=state.get("row_count", 0),
        cost_units=state.get("cost_units", 0),
        ml_prediction=state.get("ml_prediction"),
        shap_top_features=state.get("shap_top_features", []),
        guardrail_flags=state.get("guardrail_status"),
        verification_status=state.get("verification_result", {}).get("status"),
        verification_discrepancy=state.get("verification_result", {}).get("discrepancy", 0.0),
        agent_response=state.get("final_response"),
        execution_latency_ms=state.get("execution_latency_ms", 0.0),
        replayable_state={
            "session_id": state.get("session_id"),
            "intent": state.get("intent"),
            "tool_called": state.get("tool_called"),
            "executed_sql": state.get("executed_sql"),
            "row_count": state.get("row_count", 0),
            "ml_prediction": state.get("ml_prediction")
        }
    )

    return {"trace_id": trace_id}
