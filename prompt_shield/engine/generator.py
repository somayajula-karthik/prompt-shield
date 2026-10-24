"""
Format-valid surrogate generator for Indian personal identifiers.

Generates realistic, format-preserving surrogates that pass strict validation:
- Aadhaar: Valid Verhoeff checksum and UIDAI starting-digit rules.
- PAN: Valid 10-char format, preserving the 4th taxpayer status character.
- UPI: Valid Indian bank/PSP handle format.
- IFSC: Valid RBI 11-char format with 5th char '0'.
- Phone: Valid 10-digit Indian mobile number with matching prefix/delimiters.
"""

import random
import string
from typing import Optional, Set
from prompt_shield.algorithms.verhoeff import generate_valid_aadhaar, clean_digits


class SurrogateGenerator:
    """Generates format-valid, realistic surrogates for Indian identifiers."""

    COMMON_FIRST_NAMES = [
        "arun", "rahul", "priya", "amit", "neha", "vikram", "ananya",
        "suresh", "deepak", "pooja", "rohit", "sneha", "manoj", "kavita",
    ]

    COMMON_LAST_NAMES = [
        "kumar", "sharma", "verma", "singh", "patel", "iyer", "gupta",
        "reddy", "joshi", "rao", "nair", "mehta", "chatterjee", "deshmukh",
    ]

    KNOWN_IFSC_BANKS = [
        "SBIN", "HDFC", "ICIC", "UTIB", "KKBK", "PUNB", "BARB",
        "CNRB", "UBIN", "BKID", "IDFB", "YESB", "INDB",
    ]

    KNOWN_UPI_HANDLES = [
        "okhdfcbank", "oksbi", "okaxis", "okicici", "paytm",
        "ybl", "upi", "ibl", "axl", "barodampay",
    ]

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def generate_aadhaar(self, original_val: str) -> str:
        """
        Generates a synthetic 12-digit Aadhaar number with a valid Verhoeff checksum.
        Preserves formatting (spaces, hyphens, or continuous).
        """
        # Generate 11 random digits (first digit 2..9)
        first_digit = str(self._rng.randint(2, 9))
        middle_digits = "".join(str(self._rng.randint(0, 9)) for _ in range(10))
        base_11 = first_digit + middle_digits

        from prompt_shield.algorithms.verhoeff import compute_verhoeff_checksum
        chk = compute_verhoeff_checksum(base_11)
        full_12 = f"{base_11}{chk}"

        if " " in original_val or "\n" in original_val:
            return f"{full_12[:4]} {full_12[4:8]} {full_12[8:]}"
        elif "-" in original_val:
            return f"{full_12[:4]}-{full_12[4:8]}-{full_12[8:]}"
        elif "." in original_val:
            return f"{full_12[:4]}.{full_12[4:8]}.{full_12[8:]}"
        return full_12

    def generate_pan(self, original_val: str) -> str:
        """
        Generates a synthetic 10-char PAN card.
        Preserves:
        - 4th character (holder type: 'P' for Individual, 'C' for Company, etc.)
        - Casing (uppercase/lowercase)
        """
        norm = "".join(ch for ch in original_val.upper() if ch.isalnum())
        # Preserve status char (index 3), default to 'P' if not present
        status_char = norm[3] if len(norm) > 3 and norm[3] in "PCHFATBLJG" else "P"

        first_3 = "".join(self._rng.choices(string.ascii_uppercase, k=3))
        fifth_char = self._rng.choice(string.ascii_uppercase)
        # Digits 6-9 (0001 to 9999)
        digits_4 = f"{self._rng.randint(1001, 9999):04d}"
        check_char = self._rng.choice(string.ascii_uppercase)

        pan = f"{first_3}{status_char}{fifth_char}{digits_4}{check_char}"

        if original_val.islower():
            return pan.lower()
        return pan

    def generate_upi(self, original_val: str) -> str:
        """
        Generates a synthetic UPI VPA.
        Preserves handle if known, or picks a realistic bank handle.
        """
        parts = original_val.split("@")
        username_part = parts[0] if parts else "user"
        handle_part = parts[1] if len(parts) > 1 else "upi"

        first_name = self._rng.choice(self.COMMON_FIRST_NAMES)
        num_suffix = self._rng.randint(10, 999)
        surrogate_user = f"{first_name}.{num_suffix}"

        # If original handle is a known handle, preserve it; otherwise pick a standard one
        handle_lower = handle_part.lower()
        surrogate_handle = handle_lower if handle_lower in self.KNOWN_UPI_HANDLES else self._rng.choice(self.KNOWN_UPI_HANDLES)

        return f"{surrogate_user}@{surrogate_handle}"

    def generate_ifsc(self, original_val: str) -> str:
        """
        Generates an 11-char IFSC code.
        Preserves bank code prefix if known, keeps 5th char '0', and randomizes branch.
        """
        norm = original_val.strip().upper()
        bank_prefix = norm[:4] if len(norm) >= 4 and norm[:4].isalpha() else self._rng.choice(self.KNOWN_IFSC_BANKS)

        # 6-char branch code (starts with numeric/alphanumeric, e.g. 004819)
        branch_digits = f"{self._rng.randint(1000, 99999):06d}"
        return f"{bank_prefix}0{branch_digits[-6:]}"

    def generate_phone(self, original_val: str) -> str:
        """
        Generates a 10-digit Indian mobile number.
        Preserves prefix (+91, 91, 0) and spacing/hyphen structure.
        """
        # First digit must be 6, 7, 8, or 9
        first_digit = str(self._rng.randint(7, 9))
        remaining_9 = "".join(str(self._rng.randint(0, 9)) for _ in range(9))
        core_10 = first_digit + remaining_9

        # Preserve formatting
        if " " in original_val and ("+91" in original_val or original_val.startswith("91")):
            prefix = "+91 " if "+91" in original_val else "91 "
            return f"{prefix}{core_10[:5]} {core_10[5:]}"
        elif "-" in original_val and "+91" in original_val:
            return f"+91-{core_10[:5]}-{core_10[5:]}"
        elif original_val.startswith("+91"):
            return f"+91{core_10}"
        elif original_val.startswith("0") and " " in original_val:
            return f"0{core_10[:5]} {core_10[5:]}"
        elif original_val.startswith("0"):
            return f"0{core_10}"
        elif " " in original_val:
            return f"{core_10[:5]} {core_10[5:]}"
        elif "-" in original_val:
            return f"{core_10[:5]}-{core_10[5:]}"
        return core_10

    def generate_surrogate(
        self,
        entity_type: str,
        original_val: str,
        existing_surrogates: Optional[Set[str]] = None,
        max_attempts: int = 50,
    ) -> str:
        """
        Generate a unique, format-valid surrogate for the given entity type.
        Ensures the generated surrogate does not match the original or any existing surrogate.
        """
        existing = existing_surrogates or set()

        for _ in range(max_attempts):
            if entity_type == "AADHAAR":
                surrogate = self.generate_aadhaar(original_val)
            elif entity_type == "PAN":
                surrogate = self.generate_pan(original_val)
            elif entity_type == "UPI":
                surrogate = self.generate_upi(original_val)
            elif entity_type == "IFSC":
                surrogate = self.generate_ifsc(original_val)
            elif entity_type == "PHONE":
                surrogate = self.generate_phone(original_val)
            else:
                # Fallback for generic identifiers
                surrogate = f"SURROGATE_{self._rng.randint(10000, 99999)}"

            if surrogate != original_val and surrogate not in existing:
                return surrogate

        # If max attempts reached, return with unique suffix
        return f"{surrogate}_{self._rng.randint(100, 999)}"
