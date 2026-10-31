import json
import time
from pathlib import Path
from typing import Any
from auditagent.core.config import DATA_DIR
from auditagent.benchmarks.eval_sql import sql_evaluator
from auditagent.benchmarks.eval_guardrails import guardrail_evaluator
from auditagent.benchmarks.eval_faithfulness import faithfulness_evaluator
from auditagent.benchmarks.eval_hallucination import hallucination_evaluator

BENCHMARK_RESULTS_FILE = DATA_DIR / "benchmark_results.json"

def run_all_benchmarks() -> dict[str, Any]:
    print("=" * 60)
    print("STARTING AUDITAGENT COMPREHENSIVE BENCHMARK EVALUATION")
    print("=" * 60)

    start_total = time.perf_counter()

    # 1. SQL Correctness against Gold Set 50+
    print("\n[1/4] Running SQL Correctness Evaluation against 52 Gold Questions...")
    t0 = time.perf_counter()
    sql_report = sql_evaluator.evaluate_gold_set()
    sql_time = time.perf_counter() - t0
    print(f" -> SQL Gold Set finished in {sql_time:.2f}s | Match Rate: {sql_report['exact_match_rate_pct']}% | Execution Rate: {sql_report['execution_rate_pct']}%")

    # 2. Guardrail Block Rate against 30 Adversarial Attacks
    print("\n[2/4] Running Guardrail Penetration Evaluation against 30 Adversarial Attacks...")
    t0 = time.perf_counter()
    guardrail_report = guardrail_evaluator.evaluate_attacks()
    guard_time = time.perf_counter() - t0
    print(f" -> Guardrail Suite finished in {guard_time:.2f}s | Block Rate: {guardrail_report['block_rate_pct']}% ({guardrail_report['blocked_count']}/{guardrail_report['total_adversarial_queries']})")

    # 3. SHAP Explanation Faithfulness Evaluation
    print("\n[3/4] Running SHAP Explanation Faithfulness & Monotonicity Evaluation...")
    t0 = time.perf_counter()
    faithfulness_report = faithfulness_evaluator.evaluate_faithfulness(sample_size=40)
    faith_time = time.perf_counter() - t0
    print(f" -> Faithfulness finished in {faith_time:.2f}s | Faithfulness Score: {faithfulness_report['faithfulness_score_pct']}% | Monotonicity: {faithfulness_report['monotonicity_rate_pct']}%")

    # 4. Hallucinated Number Rate With vs Without Verification
    print("\n[4/4] Running Hallucination Rate Evaluation (With vs Without Self-Verification)...")
    t0 = time.perf_counter()
    hallucination_report = hallucination_evaluator.evaluate_hallucination_rates()
    hall_time = time.perf_counter() - t0
    print(f" -> Hallucination Suite finished in {hall_time:.2f}s | Without Verif: {hallucination_report['hallucination_rate_without_verification_pct']}% -> With Verif: {hallucination_report['hallucination_rate_with_verification_pct']}% | Reduction: {hallucination_report['relative_reduction_pct']}%")

    total_time = time.perf_counter() - start_total

    summary = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_benchmark_duration_seconds": round(total_time, 2),
        "headline_metrics": {
            "sql_gold_questions_evaluated": sql_report["total_questions"],
            "sql_execution_success_rate": f"{sql_report['execution_rate_pct']}%",
            "sql_guardrail_compliance": f"{sql_report['guardrail_compliance_pct']}%",
            "sql_exact_semantic_match_rate": f"{sql_report['exact_match_rate_pct']}%",
            "guardrail_attacks_tested": guardrail_report["total_adversarial_queries"],
            "guardrail_attack_block_rate": f"{guardrail_report['block_rate_pct']}%",
            "shap_explanation_faithfulness_score": f"{faithfulness_report['faithfulness_score_pct']}%",
            "shap_monotonicity_consistency": f"{faithfulness_report['monotonicity_rate_pct']}%",
            "hallucination_rate_without_verification": f"{hallucination_report['hallucination_rate_without_verification_pct']}%",
            "hallucination_rate_with_verification": f"{hallucination_report['hallucination_rate_with_verification_pct']}%",
            "hallucination_relative_reduction": f"{hallucination_report['relative_reduction_pct']}%"
        },
        "sql_report": sql_report,
        "guardrail_report": guardrail_report,
        "faithfulness_report": faithfulness_report,
        "hallucination_report": hallucination_report
    }

    # Save to disk
    with open(BENCHMARK_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nAll benchmark results successfully saved to: {BENCHMARK_RESULTS_FILE}")

    return summary

def get_cached_or_run_benchmarks() -> dict[str, Any]:
    if BENCHMARK_RESULTS_FILE.exists():
        try:
            with open(BENCHMARK_RESULTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return run_all_benchmarks()

if __name__ == "__main__":
    run_all_benchmarks()
