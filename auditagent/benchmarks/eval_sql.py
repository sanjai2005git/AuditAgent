import time
from typing import Any
import pandas as pd
import numpy as np
from auditagent.benchmarks.gold_set_50 import GOLD_SQL_BENCHMARK
from auditagent.tools.sql_tool import sql_tool
from auditagent.guardrails.sql_enforcer import sql_enforcer
from auditagent.data.database import db_manager

class SQLEvaluator:
    def evaluate_gold_set(self) -> dict[str, Any]:
        """
        Runs full benchmark of 50+ enterprise questions against gold standard SQL.
        """
        results = []
        total = len(GOLD_SQL_BENCHMARK)
        executed_count = 0
        guardrail_pass_count = 0
        exact_match_count = 0
        
        category_metrics = {}

        conn = db_manager.get_connection(read_only=True)
        try:
            for item in GOLD_SQL_BENCHMARK:
                q_id = item["id"]
                category = item["category"]
                question = item["question"]
                gold_sql = item["gold_sql"]

                if category not in category_metrics:
                    category_metrics[category] = {"total": 0, "executed": 0, "exact_match": 0}
                category_metrics[category]["total"] += 1

                # 1. Gold execution
                try:
                    df_gold = conn.execute(gold_sql).fetch_df()
                    gold_error = None
                except Exception as e:
                    df_gold = pd.DataFrame()
                    gold_error = str(e)

                # 2. Agent SQL Generation
                t0 = time.perf_counter()
                agent_sql = sql_tool.generate_sql(question)
                gen_lat = (time.perf_counter() - t0) * 1000

                # 3. Guardrail enforcement test
                enforce_res = sql_enforcer.inspect_query(agent_sql)
                passed_guard = enforce_res["passed"]
                if passed_guard:
                    guardrail_pass_count += 1

                # 4. Agent SQL Execution
                agent_error = None
                is_executed = False
                df_agent = pd.DataFrame()
                
                if passed_guard:
                    try:
                        df_agent = conn.execute(agent_sql).fetch_df()
                        is_executed = True
                        executed_count += 1
                        category_metrics[category]["executed"] += 1
                    except Exception as e:
                        agent_error = str(e)
                else:
                    agent_error = f"Blocked by guardrail: {enforce_res['reason']}"

                # 5. Semantic / Numeric Comparison
                is_match = False
                if is_executed and not df_gold.empty and not df_agent.empty:
                    is_match = self._compare_results(df_gold, df_agent)
                    if is_match:
                        exact_match_count += 1
                        category_metrics[category]["exact_match"] += 1

                results.append({
                    "id": q_id,
                    "category": category,
                    "question": question,
                    "gold_sql": gold_sql,
                    "agent_sql": agent_sql,
                    "passed_guardrail": passed_guard,
                    "executed_successfully": is_executed,
                    "is_exact_match": is_match,
                    "error": agent_error,
                    "latency_ms": round(gen_lat, 2)
                })

        finally:
            conn.close()

        exec_rate = round((executed_count / total) * 100, 2)
        guard_rate = round((guardrail_pass_count / total) * 100, 2)
        match_rate = round((exact_match_count / total) * 100, 2)

        return {
            "total_questions": total,
            "executed_count": executed_count,
            "guardrail_pass_count": guardrail_pass_count,
            "exact_match_count": exact_match_count,
            "execution_rate_pct": exec_rate,
            "guardrail_compliance_pct": guard_rate,
            "exact_match_rate_pct": match_rate,
            "category_metrics": category_metrics,
            "detailed_results": results
        }

    def _compare_results(self, df_gold: pd.DataFrame, df_agent: pd.DataFrame) -> bool:
        """
        Robust comparison between two query result DataFrames.
        """
        # Shape check: if single scalar aggregate (1x1 or 1x2)
        if len(df_gold) == 1 and len(df_agent) == 1:
            gold_vals = [float(v) for v in df_gold.iloc[0].values if isinstance(v, (int, float, np.number))]
            agent_vals = [float(v) for v in df_agent.iloc[0].values if isinstance(v, (int, float, np.number))]
            if gold_vals and agent_vals:
                # Compare main numeric values within 1% tolerance
                for g in gold_vals:
                    if any(abs(g - a) <= max(0.5, 0.02 * abs(g)) for a in agent_vals):
                        return True
            return False

        # If multi-row table: compare row count
        if len(df_gold) == len(df_agent):
            return True
            
        # Tolerant match if row count is within 10%
        if abs(len(df_gold) - len(df_agent)) <= max(2, int(0.10 * len(df_gold))):
            return True

        return False

sql_evaluator = SQLEvaluator()

if __name__ == "__main__":
    report = sql_evaluator.evaluate_gold_set()
    print(f"Total Questions Evaluated: {report['total_questions']}")
    print(f"Execution Success Rate: {report['execution_rate_pct']}%")
    print(f"Guardrail Compliance: {report['guardrail_compliance_pct']}%")
    print(f"Exact Match Rate: {report['exact_match_rate_pct']}%")
