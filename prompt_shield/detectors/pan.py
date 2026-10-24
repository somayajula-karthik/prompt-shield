"""
PAN (Permanent Account Number) detector with structural validation.
"""

import re
from typing import List, Set
from prompt_shield.detectors.base import BaseDetector, Match


class PANDetector(BaseDetector):
    """
    Detects Indian Permanent Account Numbers (PAN) in text.
    
    Structure:
    - Exactly 10 alphanumeric characters: [A-Z]{5}[0-9]{4}[A-Z]
    - 4th character indicates taxpayer status:
      'P' (Individual), 'C' (Company), 'H' (HUF), 'F' (Firm),
      'A' (AOP), 'T' (Trust), 'B' (BOI), 'L' (Local Authority),
      'J' (Artificial Juridical Person), 'G' (Government)
    - Digits 6-9 range between 0001 and 9999 (0000 is invalid)
    """

    # Boundaries ensure PAN is not a substring of a longer alphanumeric hash or code.
    # Supports contiguous 10-char PANs, block-separated PANs (BZRPK 4321 A), and OCR char-spaced PANs.
    PAN_PATTERN = re.compile(
        r"(?<![A-Za-z0-9])("
        r"[A-Za-z]{5}[ -]?[0-9]{4}[ -]?[A-Za-z]"
        r"|(?:[A-Za-z][ ]){4}[A-Za-z][ ](?:[0-9][ ]){3}[0-9][ ][A-Za-z]"
        r")(?![A-Za-z0-9])"
    )

    VALID_STATUS_CHARS: Set[str] = {
        "P", "C", "H", "F", "A", "T", "B", "L", "J", "G"
    }

    @property
    def entity_type(self) -> str:
        return "PAN"

    def validate_pan(self, pan_candidate: str) -> bool:
        """
        Validates structural rules of an Indian PAN card.
        """
        normalized = re.sub(r"[\s-]+", "", pan_candidate).upper()
        if len(normalized) != 10:
            return False

        # Status character check (4th character, index 3)
        status_char = normalized[3]
        if status_char not in self.VALID_STATUS_CHARS:
            return False

        # Numeric block check (chars 5-8, index 5 to 9)
        num_block = normalized[5:9]
        if not num_block.isdigit() or num_block == "0000":
            return False

        return True

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for match in self.PAN_PATTERN.finditer(text):
            raw_val = match.group(1)
            normalized = re.sub(r"[\s-]+", "", raw_val).upper()

            if self.validate_pan(normalized):
                status_code = normalized[3]
                matches.append(
                    Match(
                        entity_type=self.entity_type,
                        start=match.start(1),
                        end=match.end(1),
                        value=raw_val,
                        confidence=1.0,
                        metadata={
                            "normalized": normalized,
                            "holder_type": status_code,
                            "is_individual": status_code == "P",
                        },
                    )
                )

        return matches
