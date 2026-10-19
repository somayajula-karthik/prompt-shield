"""
Aadhaar detector with Verhoeff checksum validation.
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
    """

    # Matches formatted (XXXX XXXX XXXX or XXXX-XXXX-XXXX) or unformatted (XXXXXXXXXXXX)
    AADHAAR_PATTERN = re.compile(
        r"(?<!\d)([2-9]\d{3}[ -]\d{4}[ -]\d{4}|[2-9]\d{11})(?!\d)"
    )

    @property
    def entity_type(self) -> str:
        return "AADHAAR"

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for match in self.AADHAAR_PATTERN.finditer(text):
            raw_val = match.group(0)
            cleaned = clean_digits(raw_val)

            # Strict Verhoeff and UIDAI rules validation
            if validate_aadhaar(cleaned):
                matches.append(
                    Match(
                        entity_type=self.entity_type,
                        start=match.start(),
                        end=match.end(),
                        value=raw_val,
                        confidence=1.0,
                        metadata={
                            "cleaned": cleaned,
                            "formatted": " " in raw_val or "-" in raw_val,
                            "checksum_verified": True,
                        },
                    )
                )

        return matches
