import json
import uuid
import datetime
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from auditagent.core.config import settings, AUDIT_LOG_DIR
from auditagent.data.database import db_manager

class AuditLogger:
    def __init__(self, log_dir: Path = AUDIT_LOG_DIR):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_trace(
        self,
        session_id: str,
        user_query: str,
        sanitized_query: str,
        intent: str,
        trace_id: Optional[str] = None,
        tool_called: Optional[str] = None,
        tool_args: Optional[dict[str, Any]] = None,
        generated_sql: Optional[str] = None,
        executed_sql: Optional[str] = None,
        row_count: int = 0,
        cost_units: int = 0,
        ml_prediction: Optional[float] = None,
        shap_top_features: Optional[list[str]] = None,
        guardrail_flags: Optional[dict[str, Any]] = None,
        verification_status: Optional[str] = None,
        verification_discrepancy: float = 0.0,
        agent_response: Optional[str] = None,
        execution_latency_ms: float = 0.0,
        replayable_state: Optional[dict[str, Any]] = None
    ) -> str:
        trace_id = trace_id or f"TRC-{uuid.uuid4().hex[:12].upper()}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        shap_str = ", ".join(shap_top_features) if shap_top_features else None
        guardrails_str = json.dumps(guardrail_flags or {})
        replay_state_str = json.dumps(replayable_state or {})

        # 1. Store in DuckDB audit_trails table
        insert_sql = """
        INSERT INTO audit_trails (
            trace_id, session_id, timestamp, user_query, sanitized_query,
            intent, tool_called, generated_sql, executed_sql, row_count,
            cost_units, ml_prediction, shap_top_features, guardrail_flags,
            verification_status, verification_discrepancy, agent_response,
            execution_latency_ms, replayable_state_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            trace_id, session_id, now_iso, user_query, sanitized_query,
            intent, tool_called, generated_sql, executed_sql, row_count,
            cost_units, ml_prediction, shap_str, guardrails_str,
            verification_status, verification_discrepancy, agent_response,
            execution_latency_ms, replay_state_str
        ]
        db_manager.execute_write(insert_sql, params)

        # 2. Store JSON file on disk for persistent file trace replay
        trace_record = {
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": now_iso,
            "user_query": user_query,
            "sanitized_query": sanitized_query,
            "intent": intent,
            "tool_called": tool_called,
            "tool_args": tool_args,
            "generated_sql": generated_sql,
            "executed_sql": executed_sql,
            "row_count": row_count,
            "cost_units": cost_units,
            "ml_prediction": ml_prediction,
            "shap_top_features": shap_top_features,
            "guardrail_flags": guardrail_flags,
            "verification_status": verification_status,
            "verification_discrepancy": verification_discrepancy,
            "agent_response": agent_response,
            "execution_latency_ms": execution_latency_ms,
            "replayable_state": replayable_state
        }
        
        file_path = self.log_dir / f"{trace_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trace_record, f, indent=2)

        return trace_id

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        # Check disk first
        file_path = self.log_dir / f"{trace_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback to DuckDB
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute(f"SELECT * FROM audit_trails WHERE trace_id = '{trace_id}'").fetch_df()
            if not df.empty:
                df = df.astype(object).where(pd.notnull(df), None)
                row = df.iloc[0].to_dict()
                if row.get("guardrail_flags"):
                    try: row["guardrail_flags"] = json.loads(row["guardrail_flags"])
                    except Exception: pass
                if row.get("replayable_state_json"):
                    try: row["replayable_state"] = json.loads(row["replayable_state_json"])
                    except Exception: pass
                return row
            return None
        finally:
            conn.close()

    def get_recent_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute(
                f"SELECT * FROM audit_trails ORDER BY timestamp DESC LIMIT {limit}"
            ).fetch_df()
            if df.empty:
                return []
            df = df.astype(object).where(pd.notnull(df), None)
            records = df.to_dict(orient="records")
            # Parse json sub-strings if present
            for r in records:
                if r.get("guardrail_flags") and isinstance(r["guardrail_flags"], str):
                    try: r["guardrail_flags"] = json.loads(r["guardrail_flags"])
                    except Exception: pass
            return records
        finally:
            conn.close()

audit_logger = AuditLogger()
