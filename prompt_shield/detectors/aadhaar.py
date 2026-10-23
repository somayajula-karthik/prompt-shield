"""
Aadhaar detector with Verhoeff checksum validation and context disambiguation.
"""

import re
from typing import List
from prompt_shield.detectors.base import BaseDetector, Match
from prompt_shield.algorithms.verhoeff import validate_aadhaar, clean_digits


class AadhaarDetector(BaseDetector):
    """
    Detects Indian Aadhaar numbers in text.
    
    Candidate numbers must:
    - Match 12 digits in groups of 4 separated by space/hyphen, or 12 continuous digits.
    - Not be part of a longer digit sequence (negative lookahead/lookbehind).
    - Start with a digit between 2 and 9 (UIDAI rule: cannot start with 0 or 1).
    - Pass the Verhoeff checksum algorithm.
    - For unformatted 12-digit numbers, not be immediately preceded by non-Aadhaar
      transaction context (e.g. UTR, NEFT, IMPS, Order/Invoice ref) that happens to
      collide with the 1-in-10 Verhoeff check digit space.
    """

    # Matches formatted (XXXX XXXX XXXX or XXXX-XXXX-XXXX) or unformatted (XXXXXXXXXXXX)
    AADHAAR_PATTERN = re.compile(
        r"(?<!\d)([2-9]\d{3}[ -]\d{4}[ -]\d{4}|[2-9]\d{11})(?!\d)"
    )

    NEGATIVE_CONTEXT_PATTERN = re.compile(
        r"\b(?:utr|neft|rtgs|imps|txn|transaction|reference|ref|order|invoice|account|waybill)\b",
        re.IGNORECASE,
    )

    POSITIVE_CONTEXT_PATTERN = re.compile(
        r"\b(?:aadhaar|aadhar|uidai|uid|kyc|identity)\b",
        re.IGNORECASE,
    )

    @property
    def entity_type(self) -> str:
        return "AADHAAR"

    def _has_disqualifying_context(self, text: str, start: int, raw_val: str) -> bool:
        """
        Because 1 in 10 random 12-digit numbers satisfy the Verhoeff check digit by chance,
        suppress unformatted 12-digit matches when preceded by explicit transaction/UTR labels
        unless an Aadhaar/UID keyword is also present.
        """
        is_formatted = " " in raw_val or "-" in raw_val
        if is_formatted:
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

        for match in self.AADHAAR_PATTERN.finditer(text):
            raw_val = match.group(0)
            cleaned = clean_digits(raw_val)

            # Strict Verhoeff and UIDAI rules validation
            if validate_aadhaar(cleaned):
                if self._has_disqualifying_context(text, match.start(), raw_val):
                    continue

                matches.append(
                    Match(
                        entity_type=self.entity_type,
                        start=match.start(),
                        end=match.end(),
                        value=raw_val,
                        confidence=1.0 if (" " in raw_val or "-" in raw_val) else 0.92,
                        metadata={
                            "cleaned": cleaned,
                            "formatted": " " in raw_val or "-" in raw_val,
                            "checksum_verified": True,
                        },
                    )
                )

        return matches
