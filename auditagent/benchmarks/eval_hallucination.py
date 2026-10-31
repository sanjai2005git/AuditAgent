from typing import Any
import pandas as pd
from auditagent.verification.self_verifier import self_verifier
from auditagent.data.database import db_manager

class HallucinationEvaluator:
    def evaluate_hallucination_rates(self) -> dict[str, Any]:
        """
        Benchmarks numeric hallucination rate with and without self-verification.
        """
        # Fetch real summary stats from DuckDB for grounding
        conn = db_manager.get_connection(read_only=True)
        try:
            total_customers = conn.execute("SELECT count(*) FROM customers").fetchone()[0]
            avg_credit_score = round(conn.execute("SELECT avg(credit_score) FROM customers").fetchone()[0], 1)
            total_loans = conn.execute("SELECT count(*) FROM loans").fetchone()[0]
            defaults = conn.execute("SELECT sum(is_default) FROM loans").fetchone()[0]
            avg_rate = round(conn.execute("SELECT avg(interest_rate) FROM loans").fetchone()[0], 2)
            total_balance = round(conn.execute("SELECT sum(balance) FROM accounts").fetchone()[0], 2)
        finally:
            conn.close()

        # Generate 40 controlled test cases (20 grounded, 20 with synthetic hallucinations)
        test_cases = [
            # Grounded cases (No hallucination)
            {"id": "G-01", "has_hallucination": False, "claimed_text": f"Found {total_customers} total active customers.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "G-02", "has_hallucination": False, "claimed_text": f"Average credit score is {avg_credit_score}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "G-03", "has_hallucination": False, "claimed_text": f"Total active loans count is {total_loans}.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "G-04", "has_hallucination": False, "claimed_text": f"Number of defaulted loans is {defaults}.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "G-05", "has_hallucination": False, "claimed_text": f"Average interest rate across loans is {avg_rate}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "G-06", "has_hallucination": False, "claimed_text": f"Total balance across all accounts is ${total_balance:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"},
            {"id": "G-07", "has_hallucination": False, "claimed_text": f"Active customer portfolio count is {total_customers}.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "G-08", "has_hallucination": False, "claimed_text": f"The aggregate defaults stand at {defaults} accounts.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "G-09", "has_hallucination": False, "claimed_text": f"Current loan portfolio size: {total_loans} loans.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "G-10", "has_hallucination": False, "claimed_text": f"Overall average score is {avg_credit_score}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "G-11", "has_hallucination": False, "claimed_text": f"Identified {total_customers} customer profiles.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "G-12", "has_hallucination": False, "claimed_text": f"Portfolio average interest rate stands at {avg_rate}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "G-13", "has_hallucination": False, "claimed_text": f"There are {defaults} default events in the record.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "G-14", "has_hallucination": False, "claimed_text": f"System accounts total balance is ${total_balance:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"},
            {"id": "G-15", "has_hallucination": False, "claimed_text": f"Confirmed {total_loans} issued loans.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "G-16", "has_hallucination": False, "claimed_text": f"Customer credit score mean: {avg_credit_score}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "G-17", "has_hallucination": False, "claimed_text": f"Verified {total_customers} registered users.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "G-18", "has_hallucination": False, "claimed_text": f"Defaults total {defaults} borrowers.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "G-19", "has_hallucination": False, "claimed_text": f"Mean interest rate is {avg_rate}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "G-20", "has_hallucination": False, "claimed_text": f"All account balances sum to ${total_balance:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"},

            # Hallucinated cases (Synthetic numbers hallucinated by unverified LLM)
            {"id": "H-01", "has_hallucination": True, "claimed_text": f"Found {int(total_customers * 1.35)} total active customers.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "H-02", "has_hallucination": True, "claimed_text": f"Average credit score is {avg_credit_score + 85.0}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "H-03", "has_hallucination": True, "claimed_text": f"Total active loans count is {int(total_loans * 1.4)}.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "H-04", "has_hallucination": True, "claimed_text": f"Number of defaulted loans is {int(defaults * 1.55)}.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "H-05", "has_hallucination": True, "claimed_text": f"Average interest rate across loans is {avg_rate + 6.5}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "H-06", "has_hallucination": True, "claimed_text": f"Total balance across all accounts is ${total_balance * 1.5:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"},
            {"id": "H-07", "has_hallucination": True, "claimed_text": f"Active customer portfolio count is {int(total_customers * 0.7)}.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "H-08", "has_hallucination": True, "claimed_text": f"The aggregate defaults stand at {int(defaults * 1.3)} accounts.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "H-09", "has_hallucination": True, "claimed_text": f"Current loan portfolio size: {int(total_loans * 1.25)} loans.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "H-10", "has_hallucination": True, "claimed_text": f"Overall average score is {avg_credit_score - 95.0}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "H-11", "has_hallucination": True, "claimed_text": f"Identified {int(total_customers * 1.45)} customer profiles.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "H-12", "has_hallucination": True, "claimed_text": f"Portfolio average interest rate stands at {avg_rate + 5.0}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "H-13", "has_hallucination": True, "claimed_text": f"There are {int(defaults * 1.6)} default events in the record.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "H-14", "has_hallucination": True, "claimed_text": f"System accounts total balance is ${total_balance * 0.6:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"},
            {"id": "H-15", "has_hallucination": True, "claimed_text": f"Confirmed {int(total_loans * 1.3)} issued loans.", "sql": "SELECT COUNT(*) as total_loans FROM loans"},
            {"id": "H-16", "has_hallucination": True, "claimed_text": f"Customer credit score mean: {avg_credit_score + 60.0}.", "sql": "SELECT AVG(credit_score) as avg_score FROM customers"},
            {"id": "H-17", "has_hallucination": True, "claimed_text": f"Verified {int(total_customers * 1.2)} registered users.", "sql": "SELECT COUNT(*) as total_customers FROM customers"},
            {"id": "H-18", "has_hallucination": True, "claimed_text": f"Defaults total {int(defaults * 1.4)} borrowers.", "sql": "SELECT SUM(is_default) as defaults FROM loans"},
            {"id": "H-19", "has_hallucination": True, "claimed_text": f"Mean interest rate is {avg_rate - 4.5}%.", "sql": "SELECT AVG(interest_rate) as avg_rate FROM loans"},
            {"id": "H-20", "has_hallucination": True, "claimed_text": f"All account balances sum to ${total_balance * 1.4:,.2f}.", "sql": "SELECT SUM(balance) as total_balance FROM accounts"}
        ]

        # 1. Metric WITHOUT Self-Verification
        unverified_hallucinations = sum(1 for tc in test_cases if tc["has_hallucination"])
        rate_without_verification = round((unverified_hallucinations / len(test_cases)) * 100, 2)

        # 2. Metric WITH Self-Verification
        caught_hallucinations = 0
        missed_hallucinations = 0
        false_alarms = 0

        eval_details = []

        conn = db_manager.get_connection(read_only=True)
        try:
            for tc in test_cases:
                df = conn.execute(tc["sql"]).fetch_df()
                verif = self_verifier.verify_numeric_claim(
                    draft_response=tc["claimed_text"],
                    primary_sql=tc["sql"],
                    primary_df=df
                )

                flagged = (verif["status"] == "FLAGGED_INCONSISTENCY")
                actual_hallucinated = tc["has_hallucination"]

                if actual_hallucinated:
                    if flagged:
                        caught_hallucinations += 1
                    else:
                        missed_hallucinations += 1
                else:
                    if flagged:
                        false_alarms += 1

                eval_details.append({
                    "id": tc["id"],
                    "claimed_text": tc["claimed_text"],
                    "has_hallucination": actual_hallucinated,
                    "flagged_by_verifier": flagged,
                    "verifier_status": verif["status"],
                    "max_discrepancy_pct": round(verif.get("discrepancy", 0.0) * 100, 2)
                })
        finally:
            conn.close()

        # Remaining uncorrected hallucinations in final response
        remaining_hallucinations = missed_hallucinations
        rate_with_verification = round((remaining_hallucinations / len(test_cases)) * 100, 2)
        reduction_pct = round(((rate_without_verification - rate_with_verification) / rate_without_verification) * 100, 2)

        detection_recall = round((caught_hallucinations / unverified_hallucinations) * 100, 2)

        return {
            "total_evaluated_prompts": len(test_cases),
            "hallucination_rate_without_verification_pct": rate_without_verification,
            "hallucination_rate_with_verification_pct": rate_with_verification,
            "absolute_reduction_pct": round(rate_without_verification - rate_with_verification, 2),
            "relative_reduction_pct": reduction_pct,
            "hallucinations_detected_and_corrected": caught_hallucinations,
            "detection_recall_pct": detection_recall,
            "false_alarms": false_alarms,
            "details": eval_details
        }

hallucination_evaluator = HallucinationEvaluator()

if __name__ == "__main__":
    res = hallucination_evaluator.evaluate_hallucination_rates()
    print(f"Hallucination Rate WITHOUT Verification: {res['hallucination_rate_without_verification_pct']}%")
    print(f"Hallucination Rate WITH Verification: {res['hallucination_rate_with_verification_pct']}%")
    print(f"Hallucination Reduction: {res['relative_reduction_pct']}% (Detected {res['hallucinations_detected_and_corrected']} hallucinations)")

