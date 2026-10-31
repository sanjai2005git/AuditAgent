import pytest
import pandas as pd
from auditagent.verification.self_verifier import self_verifier

def test_extract_numbers():
    text = "We identified 350 defaulted loans totaling $4,250,000 with average interest rate of 14.5%."
    nums = self_verifier.extract_numbers_from_text(text)
    assert 350.0 in nums
    assert 4250000.0 in nums
    assert 14.5 in nums

def test_verification_accurate_match():
    # Pass matching dataframe
    df = pd.DataFrame([{"count": 100, "total": 5000.0}])
    draft = "Calculated metrics: count is 100 with total of $5,000."
    res = self_verifier.verify_numeric_claim(draft, primary_df=df)
    assert res["verified"] is True
    assert res["status"] == "VERIFIED_ACCURATE"
    assert len(res["discrepancies_found"]) == 0

def test_verification_flags_hallucination():
    df = pd.DataFrame([{"count": 100, "total": 5000.0}])
    # Claim 135 instead of 100 (a 35% hallucination)
    draft = "Calculated metrics: count is 135 with total of $5,000."
    res = self_verifier.verify_numeric_claim(draft, primary_df=df)
    assert res["status"] == "FLAGGED_INCONSISTENCY"
    assert len(res["discrepancies_found"]) > 0
    assert "Self-Verification Discrepancy Flagged" in res["final_response"]
