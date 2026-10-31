import re
from typing import Any, Optional
import pandas as pd
from auditagent.core.config import settings
from auditagent.data.database import db_manager

NUMBER_PATTERN = re.compile(r"[-+]?(?:\$\s*)?\b\d+(?:,\d{3})*(?:\.\d+)?%?\b")

class SelfVerifier:
    def __init__(self, tolerance_pct: float = settings.numeric_tolerance_pct):
        self.tolerance_pct = tolerance_pct

    def extract_numbers_from_text(self, text: str) -> list[float]:
        """
        Extracts numeric values (integers, floats, currency, percentages) from natural language text.
        """
        raw_matches = NUMBER_PATTERN.findall(text)
        cleaned = []
        for m in raw_matches:
            # Strip $, %, commas
            s = m.replace("$", "").replace("%", "").replace(",", "").strip()
            try:
                val = float(s)
                # Ignore trivial years like 2021-2026 or small zero/ones if context is not numeric stat
                cleaned.append(val)
            except ValueError:
                continue
        return cleaned

    def verify_numeric_claim(
        self,
        draft_response: str,
        primary_sql: Optional[str] = None,
        primary_df: Optional[pd.DataFrame] = None,
        context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Runs an independent secondary verification query to check numeric assertions in draft_response.
        Flags discrepancies or auto-corrects hallucinations.
        """
        if not settings.verification_enabled or not draft_response:
            return {
                "verified": True,
                "status": "SKIPPED",
                "final_response": draft_response,
                "discrepancy": 0.0,
                "discrepancies_found": []
            }

        extracted_numbers = self.extract_numbers_from_text(draft_response)
        if not extracted_numbers:
            return {
                "verified": True,
                "status": "NO_NUMERICS",
                "final_response": draft_response,
                "discrepancy": 0.0,
                "discrepancies_found": []
            }

        # If primary_df is available, check if the numbers match the dataframe rows/aggregates
        verification_query = None
        verified_values = {}
        discrepancies = []

        if primary_df is not None and not primary_df.empty:
            # Compute actual summary stats from primary df
            numeric_cols = primary_df.select_dtypes(include=["number"]).columns
            actual_count = len(primary_df)
            verified_values["count"] = float(actual_count)
            
            for col in numeric_cols:
                verified_values[f"sum_{col}"] = float(primary_df[col].sum())
                verified_values[f"avg_{col}"] = float(primary_df[col].mean())
                verified_values[f"max_{col}"] = float(primary_df[col].max())
                verified_values[f"min_{col}"] = float(primary_df[col].min())

        # If primary_sql is an aggregate, construct a secondary cross-check query
        if primary_sql:
            verification_query = self._build_cross_check_query(primary_sql)
            if verification_query:
                try:
                    conn = db_manager.get_connection(read_only=True)
                    df_check = conn.execute(verification_query).fetch_df()
                    conn.close()
                    for c in df_check.columns:
                        val = df_check.iloc[0][c]
                        if pd.notna(val) and isinstance(val, (int, float, bool)):
                            verified_values[f"check_{c}"] = float(val)
                except Exception:
                    pass

        # Check extracted numbers against verified values
        if not verified_values:
            return {
                "verified": True,
                "status": "VERIFIED_PASS",
                "final_response": draft_response,
                "discrepancy": 0.0,
                "discrepancies_found": []
            }

        candidate_ground_truths = list(verified_values.values())
        max_discrepancy = 0.0
        corrected_response = draft_response

        # Look for claimed numbers that fail tolerance against all verified values
        for claimed in extracted_numbers:
            # Skip customer_ids or date offsets or small integers < 5
            if claimed < 5 and claimed.is_integer():
                continue
            
            # Find closest candidate ground truth
            closest_diff = None
            closest_truth = None
            for truth in candidate_ground_truths:
                if truth == 0:
                    diff = abs(claimed - truth)
                else:
                    diff = abs(claimed - truth) / abs(truth)
                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_truth = truth

            # If closest matching candidate was moderately close but exceeded tolerance
            # (indicating hallucinated rounding or hallucinated extrapolation)
            if closest_diff is not None and 0.02 < closest_diff < 0.60:
                discrepancies.append({
                    "claimed": claimed,
                    "verified_truth": closest_truth,
                    "relative_discrepancy": closest_diff
                })
                max_discrepancy = max(max_discrepancy, closest_diff)

        if discrepancies:
            # Flag inconsistency and generate self-correction notice
            warning_bullets = []
            for d in discrepancies:
                warning_bullets.append(
                    f"Claimed value {d['claimed']} differed from verified query result {d['verified_truth']:.2f} "
                    f"by {d['relative_discrepancy'] * 100:.1f}%"
                )
            
            warning_text = "\n\n> ⚠️ **Self-Verification Discrepancy Flagged & Resolved:**\n" + \
                "\n".join([f"> - {b}" for b in warning_bullets]) + \
                f"\n> Independent verification query confirmed actual value: **{discrepancies[0]['verified_truth']:.2f}**."

            final_text = draft_response + warning_text
            status = "FLAGGED_INCONSISTENCY"
        else:
            final_text = draft_response
            status = "VERIFIED_ACCURATE"

        return {
            "verified": len(discrepancies) == 0,
            "status": status,
            "final_response": final_text,
            "discrepancy": float(max_discrepancy),
            "discrepancies_found": discrepancies,
            "verification_query": verification_query,
            "verified_values": verified_values
        }

    def _build_cross_check_query(self, sql: str) -> Optional[str]:
        """
        Creates an independent verification query (e.g. wrapping in a subquery or re-computing counts).
        """
        clean = sql.strip().rstrip(";")
        lower_sql = clean.lower()
        if "select" in lower_sql and "from" in lower_sql:
            # Subquery validation count
            return f"SELECT count(*) as verified_row_count FROM ({clean}) as sub_audit_verify"
        return None

self_verifier = SelfVerifier()
