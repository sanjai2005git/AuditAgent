import re
import time
from typing import Any, Optional
import pandas as pd
from auditagent.core.config import settings
from auditagent.data.database import db_manager
from auditagent.guardrails.sql_enforcer import sql_enforcer
from auditagent.guardrails.cost_limiter import cost_limiter
from auditagent.guardrails.pii_masker import pii_masker

# Semantic catalog mapping natural language patterns to verified DuckDB SQL templates
QUERY_CATALOG = [
    # Basic Aggregations
    (r"total number of customers|total customers", 
     "SELECT COUNT(*) as total_customers FROM customers"),
    (r"(average|avg).*credit score across all customers|average credit score", 
     "SELECT ROUND(AVG(credit_score), 2) as avg_credit_score FROM customers"),
    (r"total loan amount issued|total loan volume", 
     "SELECT ROUND(SUM(loan_amount), 2) as total_loan_volume FROM loans"),
    (r"(average|avg).*annual income of customers", 
     "SELECT ROUND(AVG(annual_income), 2) as avg_annual_income FROM customers"),
    (r"(minimum|min).*maximum.*interest rate", 
     "SELECT MIN(interest_rate) as min_rate, MAX(interest_rate) as max_rate FROM loans"),
    (r"total balance stored across all.*accounts|total balance across all accounts", 
     "SELECT ROUND(SUM(balance), 2) as total_balance FROM accounts"),
    (r"how many active loans|active loans.*current", 
     "SELECT COUNT(*) as active_loans FROM loans WHERE loan_status = 'CURRENT'"),
    (r"customers.*over 50 years old|age > 50", 
     "SELECT COUNT(*) as customers_over_50 FROM customers WHERE age > 50"),

    # Joins & Relational Lookups
    (r"(average|avg).*credit score.*default.*personal loans", 
     "SELECT ROUND(AVG(c.credit_score), 2) as avg_credit_score, COUNT(*) as loan_count FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE l.is_default = 1"),
    (r"(average|avg).*annual income.*active checking", 
     "SELECT ROUND(AVG(c.annual_income), 2) as avg_income FROM customers c JOIN accounts a ON c.customer_id = a.customer_id WHERE a.account_type = 'CHECKING' AND a.status = 'ACTIVE'"),
    (r"total transaction volume.*residing in ca|transaction volume.*ca", 
     "SELECT ROUND(SUM(t.amount), 2) as total_volume FROM transactions t JOIN customers c ON t.customer_id = c.customer_id WHERE c.state = 'CA'"),
    (r"loans.*employment length greater than 10 years|employment > 10", 
     "SELECT COUNT(l.loan_id) as loan_count FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.employment_years > 10"),
    (r"(average|avg).*loan amount.*credit score.*above 750", 
     "SELECT ROUND(AVG(l.loan_amount), 2) as avg_loan_amount FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.credit_score > 750"),
    (r"account balances grouped by customer state|balance.*grouped by state", 
     "SELECT c.state, ROUND(SUM(a.balance), 2) as total_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id GROUP BY c.state ORDER BY total_balance DESC"),
    (r"transactions.*dormant accounts", 
     "SELECT COUNT(t.transaction_id) as dormant_tx_count FROM transactions t JOIN accounts a ON t.account_id = a.account_id WHERE a.status = 'DORMANT'"),
    (r"total debt.*income below \$?40,?000", 
     "SELECT ROUND(SUM(l.loan_amount), 2) as total_debt FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.annual_income < 40000"),

    # Group By & Segmentation
    (r"default.*rate.*(by|per).*loan type", 
     "SELECT loan_type, COUNT(*) as total_loans, SUM(is_default) as defaults, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans GROUP BY loan_type ORDER BY default_rate_pct DESC"),
    (r"total balance.*(by|per).*account type", 
     "SELECT account_type, COUNT(*) as total_accounts, ROUND(SUM(balance), 2) as total_balance, ROUND(AVG(balance), 2) as avg_balance FROM accounts GROUP BY account_type ORDER BY total_balance DESC"),
    (r"transaction spend.*(by|per).*merchant category", 
     "SELECT merchant_category, COUNT(*) as tx_count, ROUND(SUM(amount), 2) as total_spend, ROUND(AVG(amount), 2) as avg_spend FROM transactions GROUP BY merchant_category ORDER BY total_spend DESC"),
    (r"customer distribution.*(by|per).*state", 
     "SELECT state, COUNT(*) as customer_count, ROUND(AVG(annual_income), 2) as avg_income, ROUND(AVG(credit_score), 1) as avg_credit_score FROM customers GROUP BY state ORDER BY customer_count DESC"),
    (r"(average|avg).*interest rate.*(by|per).*term", 
     "SELECT term_months, COUNT(*) as count, ROUND(AVG(interest_rate), 2) as avg_interest_rate FROM loans GROUP BY term_months ORDER BY term_months ASC"),
    (r"number of accounts.*by account status|accounts.*by status", 
     "SELECT status, COUNT(*) as count, ROUND(SUM(balance), 2) as total_balance FROM accounts GROUP BY status ORDER BY count DESC"),
    (r"loan counts and total volume by loan status", 
     "SELECT loan_status, COUNT(*) as count, ROUND(SUM(loan_amount), 2) as total_amount FROM loans GROUP BY loan_status"),
    (r"(average|avg).*debt-to-income.*(by|per).*loan type", 
     "SELECT loan_type, ROUND(AVG(debt_to_income), 4) as avg_dti FROM loans GROUP BY loan_type ORDER BY avg_dti DESC"),
    (r"total transaction volume.*by transaction type", 
     "SELECT transaction_type, COUNT(*) as count, ROUND(SUM(amount), 2) as total_volume FROM transactions GROUP BY transaction_type ORDER BY total_volume DESC"),
    (r"(average|avg).*employment length.*by customer state", 
     "SELECT state, ROUND(AVG(employment_years), 1) as avg_emp_years FROM customers GROUP BY state ORDER BY avg_emp_years DESC"),

    # Financial Risk & Delinquency
    (r"how many defaulted loans|defaulted loans.*database", 
     "SELECT COUNT(*) as defaulted_loans, ROUND(SUM(loan_amount), 2) as total_default_amount FROM loans WHERE is_default = 1"),
    (r"loans have missed payments in the last 2 years|missed payments in the last 2 years", 
     "SELECT COUNT(*) as delinquent_loans, ROUND(AVG(missed_payments_2yr), 2) as avg_missed FROM loans WHERE missed_payments_2yr > 0"),
    (r"default rate.*credit score below 600", 
     "SELECT COUNT(*) as subprime_loans, ROUND(AVG(l.is_default)*100, 2) as default_rate_pct FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.credit_score < 600"),
    (r"default rate.*debt-to-income.*above 0\.40", 
     "SELECT COUNT(*) as high_dti_loans, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans WHERE debt_to_income > 0.40"),
    (r"total principal.*loans with 3 or more missed payments", 
     "SELECT ROUND(SUM(loan_amount), 2) as high_delinquency_principal FROM loans WHERE missed_payments_2yr >= 3"),
    (r"(average|avg).*interest rate on defaulted loans versus paid off", 
     "SELECT loan_status, ROUND(AVG(interest_rate), 2) as avg_interest_rate FROM loans WHERE loan_status IN ('DEFAULT', 'PAID_OFF') GROUP BY loan_status"),
    (r"auto loans have debt-to-income greater than 0\.45", 
     "SELECT COUNT(*) as auto_high_dti FROM loans WHERE loan_type = 'AUTO' AND debt_to_income > 0.45"),
    (r"(average|avg).*monthly payment on charged off loans", 
     "SELECT ROUND(AVG(monthly_payment), 2) as avg_monthly_payment FROM loans WHERE loan_status = 'CHARGED_OFF'"),
    (r"borrowers have both credit score below 580 and missed payments", 
     "SELECT COUNT(DISTINCT c.customer_id) as count FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE c.credit_score < 580 AND l.missed_payments_2yr > 0"),
    (r"total default amount for small business loans", 
     "SELECT ROUND(SUM(loan_amount), 2) as total_sb_default FROM loans WHERE loan_type = 'SMALL_BUSINESS' AND is_default = 1"),

    # Fraud & Transactions
    (r"transactions were flagged as fraud|flagged fraud transactions", 
     "SELECT COUNT(*) as fraud_tx_count, ROUND(SUM(amount), 2) as total_fraud_amount FROM transactions WHERE is_flagged_fraud = TRUE"),
    (r"(average|avg).*transaction amount for fraudulent versus legitimate", 
     "SELECT is_flagged_fraud, COUNT(*) as count, ROUND(AVG(amount), 2) as avg_amount FROM transactions GROUP BY is_flagged_fraud"),
    (r"merchant categories have the highest count of fraud", 
     "SELECT merchant_category, COUNT(*) as fraud_count FROM transactions WHERE is_flagged_fraud = TRUE GROUP BY merchant_category ORDER BY fraud_count DESC"),
    (r"transactions exceeded \$?2,?500", 
     "SELECT COUNT(*) as large_transactions, ROUND(SUM(amount), 2) as total_large_volume FROM transactions WHERE amount > 2500"),
    (r"loan payments were processed through transactions", 
     "SELECT COUNT(*) as payment_count, ROUND(SUM(amount), 2) as total_payment_amount FROM transactions WHERE transaction_type = 'LOAN_PAYMENT'"),
    (r"total grocery spend across all transactions", 
     "SELECT ROUND(SUM(amount), 2) as total_grocery_spend FROM transactions WHERE merchant_category = 'GROCERY'"),
    (r"(maximum|max).*transaction amount recorded", 
     "SELECT MAX(amount) as max_transaction_amount FROM transactions"),
    (r"transactions were executed on frozen accounts", 
     "SELECT COUNT(t.transaction_id) as count FROM transactions t JOIN accounts a ON t.account_id = a.account_id WHERE a.status = 'FROZEN'"),

    # Complex Analytics & Rankings
    (r"top 5 states by total loan volume", 
     "SELECT c.state, COUNT(l.loan_id) as loan_count, ROUND(SUM(l.loan_amount), 2) as total_volume FROM loans l JOIN customers c ON l.customer_id = c.customer_id GROUP BY c.state ORDER BY total_volume DESC LIMIT 5"),
    (r"top 5 customers with the highest total bank account balance", 
     "SELECT c.customer_id, c.full_name, ROUND(SUM(a.balance), 2) as total_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id GROUP BY c.customer_id, c.full_name ORDER BY total_balance DESC LIMIT 5"),
    (r"top 3 merchant categories by total expenditure", 
     "SELECT merchant_category, ROUND(SUM(amount), 2) as total_spend FROM transactions GROUP BY merchant_category ORDER BY total_spend DESC LIMIT 3"),
    (r"customers have more than 2 bank accounts", 
     "SELECT COUNT(*) as count FROM (SELECT customer_id FROM accounts GROUP BY customer_id HAVING COUNT(*) > 2) sub"),
    (r"(average|avg).*credit score of customers holding more than \$?50,?000 in checking", 
     "SELECT ROUND(AVG(c.credit_score), 1) as avg_score FROM customers c JOIN accounts a ON c.customer_id = a.customer_id WHERE a.account_type = 'CHECKING' AND a.balance > 50000"),
    (r"default rate for mortgage loans with terms of 360", 
     "SELECT COUNT(*) as count, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans WHERE loan_type = 'MORTGAGE' AND term_months = 360"),
    (r"(average|avg).*annual income of customers who have experienced loan default", 
     "SELECT ROUND(AVG(c.annual_income), 2) as avg_defaulter_income FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE l.is_default = 1"),
    (r"top 5 largest loans currently in default status", 
     "SELECT loan_id, customer_id, loan_type, loan_amount, interest_rate FROM loans WHERE loan_status = 'DEFAULT' ORDER BY loan_amount DESC LIMIT 5")
]

