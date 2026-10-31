"""
Gold Standard Benchmark: 52 Curated Enterprise Business Questions with Verified DuckDB Ground Truth SQL.
Spans 6 enterprise domains: Aggregations, Joins, Group By, Credit Risk, Fraud Analytics, and Complex Filtering.
"""

GOLD_SQL_BENCHMARK = [
    # 1. Basic Aggregations & Counts (8 queries)
    {
        "id": "AGG-01",
        "category": "Basic Aggregations",
        "question": "What is the total number of customers in the database?",
        "gold_sql": "SELECT COUNT(*) as total_customers FROM customers"
    },
    {
        "id": "AGG-02",
        "category": "Basic Aggregations",
        "question": "What is the average credit score across all customers?",
        "gold_sql": "SELECT ROUND(AVG(credit_score), 2) as avg_credit_score FROM customers"
    },
    {
        "id": "AGG-03",
        "category": "Basic Aggregations",
        "question": "What is the total loan amount issued across all loans?",
        "gold_sql": "SELECT ROUND(SUM(loan_amount), 2) as total_loan_volume FROM loans"
    },
    {
        "id": "AGG-04",
        "category": "Basic Aggregations",
        "question": "What is the average annual income of customers?",
        "gold_sql": "SELECT ROUND(AVG(annual_income), 2) as avg_annual_income FROM customers"
    },
    {
        "id": "AGG-05",
        "category": "Basic Aggregations",
        "question": "What is the minimum and maximum interest rate offered on loans?",
        "gold_sql": "SELECT MIN(interest_rate) as min_rate, MAX(interest_rate) as max_rate FROM loans"
    },
    {
        "id": "AGG-06",
        "category": "Basic Aggregations",
        "question": "What is the total balance stored across all bank accounts?",
        "gold_sql": "SELECT ROUND(SUM(balance), 2) as total_balance FROM accounts"
    },
    {
        "id": "AGG-07",
        "category": "Basic Aggregations",
        "question": "How many active loans are currently in the system?",
        "gold_sql": "SELECT COUNT(*) as active_loans FROM loans WHERE loan_status = 'CURRENT'"
    },
    {
        "id": "AGG-08",
        "category": "Basic Aggregations",
        "question": "How many customers are over 50 years old?",
        "gold_sql": "SELECT COUNT(*) as customers_over_50 FROM customers WHERE age > 50"
    },

    # 2. Joins & Relational Lookups (8 queries)
    {
        "id": "JOIN-01",
        "category": "Joins & Lookups",
        "question": "What is the average credit score of customers who defaulted on personal loans?",
        "gold_sql": "SELECT ROUND(AVG(c.credit_score), 2) as avg_credit_score, COUNT(*) as loan_count FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE l.is_default = 1"
    },
    {
        "id": "JOIN-02",
        "category": "Joins & Lookups",
        "question": "Find the average annual income of customers holding active checking accounts.",
        "gold_sql": "SELECT ROUND(AVG(c.annual_income), 2) as avg_income FROM customers c JOIN accounts a ON c.customer_id = a.customer_id WHERE a.account_type = 'CHECKING' AND a.status = 'ACTIVE'"
    },
    {
        "id": "JOIN-03",
        "category": "Joins & Lookups",
        "question": "What is the total transaction volume executed by customers residing in CA?",
        "gold_sql": "SELECT ROUND(SUM(t.amount), 2) as total_volume FROM transactions t JOIN customers c ON t.customer_id = c.customer_id WHERE c.state = 'CA'"
    },
    {
        "id": "JOIN-04",
        "category": "Joins & Lookups",
        "question": "How many loans were issued to customers with employment length greater than 10 years?",
        "gold_sql": "SELECT COUNT(l.loan_id) as loan_count FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.employment_years > 10"
    },
    {
        "id": "JOIN-05",
        "category": "Joins & Lookups",
        "question": "What is the average loan amount for customers whose credit score is above 750?",
        "gold_sql": "SELECT ROUND(AVG(l.loan_amount), 2) as avg_loan_amount FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.credit_score > 750"
    },
    {
        "id": "JOIN-06",
        "category": "Joins & Lookups",
        "question": "List total account balances grouped by customer state.",
        "gold_sql": "SELECT c.state, ROUND(SUM(a.balance), 2) as total_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id GROUP BY c.state ORDER BY total_balance DESC"
    },
    {
        "id": "JOIN-07",
        "category": "Joins & Lookups",
        "question": "How many transactions were made on dormant accounts?",
        "gold_sql": "SELECT COUNT(t.transaction_id) as dormant_tx_count FROM transactions t JOIN accounts a ON t.account_id = a.account_id WHERE a.status = 'DORMANT'"
    },
    {
        "id": "JOIN-08",
        "category": "Joins & Lookups",
        "question": "What is the total debt held by customers with annual income below $40,000?",
        "gold_sql": "SELECT ROUND(SUM(l.loan_amount), 2) as total_debt FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.annual_income < 40000"
    },

    # 3. Group By & Segmentations (10 queries)
    {
        "id": "GRP-01",
        "category": "Group By & Segmentation",
        "question": "What is the loan default rate by loan type?",
        "gold_sql": "SELECT loan_type, COUNT(*) as total_loans, SUM(is_default) as defaults, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans GROUP BY loan_type ORDER BY default_rate_pct DESC"
    },
    {
        "id": "GRP-02",
        "category": "Group By & Segmentation",
        "question": "What is the total balance by account type?",
        "gold_sql": "SELECT account_type, COUNT(*) as total_accounts, ROUND(SUM(balance), 2) as total_balance, ROUND(AVG(balance), 2) as avg_balance FROM accounts GROUP BY account_type ORDER BY total_balance DESC"
    },
    {
        "id": "GRP-03",
        "category": "Group By & Segmentation",
        "question": "What is the transaction spend by merchant category?",
        "gold_sql": "SELECT merchant_category, COUNT(*) as tx_count, ROUND(SUM(amount), 2) as total_spend, ROUND(AVG(amount), 2) as avg_spend FROM transactions GROUP BY merchant_category ORDER BY total_spend DESC"
    },
    {
        "id": "GRP-04",
        "category": "Group By & Segmentation",
        "question": "What is the customer distribution by state?",
        "gold_sql": "SELECT state, COUNT(*) as customer_count, ROUND(AVG(annual_income), 2) as avg_income, ROUND(AVG(credit_score), 1) as avg_credit_score FROM customers GROUP BY state ORDER BY customer_count DESC"
    },
    {
        "id": "GRP-05",
        "category": "Group By & Segmentation",
        "question": "What is the average interest rate by term months?",
        "gold_sql": "SELECT term_months, COUNT(*) as count, ROUND(AVG(interest_rate), 2) as avg_interest_rate FROM loans GROUP BY term_months ORDER BY term_months ASC"
    },
    {
        "id": "GRP-06",
        "category": "Group By & Segmentation",
        "question": "Count the number of accounts by account status.",
        "gold_sql": "SELECT status, COUNT(*) as count, ROUND(SUM(balance), 2) as total_balance FROM accounts GROUP BY status ORDER BY count DESC"
    },
    {
        "id": "GRP-07",
        "category": "Group By & Segmentation",
        "question": "Calculate loan counts and total volume by loan status.",
        "gold_sql": "SELECT loan_status, COUNT(*) as count, ROUND(SUM(loan_amount), 2) as total_amount FROM loans GROUP BY loan_status"
    },
    {
        "id": "GRP-08",
        "category": "Group By & Segmentation",
        "question": "What is the average debt-to-income ratio by loan type?",
        "gold_sql": "SELECT loan_type, ROUND(AVG(debt_to_income), 4) as avg_dti FROM loans GROUP BY loan_type ORDER BY avg_dti DESC"
    },
    {
        "id": "GRP-09",
        "category": "Group By & Segmentation",
        "question": "What is the total transaction volume broken down by transaction type?",
        "gold_sql": "SELECT transaction_type, COUNT(*) as count, ROUND(SUM(amount), 2) as total_volume FROM transactions GROUP BY transaction_type ORDER BY total_volume DESC"
    },
    {
        "id": "GRP-10",
        "category": "Group By & Segmentation",
        "question": "What is the average employment length grouped by customer state?",
        "gold_sql": "SELECT state, ROUND(AVG(employment_years), 1) as avg_emp_years FROM customers GROUP BY state ORDER BY avg_emp_years DESC"
    },

    # 4. Financial Risk & Delinquency (10 queries)
    {
        "id": "RSK-01",
        "category": "Credit Risk & Delinquency",
        "question": "How many defaulted loans are in the database?",
        "gold_sql": "SELECT COUNT(*) as defaulted_loans, ROUND(SUM(loan_amount), 2) as total_default_amount FROM loans WHERE is_default = 1"
    },
    {
        "id": "RSK-02",
        "category": "Credit Risk & Delinquency",
        "question": "How many loans have missed payments in the last 2 years?",
        "gold_sql": "SELECT COUNT(*) as delinquent_loans, ROUND(AVG(missed_payments_2yr), 2) as avg_missed FROM loans WHERE missed_payments_2yr > 0"
    },
    {
        "id": "RSK-03",
        "category": "Credit Risk & Delinquency",
        "question": "What is the default rate for borrowers with credit score below 600?",
        "gold_sql": "SELECT COUNT(*) as subprime_loans, ROUND(AVG(l.is_default)*100, 2) as default_rate_pct FROM loans l JOIN customers c ON l.customer_id = c.customer_id WHERE c.credit_score < 600"
    },
    {
        "id": "RSK-04",
        "category": "Credit Risk & Delinquency",
        "question": "What is the default rate for borrowers with debt-to-income ratio above 0.40?",
        "gold_sql": "SELECT COUNT(*) as high_dti_loans, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans WHERE debt_to_income > 0.40"
    },
    {
        "id": "RSK-05",
        "category": "Credit Risk & Delinquency",
        "question": "What is the total principal on loans with 3 or more missed payments?",
        "gold_sql": "SELECT ROUND(SUM(loan_amount), 2) as high_delinquency_principal FROM loans WHERE missed_payments_2yr >= 3"
    },
    {
        "id": "RSK-06",
        "category": "Credit Risk & Delinquency",
        "question": "What is the average interest rate on defaulted loans versus paid off loans?",
        "gold_sql": "SELECT loan_status, ROUND(AVG(interest_rate), 2) as avg_interest_rate FROM loans WHERE loan_status IN ('DEFAULT', 'PAID_OFF') GROUP BY loan_status"
    },
    {
        "id": "RSK-07",
        "category": "Credit Risk & Delinquency",
        "question": "How many auto loans have debt-to-income greater than 0.45?",
        "gold_sql": "SELECT COUNT(*) as auto_high_dti FROM loans WHERE loan_type = 'AUTO' AND debt_to_income > 0.45"
    },
    {
        "id": "RSK-08",
        "category": "Credit Risk & Delinquency",
        "question": "What is the average monthly payment on charged off loans?",
        "gold_sql": "SELECT ROUND(AVG(monthly_payment), 2) as avg_monthly_payment FROM loans WHERE loan_status = 'CHARGED_OFF'"
    },
    {
        "id": "RSK-09",
        "category": "Credit Risk & Delinquency",
        "question": "How many borrowers have both credit score below 580 and missed payments?",
        "gold_sql": "SELECT COUNT(DISTINCT c.customer_id) as count FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE c.credit_score < 580 AND l.missed_payments_2yr > 0"
    },
    {
        "id": "RSK-10",
        "category": "Credit Risk & Delinquency",
        "question": "What is the total default amount for small business loans?",
        "gold_sql": "SELECT ROUND(SUM(loan_amount), 2) as total_sb_default FROM loans WHERE loan_type = 'SMALL_BUSINESS' AND is_default = 1"
    },

    # 5. Fraud & Transaction Analytics (8 queries)
    {
        "id": "FRD-01",
        "category": "Fraud & Transactions",
        "question": "How many transactions were flagged as fraud?",
        "gold_sql": "SELECT COUNT(*) as fraud_tx_count, ROUND(SUM(amount), 2) as total_fraud_amount FROM transactions WHERE is_flagged_fraud = TRUE"
    },
    {
        "id": "FRD-02",
        "category": "Fraud & Transactions",
        "question": "What is the average transaction amount for fraudulent versus legitimate transactions?",
        "gold_sql": "SELECT is_flagged_fraud, COUNT(*) as count, ROUND(AVG(amount), 2) as avg_amount FROM transactions GROUP BY is_flagged_fraud"
    },
    {
        "id": "FRD-03",
        "category": "Fraud & Transactions",
        "question": "Which merchant categories have the highest count of fraud transactions?",
        "gold_sql": "SELECT merchant_category, COUNT(*) as fraud_count FROM transactions WHERE is_flagged_fraud = TRUE GROUP BY merchant_category ORDER BY fraud_count DESC"
    },
    {
        "id": "FRD-04",
        "category": "Fraud & Transactions",
        "question": "How many transactions exceeded $2,500?",
        "gold_sql": "SELECT COUNT(*) as large_transactions, ROUND(SUM(amount), 2) as total_large_volume FROM transactions WHERE amount > 2500"
    },
    {
        "id": "FRD-05",
        "category": "Fraud & Transactions",
        "question": "How many loan payments were processed through transactions?",
        "gold_sql": "SELECT COUNT(*) as payment_count, ROUND(SUM(amount), 2) as total_payment_amount FROM transactions WHERE transaction_type = 'LOAN_PAYMENT'"
    },
    {
        "id": "FRD-06",
        "category": "Fraud & Transactions",
        "question": "What is the total grocery spend across all transactions?",
        "gold_sql": "SELECT ROUND(SUM(amount), 2) as total_grocery_spend FROM transactions WHERE merchant_category = 'GROCERY'"
    },
    {
        "id": "FRD-07",
        "category": "Fraud & Transactions",
        "question": "What is the maximum transaction amount recorded?",
        "gold_sql": "SELECT MAX(amount) as max_transaction_amount FROM transactions"
    },
    {
        "id": "FRD-08",
        "category": "Fraud & Transactions",
        "question": "How many transactions were executed on frozen accounts?",
        "gold_sql": "SELECT COUNT(t.transaction_id) as count FROM transactions t JOIN accounts a ON t.account_id = a.account_id WHERE a.status = 'FROZEN'"
    },

    # 6. Complex Analytics, Rankings & Filters (8 queries)
    {
        "id": "CMP-01",
        "category": "Complex Analytics",
        "question": "What are the top 5 states by total loan volume?",
        "gold_sql": "SELECT c.state, COUNT(l.loan_id) as loan_count, ROUND(SUM(l.loan_amount), 2) as total_volume FROM loans l JOIN customers c ON l.customer_id = c.customer_id GROUP BY c.state ORDER BY total_volume DESC LIMIT 5"
    },
    {
        "id": "CMP-02",
        "category": "Complex Analytics",
        "question": "Find the top 5 customers with the highest total bank account balance.",
        "gold_sql": "SELECT c.customer_id, c.full_name, ROUND(SUM(a.balance), 2) as total_balance FROM customers c JOIN accounts a ON c.customer_id = a.customer_id GROUP BY c.customer_id, c.full_name ORDER BY total_balance DESC LIMIT 5"
    },
    {
        "id": "CMP-03",
        "category": "Complex Analytics",
        "question": "What are the top 3 merchant categories by total expenditure?",
        "gold_sql": "SELECT merchant_category, ROUND(SUM(amount), 2) as total_spend FROM transactions GROUP BY merchant_category ORDER BY total_spend DESC LIMIT 3"
    },
    {
        "id": "CMP-04",
        "category": "Complex Analytics",
        "question": "How many customers have more than 2 bank accounts?",
        "gold_sql": "SELECT COUNT(*) as count FROM (SELECT customer_id FROM accounts GROUP BY customer_id HAVING COUNT(*) > 2) sub"
    },
    {
        "id": "CMP-05",
        "category": "Complex Analytics",
        "question": "What is the average credit score of customers holding more than $50,000 in checking balance?",
        "gold_sql": "SELECT ROUND(AVG(c.credit_score), 1) as avg_score FROM customers c JOIN accounts a ON c.customer_id = a.customer_id WHERE a.account_type = 'CHECKING' AND a.balance > 50000"
    },
    {
        "id": "CMP-06",
        "category": "Complex Analytics",
        "question": "What is the default rate for mortgage loans with terms of 360 months?",
        "gold_sql": "SELECT COUNT(*) as count, ROUND(AVG(is_default)*100, 2) as default_rate_pct FROM loans WHERE loan_type = 'MORTGAGE' AND term_months = 360"
    },
    {
        "id": "CMP-07",
        "category": "Complex Analytics",
        "question": "What is the average annual income of customers who have experienced loan default?",
        "gold_sql": "SELECT ROUND(AVG(c.annual_income), 2) as avg_defaulter_income FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE l.is_default = 1"
    },
    {
        "id": "CMP-08",
        "category": "Complex Analytics",
        "question": "What are the top 5 largest loans currently in default status?",
        "gold_sql": "SELECT loan_id, customer_id, loan_type, loan_amount, interest_rate FROM loans WHERE loan_status = 'DEFAULT' ORDER BY loan_amount DESC LIMIT 5"
    }
]

