-- AuditAgent Enterprise Schema (DuckDB)

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    full_name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    phone VARCHAR NOT NULL,
    ssn VARCHAR NOT NULL,
    age INTEGER NOT NULL,
    state VARCHAR(2) NOT NULL,
    annual_income DOUBLE NOT NULL,
    employment_years INTEGER NOT NULL,
    credit_score INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    account_type VARCHAR NOT NULL,
    balance DOUBLE NOT NULL,
    status VARCHAR NOT NULL,
    opened_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id VARCHAR PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    loan_type VARCHAR NOT NULL,
    loan_amount DOUBLE NOT NULL,
    interest_rate DOUBLE NOT NULL,
    term_months INTEGER NOT NULL,
    monthly_payment DOUBLE NOT NULL,
    debt_to_income DOUBLE NOT NULL,
    open_credit_lines INTEGER NOT NULL,
    missed_payments_2yr INTEGER NOT NULL,
    loan_status VARCHAR NOT NULL,
    is_default INTEGER NOT NULL,
    issue_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR PRIMARY KEY,
    account_id VARCHAR NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    amount DOUBLE NOT NULL,
    transaction_type VARCHAR NOT NULL,
    merchant_category VARCHAR NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    is_flagged_fraud BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS approval_requests (
    request_id VARCHAR PRIMARY KEY,
    trace_id VARCHAR NOT NULL,
    action_type VARCHAR NOT NULL,
    details VARCHAR NOT NULL,
    requested_by VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR,
    reviewed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_trails (
    trace_id VARCHAR PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_query VARCHAR NOT NULL,
    sanitized_query VARCHAR NOT NULL,
    intent VARCHAR NOT NULL,
    tool_called VARCHAR,
    generated_sql VARCHAR,
    executed_sql VARCHAR,
    row_count INTEGER DEFAULT 0,
    cost_units INTEGER DEFAULT 0,
    ml_prediction DOUBLE,
    shap_top_features VARCHAR,
    guardrail_flags VARCHAR,
    verification_status VARCHAR,
    verification_discrepancy DOUBLE DEFAULT 0.0,
    agent_response VARCHAR,
    execution_latency_ms DOUBLE,
    replayable_state_json VARCHAR
);

