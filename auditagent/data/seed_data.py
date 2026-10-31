import random
import datetime
import numpy as np
import pandas as pd
from auditagent.data.database import db_manager

# Set deterministic seeds
random.seed(42)
np.random.seed(42)

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
               "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
               "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
               "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"]

STATES = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI", "WA", "AZ", "MA", "VA", "CO"]

MERCHANTS = {
    "GROCERY": ["Kroger", "Whole Foods", "Trader Joe's", "Safeway", "HEB"],
    "MORTGAGE": ["Wells Fargo Home", "Quicken Loans", "Chase Mortgage", "Rocket Mortgage"],
    "UTILITIES": ["Duke Energy", "Con Edison", "PG&E", "AT&T Telecom"],
    "RETAIL": ["Amazon.com", "Walmart", "Target", "Costco", "Best Buy"],
    "ENTERTAINMENT": ["Netflix", "Spotify", "AMC Theatres", "Disney Plus"],
    "TRAVEL": ["Delta Air", "United Airlines", "Marriott Hotels", "Airbnb", "Uber"]
}

def generate_ssn():
    return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

def generate_phone():
    return f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"

def seed_database(num_customers: int = 1000, num_loans: int = 1500, num_transactions: int = 5000):
    conn = db_manager.get_connection(read_only=False)
    
    # Check if data already exists
    existing = conn.execute("SELECT count(*) FROM customers").fetchone()[0]
    if existing >= num_customers:
        print(f"Database already populated with {existing} customers. Skipping seed.")
        conn.close()
        return

    print(f"Seeding database with {num_customers} customers, {num_loans} loans, {num_transactions} transactions...")
    
    # 1. Customers
    customers = []
    base_date = datetime.date(2021, 1, 1)
    
    for i in range(1, num_customers + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i % 99}@example.com"
        phone = generate_phone()
        ssn = generate_ssn()
        age = int(np.clip(np.random.normal(42, 13), 21, 75))
        state = random.choice(STATES)
        
        # Log-normal distribution for income
        annual_income = round(float(np.exp(np.random.normal(11.0, 0.55))), 2)
        annual_income = float(np.clip(annual_income, 24000.0, 350000.0))
        
        # Employment years correlated with age
        max_emp = max(1, age - 20)
        employment_years = int(np.clip(random.randint(0, max_emp), 0, 35))
        
        # Credit score (300 - 850)
        credit_score = int(np.clip(np.random.normal(680, 75), 380, 850))
        
        days_offset = random.randint(0, 1000)
        created_at = base_date + datetime.timedelta(days=days_offset)
        
        customers.append((i, full_name, email, phone, ssn, age, state, annual_income, employment_years, credit_score, created_at))
    
    customers_df = pd.DataFrame(customers, columns=[
        "customer_id", "full_name", "email", "phone", "ssn", "age",
        "state", "annual_income", "employment_years", "credit_score", "created_at"
    ])
    
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM loans")
    conn.execute("DELETE FROM accounts")
    conn.execute("DELETE FROM customers")
    
    conn.register("df_customers", customers_df)
    conn.execute("INSERT INTO customers SELECT * FROM df_customers")
    conn.unregister("df_customers")
    
    # 2. Accounts
    accounts = []
    account_types = ["CHECKING", "SAVINGS", "MONEY_MARKET"]
    acct_id_counter = 100000
    
    for cust in customers:
        cust_id = cust[0]
        # 1-3 accounts per customer
        for _ in range(random.choice([1, 1, 2, 3])):
            acct_id_counter += 1
            acct_id = f"ACC-{acct_id_counter}"
            acct_type = random.choice(account_types)
            balance = round(random.uniform(500.0, 65000.0), 2)
            status = random.choices(["ACTIVE", "DORMANT", "FROZEN"], weights=[0.92, 0.06, 0.02])[0]
            opened = cust[10] + datetime.timedelta(days=random.randint(1, 100))
            accounts.append((acct_id, cust_id, acct_type, balance, status, opened))
            
    accounts_df = pd.DataFrame(accounts, columns=["account_id", "customer_id", "account_type", "balance", "status", "opened_date"])
    conn.register("df_accounts", accounts_df)
    conn.execute("INSERT INTO accounts SELECT * FROM df_accounts")
    conn.unregister("df_accounts")
    
    # 3. Loans
    loans = []
    loan_types = ["PERSONAL", "MORTGAGE", "AUTO", "SMALL_BUSINESS"]
    loan_id_counter = 50000
    
    for _ in range(num_loans):
        loan_id_counter += 1
        loan_id = f"LN-{loan_id_counter}"
        cust = random.choice(customers)
        cust_id = cust[0]
        cust_income = cust[7]
        cust_score = cust[9]
        
        loan_type = random.choice(loan_types)
        if loan_type == "MORTGAGE":
            loan_amount = round(random.uniform(150000, 650000), 2)
            term_months = random.choice([180, 360])
            interest_rate = round(random.uniform(5.5, 8.5), 2)
        elif loan_type == "AUTO":
            loan_amount = round(random.uniform(15000, 60000), 2)
            term_months = random.choice([36, 48, 60, 72])
            interest_rate = round(random.uniform(4.5, 12.0), 2)
        elif loan_type == "SMALL_BUSINESS":
            loan_amount = round(random.uniform(50000, 250000), 2)
            term_months = random.choice([36, 60, 120])
            interest_rate = round(random.uniform(7.0, 14.5), 2)
        else: # PERSONAL
            loan_amount = round(random.uniform(3000, 40000), 2)
            term_months = random.choice([12, 24, 36, 60])
            interest_rate = round(random.uniform(8.0, 22.0), 2)
            
        # Monthly payment estimation
        monthly_payment = round((loan_amount / term_months) * (1 + (interest_rate / 100)), 2)
        
        # Debt to income ratio (0.10 - 0.65)
        dti = round(float(np.clip(np.random.normal(0.32, 0.12), 0.08, 0.68)), 4)
        
        open_lines = random.randint(1, 15)
        
        # Missed payments correlated inversely with credit score
        if cust_score < 580:
            missed = random.choice([2, 3, 4, 5])
        elif cust_score < 670:
            missed = random.choice([0, 1, 2, 3])
        elif cust_score < 740:
            missed = random.choice([0, 0, 1])
        else:
            missed = 0
            
        # Ground truth default calculation (Logit probability)
        # Latent risk score
        z = (
            -2.8
            + 4.2 * dti
            + 0.65 * missed
            - 0.007 * (cust_score - 600)
            - 0.000008 * (cust_income - 60000)
            + 0.12 * (interest_rate - 8.0)
        )
        prob_default = 1.0 / (1.0 + np.exp(-z))
        is_default = 1 if (random.random() < prob_default) else 0
        
        if is_default:
            loan_status = random.choice(["DEFAULT", "CHARGED_OFF"])
        else:
            loan_status = random.choices(["CURRENT", "PAID_OFF"], weights=[0.75, 0.25])[0]
            
        issue_date = base_date + datetime.timedelta(days=random.randint(100, 1100))
        
        loans.append((
            loan_id, cust_id, loan_type, loan_amount, interest_rate, term_months,
            monthly_payment, dti, open_lines, missed, loan_status, is_default, issue_date
        ))
        
    loans_df = pd.DataFrame(loans, columns=[
        "loan_id", "customer_id", "loan_type", "loan_amount", "interest_rate", "term_months",
        "monthly_payment", "debt_to_income", "open_credit_lines", "missed_payments_2yr",
        "loan_status", "is_default", "issue_date"
    ])
    conn.register("df_loans", loans_df)
    conn.execute("INSERT INTO loans SELECT * FROM df_loans")
    conn.unregister("df_loans")
    
    # 4. Transactions
    transactions = []
    tx_id_counter = 700000
    
    for _ in range(num_transactions):
        tx_id_counter += 1
        tx_id = f"TX-{tx_id_counter}"
        acct = random.choice(accounts)
        acct_id = acct[0]
        cust_id = acct[1]
        
        category = random.choice(list(MERCHANTS.keys()))
        amount = round(float(np.clip(np.random.exponential(120), 5.0, 5000.0)), 2)
        if category == "MORTGAGE":
            amount = round(random.uniform(1200, 3800), 2)
            tx_type = "LOAN_PAYMENT"
        elif category in ["GROCERY", "RETAIL", "ENTERTAINMENT"]:
            tx_type = random.choice(["WITHDRAWAL", "WITHDRAWAL", "DEPOSIT"])
        else:
            tx_type = random.choice(["WITHDRAWAL", "TRANSFER"])
            
        # Small fraud chance
        is_fraud = True if (amount > 2500 and random.random() < 0.08) else False
        
        days_offset = random.randint(1, 700)
        tx_date = datetime.datetime.combine(base_date + datetime.timedelta(days=days_offset),
                                           datetime.time(random.randint(6, 23), random.randint(0, 59)))
        
        transactions.append((tx_id, acct_id, cust_id, amount, tx_type, category, tx_date, is_fraud))
        
    tx_df = pd.DataFrame(transactions, columns=[
        "transaction_id", "account_id", "customer_id", "amount", "transaction_type",
        "merchant_category", "transaction_date", "is_flagged_fraud"
    ])
    conn.register("df_transactions", tx_df)
    conn.execute("INSERT INTO transactions SELECT * FROM df_transactions")
    conn.unregister("df_transactions")
    
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()

