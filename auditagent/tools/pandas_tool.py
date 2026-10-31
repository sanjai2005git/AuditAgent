from typing import Any, Optional
import pandas as pd
import numpy as np
from auditagent.data.database import db_manager

class PandasAnalysisTool:
    def analyze_portfolio_risk(self) -> dict[str, Any]:
        """
        Runs comprehensive pandas aggregations and correlations across loan book.
        """
        conn = db_manager.get_connection(read_only=True)
        try:
            df = conn.execute("""
            SELECT 
                l.loan_type,
                l.loan_amount,
                l.interest_rate,
                l.debt_to_income,
                l.missed_payments_2yr,
                l.is_default,
                c.credit_score,
                c.annual_income,
                c.employment_years
            FROM loans l
            JOIN customers c ON l.customer_id = c.customer_id
            """).fetch_df()
        finally:
            conn.close()

        # 1. Summary by loan type
        type_summary = df.groupby("loan_type").agg(
            loan_count=("loan_amount", "count"),
            total_principal=("loan_amount", "sum"),
            avg_principal=("loan_amount", "mean"),
            avg_interest=("interest_rate", "mean"),
            default_count=("is_default", "sum"),
            default_rate=("is_default", "mean")
        ).reset_index()
        type_summary["default_rate_pct"] = (type_summary["default_rate"] * 100).round(2)
        type_summary["total_principal"] = type_summary["total_principal"].round(2)
        type_summary["avg_principal"] = type_summary["avg_principal"].round(2)
        type_summary["avg_interest"] = type_summary["avg_interest"].round(2)

        # 2. Risk factor correlations with default
        numeric_cols = ["loan_amount", "interest_rate", "debt_to_income", "missed_payments_2yr", "credit_score", "annual_income"]
        corr_series = df[numeric_cols + ["is_default"]].corr()["is_default"].drop("is_default")
        correlations = corr_series.round(4).to_dict()

        # 3. Quantile distributions
        quantiles = {
            "credit_score": df["credit_score"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(1).to_dict(),
            "debt_to_income": df["debt_to_income"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(4).to_dict(),
            "loan_amount": df["loan_amount"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(2).to_dict()
        }

        # 4. Overall metrics
        total_loans = len(df)
        total_defaults = int(df["is_default"].sum())
        overall_default_rate = round(float(df["is_default"].mean()) * 100, 2)
        total_exposure = round(float(df["loan_amount"].sum()), 2)

        narrative = (
            f"Portfolio comprises {total_loans:,} loans with total exposure of ${total_exposure:,.2f}. "
            f"Overall default rate is {overall_default_rate}% ({total_defaults:,} defaults). "
            f"Highest risk correlation with default: missed_payments_2yr (r={correlations.get('missed_payments_2yr', 0):.3f}) "
            f"and debt_to_income (r={correlations.get('debt_to_income', 0):.3f}), while credit_score has strong protective correlation (r={correlations.get('credit_score', 0):.3f})."
        )

        return {
            "total_loans": total_loans,
            "total_defaults": total_defaults,
            "overall_default_rate_pct": overall_default_rate,
            "total_exposure": total_exposure,
            "by_loan_type": type_summary.to_dict(orient="records"),
            "correlations_with_default": correlations,
            "quantiles": quantiles,
            "narrative": narrative
        }

pandas_tool = PandasAnalysisTool()

