from typing import Any
import sqlglot
from sqlglot import exp
from auditagent.core.config import settings

class CostLimiter:
    def __init__(
        self,
        max_cost_units: int = settings.max_query_cost_units,
        max_result_rows: int = settings.max_result_rows,
        max_joins: int = 4
    ):
        self.max_cost_units = max_cost_units
        self.max_result_rows = max_result_rows
        self.max_joins = max_joins

    def estimate_cost(self, sql: str) -> dict[str, Any]:
        """
        Estimates computational cost units based on AST complexity metrics.
        """
        try:
            parsed = sqlglot.parse_one(sql, read="duckdb")
        except Exception as e:
            return {
                "passed": False,
                "estimated_cost": 999999,
                "reason": f"AST parse error in cost analysis: {str(e)}"
            }

        cost = 100  # Base cost
        join_count = 0
        has_cartesian = False
        subquery_count = 0
        window_count = 0

        for node in parsed.walk():
            # Check explicit joins
            if isinstance(node, exp.Join):
                join_count += 1
                cost += 350
                # Check for cartesian / cross join
                if node.kind and "CROSS" in node.kind.upper():
                    has_cartesian = True
                    cost += 5000
                elif not node.this:
                    has_cartesian = True
                    cost += 4000

            # Subqueries
            elif isinstance(node, exp.Subquery):
                subquery_count += 1
                cost += 300

            # Window functions
            elif isinstance(node, exp.Window):
                window_count += 1
                cost += 400

            # Group By
            elif isinstance(node, exp.Group):
                cost += 250

            # Order By
            elif isinstance(node, exp.Order):
                cost += 150

        all_tables = list(parsed.find_all(exp.Table))

        # Check for unconditional multi-table product without WHERE or ON conditions
        if len(all_tables) > 1:
            where_node = parsed.find(exp.Where)
            explicit_joins = list(parsed.find_all(exp.Join))
            has_join_conditions = any(bool(j.args.get("on") or j.args.get("using")) for j in explicit_joins)
            if not where_node and not has_join_conditions:
                has_cartesian = True
                cost += 15000

        # Total table references
        if len(all_tables) > self.max_joins:
            return {
                "passed": False,
                "estimated_cost": cost,
                "max_cost": self.max_cost_units,
                "join_count": len(all_tables),
                "has_cartesian": has_cartesian,
                "reason": f"Query references {len(all_tables)} tables, exceeding max join depth limit of {self.max_joins}."
            }

        # Check for LIMIT
        limit_node = parsed.find(exp.Limit)
        if not limit_node:
            cost += 500
        else:
            try:
                limit_val = int(limit_node.expression.this)
                if limit_val > self.max_result_rows:
                    cost += (limit_val - self.max_result_rows) * 2
            except Exception:
                pass

        if join_count > self.max_joins:
            return {
                "passed": False,
                "estimated_cost": cost,
                "max_cost": self.max_cost_units,
                "join_count": join_count,
                "has_cartesian": has_cartesian,
                "reason": f"Query join depth ({join_count}) exceeds enterprise limit ({self.max_joins})."
            }

        if has_cartesian:
            return {
                "passed": False,
                "estimated_cost": cost,
                "max_cost": self.max_cost_units,
                "join_count": join_count,
                "has_cartesian": True,
                "reason": "Unconstrained or Cross Join detected. Risk of memory exhaustion."
            }

        if cost > self.max_cost_units:
            return {
                "passed": False,
                "estimated_cost": cost,
                "max_cost": self.max_cost_units,
                "join_count": join_count,
                "has_cartesian": has_cartesian,
                "reason": f"Estimated query cost ({cost} units) exceeds budget limit ({self.max_cost_units} units)."
            }

        return {
            "passed": True,
            "estimated_cost": cost,
            "max_cost": self.max_cost_units,
            "join_count": join_count,
            "has_cartesian": False,
            "reason": f"Query cost within budget ({cost}/{self.max_cost_units} units)."
        }

cost_limiter = CostLimiter()
