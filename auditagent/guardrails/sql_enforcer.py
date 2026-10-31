import re
from typing import Any
import sqlglot
from sqlglot import exp
from auditagent.core.config import settings

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "ATTACH", "DETACH", "COPY",
    "EXPORT", "PRAGMA", "VACUUM", "INSTALL", "LOAD", "CHECKPOINT",
    "INTO OUTFILE", "INTO DUMPFILE", "INFORMATION_SCHEMA.SYSTEM",
    "READ_CSV", "READ_PARQUET", "WRITE_CSV", "WRITE_PARQUET"
]

class SQLEnforcer:
    def __init__(self, strict_read_only: bool = settings.strict_read_only):
        self.strict_read_only = strict_read_only
        self.allowed_tables = {"customers", "accounts", "loans", "transactions"}

    def inspect_query(self, sql: str) -> dict[str, Any]:
        """
        Validates SQL query against AST and lexical guardrails.
        Returns:
            passed (bool): True if safe to execute.
            violation_type (str): Category of violation (e.g. 'DML_DETECTED', 'DDL_DETECTED', 'MULTI_STATEMENT', 'SYNTAX_ERROR')
            reason (str): Human-readable audit explanation.
            ast_type (str): The primary SQL statement type (e.g. 'Select')
        """
        if not sql or not sql.strip():
            return {
                "passed": False,
                "violation_type": "EMPTY_QUERY",
                "reason": "Query string is empty.",
                "ast_type": None
            }

        raw_sql = sql.strip()
        upper_sql = raw_sql.upper()

        # 1. Lexical checks for forbidden keywords (fast path)
        for kw in FORBIDDEN_KEYWORDS:
            # Match whole keyword with boundary
            pattern = rf"\b{kw}\b"
            if re.search(pattern, upper_sql):
                return {
                    "passed": False,
                    "violation_type": "FORBIDDEN_KEYWORD_DETECTED",
                    "reason": f"Query contains forbidden keyword '{kw}'. Strictly read-only operations permitted.",
                    "ast_type": kw
                }

        # 2. Multi-statement injection check (e.g. "SELECT 1; DROP TABLE...")
        # Check for non-trailing semicolons
        stmts_raw = [s.strip() for s in raw_sql.split(";") if s.strip()]
        if len(stmts_raw) > 1:
            return {
                "passed": False,
                "violation_type": "MULTI_STATEMENT_INJECTION",
                "reason": f"Query contains {len(stmts_raw)} statements separated by semicolons. Only single SELECT statement allowed.",
                "ast_type": "MultiStatement"
            }

        # 3. AST Parser Inspection using sqlglot (DuckDB dialect)
        try:
            parsed = sqlglot.parse(stmts_raw[0], read="duckdb")
        except Exception as e:
            return {
                "passed": False,
                "violation_type": "SYNTAX_ERROR",
                "reason": f"Failed to parse SQL into AST: {str(e)}",
                "ast_type": "Unknown"
            }

        if not parsed or parsed[0] is None:
            return {
                "passed": False,
                "violation_type": "EMPTY_AST",
                "reason": "Query produced empty AST.",
                "ast_type": None
            }

        expression = parsed[0]
        expr_name = expression.__class__.__name__

        # Must be a Select or Union or Expression with Select
        is_select = isinstance(expression, (exp.Select, exp.Union))
        if not is_select:
            # Check if it is a CTE query (e.g. WITH cte AS (...) SELECT ...)
            if isinstance(expression, exp.Expression) and expression.find(exp.Select):
                is_select = True

        if not is_select:
            return {
                "passed": False,
                "violation_type": "NON_SELECT_STATEMENT",
                "reason": f"Query AST root is '{expr_name}', expected 'Select'. Write, administrative, and DDL operations are blocked.",
                "ast_type": expr_name
            }

        # 4. Deep AST inspection: verify no subexpressions contain DML or harmful constructs
        forbidden_expr_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
            exp.Alter, exp.Command, exp.Pragma, exp.Grant, exp.Revoke
        )
        for node in expression.walk():
            if isinstance(node, forbidden_expr_types):
                return {
                    "passed": False,
                    "violation_type": "MUTATION_IN_SUBQUERY",
                    "reason": f"Found forbidden AST node '{node.__class__.__name__}' embedded in expression.",
                    "ast_type": node.__class__.__name__
                }

        # 5. Table reference validation
        tables_referenced = set()
        for tbl in expression.find_all(exp.Table):
            t_name = tbl.name.lower()
            tables_referenced.add(t_name)

        # Allow CTE alias names
        cte_aliases = set()
        for cte in expression.find_all(exp.CTE):
            if cte.alias:
                cte_aliases.add(cte.alias.lower())

        disallowed_tables = (tables_referenced - self.allowed_tables) - cte_aliases
        if disallowed_tables:
            return {
                "passed": False,
                "violation_type": "UNAUTHORIZED_TABLE_ACCESS",
                "reason": f"Query references non-permitted tables: {disallowed_tables}. Permitted tables: {list(self.allowed_tables)}",
                "ast_type": "Select"
            }

        return {
            "passed": True,
            "violation_type": None,
            "reason": "Query passed all read-only AST safety guardrails.",
            "ast_type": expr_name,
            "tables": list(tables_referenced)
        }

sql_enforcer = SQLEnforcer()
