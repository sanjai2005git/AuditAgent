import pytest
from auditagent.guardrails.sql_enforcer import sql_enforcer
from auditagent.guardrails.pii_masker import pii_masker
from auditagent.guardrails.cost_limiter import cost_limiter
from auditagent.guardrails.human_approval import human_approval

def test_sql_enforcer_allows_select():
    query = "SELECT customer_id, full_name, credit_score FROM customers WHERE state = 'CA' LIMIT 10"
    res = sql_enforcer.inspect_query(query)
    assert res["passed"] is True
    assert res["violation_type"] is None

def test_sql_enforcer_blocks_drop():
    res = sql_enforcer.inspect_query("DROP TABLE customers")
    assert res["passed"] is False

def test_sql_enforcer_blocks_delete():
    res = sql_enforcer.inspect_query("DELETE FROM loans WHERE is_default = 1")
    assert res["passed"] is False

def test_sql_enforcer_blocks_update():
    res = sql_enforcer.inspect_query("UPDATE customers SET credit_score = 800")
    assert res["passed"] is False

def test_sql_enforcer_blocks_multi_statement():
    res = sql_enforcer.inspect_query("SELECT 1; DROP TABLE loans;")
    assert res["passed"] is False
    assert res["violation_type"] in ["FORBIDDEN_KEYWORD_DETECTED", "MULTI_STATEMENT_INJECTION"]

def test_sql_enforcer_blocks_unauthorized_tables():
    res = sql_enforcer.inspect_query("SELECT * FROM sqlite_master")
    assert res["passed"] is False
    assert res["violation_type"] == "UNAUTHORIZED_TABLE_ACCESS"

def test_pii_masker_text():
    raw = "Customer Alice has email alice@example.com, phone +1-415-555-1234, and SSN 123-45-6789."
    masked, counts = pii_masker.mask_text(raw)
    assert "[MASKED_EMAIL]" in masked
    assert "[MASKED_PHONE]" in masked
    assert "[MASKED_SSN]" in masked
    assert counts["email"] == 1
    assert counts["phone"] == 1
    assert counts["ssn"] == 1

def test_cost_limiter_allows_simple_query():
    sql = "SELECT customer_id, state FROM customers LIMIT 20"
    res = cost_limiter.estimate_cost(sql)
    assert res["passed"] is True
    assert res["estimated_cost"] < 1000

def test_cost_limiter_blocks_cartesian():
    sql = "SELECT * FROM customers, loans, accounts, transactions"
    res = cost_limiter.estimate_cost(sql)
    assert res["passed"] is False
    assert res["has_cartesian"] is True

def test_human_approval_detection():
    res = human_approval.evaluate_action("PROMPT", "Please delete all defaulted loans from the table")
    assert res["requires_approval"] is True
    assert any("delete" in r for r in res["reasons"])
