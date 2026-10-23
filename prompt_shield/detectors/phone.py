"""
Indian Mobile Phone Number detector.
"""

import re
from typing import List
from prompt_shield.detectors.base import BaseDetector, Match
from prompt_shield.algorithms.verhoeff import clean_digits


class PhoneDetector(BaseDetector):
    """
    Detects Indian mobile phone numbers in text.
    
    Structure:
    - 10 decimal digits starting with 6, 7, 8, or 9 (National Numbering Plan).
    - Optional prefixes: '+91', '91', or '0' (trunk code).
    - Common separators: spaces or hyphens (e.g. +91 98765 43210, 98765-43210).
    - Excludes numbers embedded inside longer digit sequences (e.g. 12-digit Aadhaar or 16-digit accounts).
    - Uses local context window to suppress bare 10-digit non-phone numbers (Order IDs, account numbers, currency amounts).
    """

    PHONE_PATTERN = re.compile(
        r"(?<![A-Za-z0-9+])(?:\+91[\s.-]?|(?<!\d)91[\s.-]|(?<!\d)0[\s.-]?)?"
        r"([6-9]\d{4}[\s.-]?\d{5}|[6-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{4}|[6-9]\d{9})"
        r"(?!\d)"
    )

    NEGATIVE_CONTEXT_PATTERN = re.compile(
        r"\b(?:order(?:\s+id|\s+no|\s*#)?|account(?:\s+number|\s+no)?|a/c|invoice(?:\s+total|\s+no)?|"
        r"rs\.?|inr|utr|txn|transaction|ledger|amount| serial)\b",
        re.IGNORECASE,
    )

    POSITIVE_CONTEXT_PATTERN = re.compile(
        r"\b(?:phone|mobile|cell|contact|call|whatsapp|sms|otp|callback|reach|dial|number\s+is)\b",
        re.IGNORECASE,
    )

    @property
    def entity_type(self) -> str:
        return "PHONE"

    def validate_phone(self, raw_val: str) -> bool:
        """
        Validates that extracted candidate resolves to a valid 10-digit Indian mobile number.
        """
        digits = clean_digits(raw_val)

        # Strip country / trunk prefix
        if raw_val.strip().startswith("+91") or (digits.startswith("91") and len(digits) == 12):
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        # Must be exactly 10 digits starting with 6, 7, 8, or 9
        if len(digits) != 10:
            return False

        if digits[0] not in ("6", "7", "8", "9"):
            return False

        # Reject all identical digits (e.g. 9999999999)
        if len(set(digits)) == 1:
            return False

        return True

    def _has_disqualifying_context(self, text: str, start: int, end: int, raw_val: str) -> bool:
        """
        Checks if a bare 10-digit number (without +91, leading 0, or spacing) is immediately
        preceded by non-phone context keywords (Order ID, Account number, Rs/INR amount)
        without any phone-related cue. Furthermore, skips numbers that form the username
        of a UPI VPA (i.e. immediately followed by '@').
        """
        # If immediately followed by '@', let UPIDetector claim the full VPA
        if end < len(text) and text[end] == "@":
            return True

        has_explicit_phone_format = (
            "+91" in raw_val
            or raw_val.startswith("91 ")
            or raw_val.startswith("0")
            or " " in raw_val
            or "-" in raw_val
        )
        if has_explicit_phone_format:
            return False

        window_start = max(0, start - 40)
        preceding = text[window_start:start]

        if self.NEGATIVE_CONTEXT_PATTERN.search(preceding) and not self.POSITIVE_CONTEXT_PATTERN.search(preceding):
            return True

        return False

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for match in self.PHONE_PATTERN.finditer(text):
            raw_val = match.group(0).strip()

            if not self.validate_phone(raw_val):
                continue

            if self._has_disqualifying_context(text, match.start(), match.end(), raw_val):
                continue

            digits = clean_digits(raw_val)
            if len(digits) == 12 and digits.startswith("91"):
                core_10 = digits[2:]
            elif len(digits) == 11 and digits.startswith("0"):
                core_10 = digits[1:]
            else:
                core_10 = digits

            has_country_code = "+91" in raw_val or raw_val.startswith("91 ")
            matches.append(
                Match(
                    entity_type=self.entity_type,
                    start=match.start(),
                    end=match.end(),
                    value=raw_val,
                    confidence=1.0 if has_country_code else 0.90,
                    metadata={
                        "normalized_10": core_10,
                        "has_country_code": has_country_code,
                        "formatted": " " in raw_val or "-" in raw_val,
                    },
                )
            )

        return matches
