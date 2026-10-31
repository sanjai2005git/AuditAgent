"""
Single setup script to initialize the DuckDB database, seed realistic lending and transactional data,
and train the XGBoost credit risk model with SHAP background data.
"""
from auditagent.data.seed_data import seed_database
from auditagent.ml.train_model import train_and_save_model
from auditagent.benchmarks.runner import run_all_benchmarks

def main():
    print("=== Step 1: Seeding Enterprise DuckDB Data Lake ===")
    seed_database()

    print("\n=== Step 2: Training XGBoost Credit Risk Model & SHAP Explainer ===")
    train_and_save_model()

    print("\n=== Step 3: Running Enterprise Benchmarks ===")
    run_all_benchmarks()

    print("\n Setup completed successfully! You can now start FastAPI or Streamlit UI.")

if __name__ == "__main__":
    main()
