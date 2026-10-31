import pytest
import pandas as pd
from auditagent.data.database import db_manager
from auditagent.tools.sql_tool import sql_tool

def test_database_connection_and_counts():
    counts = db_manager.table_row_counts()
    assert counts["customers"] >= 1000
    assert counts["loans"] >= 1500
    assert counts["accounts"] >= 1000
    assert counts["transactions"] >= 5000

def test_read_query_row_cap():
    # Attempting to fetch all customers should be capped by max_result_rows
    df, lat = db_manager.execute_read_query("SELECT * FROM customers", max_rows=50)
    assert len(df) == 50
    assert lat > 0

def test_sql_tool_execution():
    res = sql_tool.execute_query("SELECT COUNT(*) as count FROM customers")
    assert res["success"] is True
    assert res["row_count"] == 1
    assert "count" in res["columns"]

def test_sql_tool_pii_redaction_in_output():
    res = sql_tool.execute_query("SELECT customer_id, full_name, email, ssn FROM customers LIMIT 5")
    assert res["success"] is True
    df_masked = res["df_masked"]
    # Verify emails are masked
    assert all("@" in str(e) and "***@" in str(e) for e in df_masked["email"])
    # Verify SSNs are masked
    assert all("***-**-" in str(s) for s in df_masked["ssn"])

