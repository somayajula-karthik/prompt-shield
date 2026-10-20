"""
IFSC (Indian Financial System Code) detector.
"""

import re
from typing import List, Set
from prompt_shield.detectors.base import BaseDetector, Match


class IFSCDetector(BaseDetector):
    """
    Detects Indian Financial System Codes (IFSC) in text.
    
    Structure:
    - 11 alphanumeric characters: ^[A-Z]{4}0[A-Z0-9]{6}$
    - First 4 characters represent the bank (alphabetic).
    - 5th character is always numeric '0' (reserved by RBI for future use).
    - Last 6 characters represent the specific branch (alphanumeric).
    """

    # Boundaries prevent matching within longer alphanumeric hashes or identifiers
    IFSC_PATTERN = re.compile(
        r"(?<![A-Za-z0-9])([A-Za-z]{4}0[A-Za-z0-9]{6})(?![A-Za-z0-9])"
    )

    # Major Indian Bank 4-letter IFSC prefixes
    KNOWN_BANK_PREFIXES: Set[str] = {
        "SBIN", "HDFC", "ICIC", "UTIB", "KKBK", "PUNB", "BARB",
        "CNRB", "UBIN", "BKID", "IOBA", "IDIB", "CBIN", "IDFB",
        "YESB", "INDB", "MAHB", "PSIB", "UCOB", "FDRL", "SIBL",
        "KVBL", "RBLN", "AUBL", "ESFB", "JSFB", "UTKS", "PYTM",
        "AIRP", "IPOS", "SCBL", "HSBC", "CITI", "DBSS",
    }

    @property
    def entity_type(self) -> str:
        return "IFSC"

    def validate_ifsc(self, code: str) -> bool:
        """
        Validates structural syntax of an IFSC candidate.
        """
        normalized = code.upper().strip()
        if len(normalized) != 11:
            return False

        # First 4 must be letters
        if not normalized[:4].isalpha():
            return False

        # 5th character must be '0'
        if normalized[4] != "0":
            return False

        # Last 6 must be alphanumeric
        branch = normalized[5:]
        if not branch.isalnum():
            return False

        # Avoid trivial degenerate strings like '000000' unless paired with known bank
        if branch == "000000" and normalized[:4] not in self.KNOWN_BANK_PREFIXES:
            return False

        return True

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for match in self.IFSC_PATTERN.finditer(text):
            raw_val = match.group(1)
            normalized = raw_val.upper()

            if self.validate_ifsc(normalized):
                bank_prefix = normalized[:4]
                is_known = bank_prefix in self.KNOWN_BANK_PREFIXES
                matches.append(
                    Match(
                        entity_type=self.entity_type,
                        start=match.start(1),
                        end=match.end(1),
                        value=raw_val,
                        confidence=1.0 if is_known else 0.85,
                        metadata={
                            "normalized": normalized,
                            "bank_prefix": bank_prefix,
                            "branch_code": normalized[5:],
                            "is_known_bank": is_known,
                        },
                    )
                )

        return matches
