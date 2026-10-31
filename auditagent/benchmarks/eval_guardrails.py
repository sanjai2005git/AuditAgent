from typing import Any
from auditagent.benchmarks.guardrail_test_suite import ADVERSARIAL_QUERY_SUITE
from auditagent.guardrails.sql_enforcer import sql_enforcer
from auditagent.guardrails.cost_limiter import cost_limiter
from auditagent.guardrails.human_approval import human_approval

class GuardrailEvaluator:
    def evaluate_attacks(self) -> dict[str, Any]:
        """
        Executes adversarial test suite against AST enforcer, cost limiter, and HITL evaluator.
        """
        total = len(ADVERSARIAL_QUERY_SUITE)
        blocked_count = 0
        allowed_count = 0

        type_metrics = {}
        details = []

        for item in ADVERSARIAL_QUERY_SUITE:
            q_id = item["id"]
            atk_type = item["type"]
            query = item["query"]
            should_block = item["should_block"]

            if atk_type not in type_metrics:
                type_metrics[atk_type] = {"total": 0, "blocked": 0}
            type_metrics[atk_type]["total"] += 1

            # Test 1: Check HITL / Prompt Inspection
            hitl_res = human_approval.evaluate_action("PROMPT", query)
            blocked_by_hitl = hitl_res["requires_approval"]

            # Test 2: Check SQL AST inspection
            enforce_res = sql_enforcer.inspect_query(query)
            blocked_by_enforcer = not enforce_res["passed"]

            # Test 3: Check Cost limiter
            cost_res = cost_limiter.estimate_cost(query)
            blocked_by_cost = not cost_res["passed"]

            is_blocked = blocked_by_hitl or blocked_by_enforcer or blocked_by_cost
            reason = []
            if blocked_by_enforcer:
                reason.append(f"SQL Guardrail: {enforce_res['reason']}")
            if blocked_by_cost:
                reason.append(f"Cost Guardrail: {cost_res['reason']}")
            if blocked_by_hitl:
                reason.append(f"HITL Guardrail: {hitl_res['summary']}")

            if is_blocked:
                blocked_count += 1
                type_metrics[atk_type]["blocked"] += 1
            else:
                allowed_count += 1

            details.append({
                "id": q_id,
                "type": atk_type,
                "query": query,
                "is_blocked": is_blocked,
                "expected_blocked": should_block,
                "defense_layer": "AST / Lexical / HITL / Cost",
                "reasons": "; ".join(reason) if reason else "Allowed"
            })

        block_rate = round((blocked_count / total) * 100, 2)

        return {
            "total_adversarial_queries": total,
            "blocked_count": blocked_count,
            "allowed_count": allowed_count,
            "block_rate_pct": block_rate,
            "threat_category_metrics": type_metrics,
            "details": details
        }

guardrail_evaluator = GuardrailEvaluator()

if __name__ == "__main__":
    rep = guardrail_evaluator.evaluate_attacks()
    print(f"Total Adversarial Attacks Tested: {rep['total_adversarial_queries']}")
    print(f"Blocked Count: {rep['blocked_count']}/{rep['total_adversarial_queries']}")
    print(f"Guardrail Block Rate: {rep['block_rate_pct']}%")
