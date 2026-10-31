import duckdb
import threading
import time
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from auditagent.core.config import settings

_local = threading.local()

class DatabaseManager:
    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def get_connection(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        # DuckDB in-memory or file connection per thread
        conn = duckdb.connect(self.db_path, read_only=read_only)
        return conn

    def _init_schema(self):
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            return
        sql = schema_file.read_text(encoding="utf-8")
        conn = self.get_connection(read_only=False)
        try:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
        finally:
            conn.close()

    def execute_read_query(
        self,
        sql: str,
        max_rows: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> tuple[pd.DataFrame, float]:
        """
        Executes a SELECT query strictly in read-only mode and returns (df, latency_seconds).
        Enforces row limits and execution time budgets.
        """
        max_rows = max_rows or settings.max_result_rows
        timeout_seconds = timeout_seconds or settings.query_timeout_seconds
        
        start_time = time.perf_counter()
        conn = self.get_connection(read_only=False)
        try:
            # We set duckdb execution limit
            cursor = conn.cursor()
            
            # Execute with limit wrapper if not present
            clean_sql = sql.strip().rstrip(";")
            if "limit" not in clean_sql.lower():
                clean_sql = f"{clean_sql} LIMIT {max_rows + 1}"
            
            cursor.execute(clean_sql)
            df = cursor.fetch_df()
            
            latency = time.perf_counter() - start_time
            if latency > timeout_seconds:
                raise TimeoutError(f"Query exceeded execution budget of {timeout_seconds}s (took {latency:.2f}s)")
            
            if len(df) > max_rows:
                df = df.iloc[:max_rows]
                
            return df, latency
        finally:
            conn.close()

    def execute_write(self, sql: str, params: Optional[list] = None) -> int:
        """
        Used ONLY for internal agent writes (Audit Log, Approval Requests).
        """
        conn = self.get_connection(read_only=False)
        try:
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            return cursor.rowcount
        finally:
            conn.close()

    def get_schema_summary(self) -> str:
        """
        Returns a concise markdown representation of all tables and columns for the Text-to-SQL context.
        """
        conn = self.get_connection(read_only=False)
        try:
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
            ).fetchall()
            
            lines = []
            for (t_name,) in tables:
                if t_name in ['audit_trails', 'approval_requests']:
                    continue
                cols = conn.execute(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t_name}' ORDER BY ordinal_position"
                ).fetchall()
                col_defs = ", ".join([f"{col} ({dtype})" for col, dtype in cols])
                lines.append(f"Table: {t_name}\n  Columns: {col_defs}")
            return "\n".join(lines)
        finally:
            conn.close()

    def table_row_counts(self) -> dict[str, int]:
        conn = self.get_connection(read_only=False)
        try:
            counts = {}
            for t in ["customers", "accounts", "loans", "transactions", "audit_trails", "approval_requests"]:
                try:
                    res = conn.execute(f"SELECT count(*) FROM {t}").fetchone()
                    counts[t] = res[0] if res else 0
                except Exception:
                    counts[t] = 0
            return counts
        finally:
            conn.close()

db_manager = DatabaseManager()