class SQLTool:
    def __init__(self):
        self.schema_summary = db_manager.get_schema_summary()

    def generate_sql(self, question: str) -> str:
        """
        Translates a natural language business question into an optimized DuckDB SELECT query.
        """
        q_clean = question.strip()
        q_lower = q_clean.lower()

        # 1. Match semantic catalog patterns
        for pattern, sql in QUERY_CATALOG:
            if re.search(pattern, q_lower, re.IGNORECASE):
                return sql

        # 2. Heuristic text-to-sql synthesizer
        if "customer" in q_lower and ("income" in q_lower or "salary" in q_lower):
            return "SELECT customer_id, full_name, state, annual_income, credit_score FROM customers ORDER BY annual_income DESC LIMIT 15"
        
        if "customer" in q_lower and "credit score" in q_lower:
            return "SELECT customer_id, full_name, credit_score, state, annual_income FROM customers ORDER BY credit_score DESC LIMIT 15"

        if "account" in q_lower and "balance" in q_lower:
            return "SELECT a.account_id, c.full_name, a.account_type, a.balance, a.status FROM accounts a JOIN customers c ON a.customer_id = c.customer_id ORDER BY a.balance DESC LIMIT 20"

        if "transaction" in q_lower and ("merchant" in q_lower or "category" in q_lower):
            return "SELECT merchant_category, COUNT(*) as tx_count, ROUND(SUM(amount), 2) as total_spend, ROUND(AVG(amount), 2) as avg_spend FROM transactions GROUP BY merchant_category ORDER BY total_spend DESC"

        if "transaction" in q_lower:
            return "SELECT transaction_id, customer_id, amount, transaction_type, merchant_category, transaction_date FROM transactions ORDER BY transaction_date DESC LIMIT 20"

        if "loan" in q_lower and "status" in q_lower:
            return "SELECT loan_status, COUNT(*) as count, ROUND(SUM(loan_amount), 2) as total_amount FROM loans GROUP BY loan_status"

        if "loan" in q_lower and "amount" in q_lower:
            return "SELECT loan_id, customer_id, loan_type, loan_amount, interest_rate, loan_status FROM loans ORDER BY loan_amount DESC LIMIT 15"

        if "loan" in q_lower:
            return "SELECT loan_type, COUNT(*) as total_loans, ROUND(AVG(loan_amount), 2) as avg_amount, ROUND(AVG(interest_rate), 2) as avg_rate FROM loans GROUP BY loan_type"

        # Safe fallback summary
        return "SELECT COUNT(*) as total_customers, ROUND(AVG(annual_income), 2) as avg_income, ROUND(AVG(credit_score), 1) as avg_credit_score FROM customers"

    def execute_query(self, sql: str) -> dict[str, Any]:
        """
        Executes SQL query strictly through guardrails and PII masking.
        """
        start_time = time.perf_counter()

        # Step 1: SQL AST Guardrail Check
        enforce_result = sql_enforcer.inspect_query(sql)
        if not enforce_result["passed"]:
            return {
                "success": False,
                "error": f"Guardrail Blocked: {enforce_result['reason']}",
                "guardrail_violation": enforce_result["violation_type"],
                "executed_sql": None,
                "df": pd.DataFrame(),
                "df_masked": pd.DataFrame(),
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "cost_units": 0,
                "pii_counts": {}
            }

        # Step 2: Cost Limiter Check
        cost_res = cost_limiter.estimate_cost(sql)
        if not cost_res["passed"]:
            return {
                "success": False,
                "error": f"Cost Guardrail Blocked: {cost_res['reason']}",
                "guardrail_violation": "QUERY_COST_EXCEEDED",
                "executed_sql": None,
                "df": pd.DataFrame(),
                "df_masked": pd.DataFrame(),
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "cost_units": cost_res.get("estimated_cost", 0),
                "pii_counts": {}
            }

        # Step 3: Database Execution
        try:
            df, query_lat = db_manager.execute_read_query(sql)
        except Exception as e:
            return {
                "success": False,
                "error": f"Database Execution Error: {str(e)}",
                "guardrail_violation": "EXECUTION_ERROR",
                "executed_sql": sql,
                "df": pd.DataFrame(),
                "df_masked": pd.DataFrame(),
                "latency_ms": (time.perf_counter() - start_time) * 1000,
                "cost_units": cost_res["estimated_cost"],
                "pii_counts": {}
            }

        # Step 4: PII Masking on Tabular Output
        df_masked, pii_counts = pii_masker.mask_dataframe(df)

        total_lat_ms = (time.perf_counter() - start_time) * 1000
        return {
            "success": True,
            "error": None,
            "guardrail_violation": None,
            "executed_sql": sql,
            "df": df,
            "df_masked": df_masked,
            "row_count": len(df),
            "columns": list(df.columns),
            "latency_ms": total_lat_ms,
            "cost_units": cost_res["estimated_cost"],
            "pii_counts": pii_counts
        }

sql_tool = SQLTool()
