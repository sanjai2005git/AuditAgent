import re
from typing import Any
import pandas as pd
from auditagent.core.config import settings

# Comprehensive regex patterns for PII
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

class PIIMasker:
    def __init__(self):
        self.sensitive_column_names = {
            "ssn": "SSN",
            "email": "EMAIL",
            "phone": "PHONE",
            "full_name": "NAME",
            "name": "NAME"
        }

    def mask_text(self, text: str) -> tuple[str, dict[str, int]]:
        """
        Masks PII patterns in text prompts or output descriptions.
        Returns: (sanitized_text, counts_dict)
        """
        if not text:
            return "", {}

        counts = {"ssn": 0, "email": 0, "phone": 0, "card": 0}
        sanitized = text

        # 1. Mask SSN
        ssns = SSN_PATTERN.findall(sanitized)
        if ssns:
            counts["ssn"] += len(ssns)
            sanitized = SSN_PATTERN.sub("[MASKED_SSN]", sanitized)

        # 2. Mask Credit Cards
        cards = CARD_PATTERN.findall(sanitized)
        if cards:
            counts["card"] += len(cards)
            sanitized = CARD_PATTERN.sub("[MASKED_CREDIT_CARD]", sanitized)

        # 3. Mask Emails
        emails = EMAIL_PATTERN.findall(sanitized)
        if emails:
            counts["email"] += len(emails)
            sanitized = EMAIL_PATTERN.sub("[MASKED_EMAIL]", sanitized)

        # 4. Mask Phones
        phones = PHONE_PATTERN.findall(sanitized)
        if phones:
            counts["phone"] += len(phones)
            sanitized = PHONE_PATTERN.sub("[MASKED_PHONE]", sanitized)

        return sanitized, counts

    def mask_dataframe(self, df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """
        Masks PII fields in tabular query results before returning to agent or user.
        """
        if df.empty:
            return df, {}

        df_masked = df.copy()
        counts = {"ssn_cells": 0, "email_cells": 0, "phone_cells": 0, "name_cells": 0}

        for col in df_masked.columns:
            col_lower = str(col).lower()
            
            # Check column name heuristics
            if "ssn" in col_lower:
                counts["ssn_cells"] += len(df_masked)
                df_masked[col] = df_masked[col].astype(str).apply(
                    lambda x: f"***-**-{x[-4:]}" if len(x) >= 4 else "[MASKED_SSN]"
                )
            elif "email" in col_lower:
                counts["email_cells"] += len(df_masked)
                df_masked[col] = df_masked[col].astype(str).apply(
                    lambda x: (x.split("@")[0][0] + "***@" + x.split("@")[1]) if "@" in x else "[MASKED_EMAIL]"
                )
            elif "phone" in col_lower:
                counts["phone_cells"] += len(df_masked)
                df_masked[col] = df_masked[col].astype(str).apply(
                    lambda x: f"***-***-{x[-4:]}" if len(x) >= 4 else "[MASKED_PHONE]"
                )
            elif "full_name" in col_lower or col_lower == "name":
                counts["name_cells"] += len(df_masked)
                df_masked[col] = df_masked[col].astype(str).apply(
                    lambda x: self._mask_name(x)
                )
            elif df_masked[col].dtype == object:
                # Value-level pattern scan for text columns
                df_masked[col] = df_masked[col].astype(str).apply(
                    lambda x: self._mask_cell_value(x)
                )

        return df_masked, counts

    def _mask_name(self, name: str) -> str:
        parts = name.strip().split()
        if not parts:
            return "[MASKED_NAME]"
        masked_parts = [f"{p[0]}***" if len(p) > 1 else p for p in parts]
        return " ".join(masked_parts)

    def _mask_cell_value(self, val: str) -> str:
        if not val or val in ("None", "nan"):
            return val
        if SSN_PATTERN.search(val):
            val = SSN_PATTERN.sub("[MASKED_SSN]", val)
        if EMAIL_PATTERN.search(val):
            val = EMAIL_PATTERN.sub("[MASKED_EMAIL]", val)
        return val

pii_masker = PIIMasker()

