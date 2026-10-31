import uuid
import datetime
from typing import Any, Optional
from auditagent.core.config import settings
from auditagent.data.database import db_manager

class HumanApprovalManager:
    def __init__(self):
        self.high_impact_keywords = settings.high_impact_keywords
        self.bulk_row_threshold = settings.high_impact_row_threshold

    def evaluate_action(
        self,
        action_type: str,
        details: str,
        proposed_sql: Optional[str] = None,
        estimated_rows: Optional[int] = None,
        risk_probability: Optional[float] = None
    ) -> dict[str, Any]:
        """
        Determines whether the proposed operation triggers a Human-in-the-Loop (HITL) approval gate.
        """
        reasons = []

        # 1. Any write intent or mutation keyword
        lower_details = details.lower()
        for kw in self.high_impact_keywords:
            if kw in lower_details or (proposed_sql and kw in proposed_sql.lower()):
                reasons.append(f"Contains high-impact or mutation keyword '{kw}'")

        # 2. Bulk extraction of sensitive data
        if estimated_rows and estimated_rows > self.bulk_row_threshold:
            reasons.append(f"Bulk data export threshold exceeded ({estimated_rows} > {self.bulk_row_threshold} rows)")

        # 3. High-risk automated credit override
        if risk_probability and risk_probability > 0.65 and "approve" in lower_details:
            reasons.append(f"Attempting automated approval on High-Risk borrower (P(default)={risk_probability:.2%})")

        requires_approval = len(reasons) > 0
        return {
            "requires_approval": requires_approval,
            "reasons": reasons,
            "summary": "; ".join(reasons) if reasons else "Standard automated query - pre-approved."
        }

    def create_request(
        self,
        trace_id: str,
        action_type: str,
        details: str,
        requested_by: str = "AuditAgent"
    ) -> str:
        request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        sql = """
        INSERT INTO approval_requests (request_id, trace_id, action_type, details, requested_by, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
        """
        db_manager.execute_write(sql, [request_id, trace_id, action_type, details, requested_by])
        return request_id

    def decide_request(self, request_id: str, decision: str, reviewer: str) -> bool:
        decision_clean = decision.upper().strip()
        if decision_clean not in ["APPROVED", "REJECTED"]:
            raise ValueError("Decision must be either 'APPROVED' or 'REJECTED'")
        
        sql = """
        UPDATE approval_requests 
        SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE request_id = ?
        """
        rows = db_manager.execute_write(sql, [decision_clean, reviewer, request_id])
        return rows > 0

    def get_pending_requests(self) -> list[dict[str, Any]]:
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute(
                "SELECT * FROM approval_requests WHERE status = 'PENDING' ORDER BY created_at DESC"
            ).fetch_df()
            return df.to_dict(orient="records")
        finally:
            conn.close()

    def get_all_requests(self) -> list[dict[str, Any]]:
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute(
                "SELECT * FROM approval_requests ORDER BY created_at DESC LIMIT 100"
            ).fetch_df()
            return df.to_dict(orient="records")
        finally:
            conn.close()

human_approval = HumanApprovalManager()

