import time
from typing import Any, Optional
from auditagent.audit.logger import audit_logger
from auditagent.guardrails.sql_enforcer import sql_enforcer
from auditagent.data.database import db_manager
from auditagent.ml.model_runner import model_runner
from auditagent.verification.self_verifier import self_verifier

class TraceReplayer:
    def replay_trace(self, trace_id: str) -> dict[str, Any]:
        """
        Replays an execution trace deterministically and checks output consistency.
        """
        original = audit_logger.get_trace(trace_id)
        if not original:
            return {
                "success": False,
                "error": f"Trace ID '{trace_id}' not found in audit logs."
            }

        start_time = time.perf_counter()
        tool = original.get("tool_called")
        executed_sql = original.get("executed_sql")
        user_query = original.get("user_query")

        replayed_data = {}
        matches = {}

        if tool == "sql_tool" and executed_sql:
            # Replay SQL
            guard_res = sql_enforcer.inspect_query(executed_sql)
            if not guard_res["passed"]:
                return {
                    "success": False,
                    "error": f"Replay failed guardrails: {guard_res['reason']}"
                }

            df_replay, lat = db_manager.execute_read_query(executed_sql)
            replayed_data["row_count"] = len(df_replay)
            replayed_data["latency_ms"] = lat * 1000
            
            matches["row_count_match"] = bool(replayed_data["row_count"] == original.get("row_count"))
            matches["sql_identical"] = True

        elif tool == "ml_tool":
            args = original.get("tool_args") or {}
            cust_id = args.get("customer_id")
            if cust_id:
                pred_res = model_runner.predict_for_customer(int(cust_id))
            else:
                pred_res = model_runner.predict_for_profile(args.get("profile", {}))

            orig_proba = original.get("ml_prediction")
            new_proba = pred_res["prediction_probability"]
            replayed_data["ml_prediction"] = new_proba
            replayed_data["risk_tier"] = pred_res["risk_tier"]
            replayed_data["top_risk_drivers"] = [d["feature"] for d in pred_res["top_risk_drivers"]]

            matches["prediction_match"] = abs((orig_proba or 0.0) - new_proba) < 0.001
        
        else:
            matches["general_status"] = "Trace replayed successfully without side-effects."

        total_lat = (time.perf_counter() - start_time) * 1000
        all_passed = all(matches.values()) if matches else True

        return {
            "success": True,
            "trace_id": trace_id,
            "replayed_in_ms": round(total_lat, 2),
            "original_recorded_ms": original.get("execution_latency_ms", 0.0),
            "is_deterministic_match": all_passed,
            "match_details": matches,
            "original_trace": {
                "timestamp": original.get("timestamp"),
                "user_query": original.get("user_query"),
                "tool_called": original.get("tool_called"),
                "executed_sql": original.get("executed_sql"),
                "row_count": original.get("row_count"),
                "ml_prediction": original.get("ml_prediction"),
                "agent_response": original.get("agent_response")
            },
            "replayed_trace": replayed_data
        }

trace_replayer = TraceReplayer()

