"""
Identifier detectors for Prompt Shield.
Covers 5 core Indian personal and financial identifier types:
1. Aadhaar (12 digits, Verhoeff checksum validated)
2. PAN (10 chars, status code validated)
3. UPI VPA (Payment handle validated, emails excluded)
4. IFSC (11 chars, RBI 5th char 0 and bank code validated)
5. Phone (10-digit Indian mobile numbers with optional +91/0 prefix)
"""

from typing import List, Optional
from prompt_shield.detectors.base import BaseDetector, Match
from prompt_shield.detectors.aadhaar import AadhaarDetector
from prompt_shield.detectors.pan import PANDetector
from prompt_shield.detectors.upi import UPIDetector
from prompt_shield.detectors.ifsc import IFSCDetector
from prompt_shield.detectors.phone import PhoneDetector

__all__ = [
    "BaseDetector",
    "Match",
    "AadhaarDetector",
    "PANDetector",
    "UPIDetector",
    "IFSCDetector",
    "PhoneDetector",
    "get_default_detectors",
    "detect_all",
]


def get_default_detectors() -> List[BaseDetector]:
    """Returns instances of all 5 active Indian identifier detectors."""
    return [
        AadhaarDetector(),
        PANDetector(),
        UPIDetector(),
        IFSCDetector(),
        PhoneDetector(),
    ]


def detect_all(text: str, detectors: Optional[List[BaseDetector]] = None) -> List[Match]:
    """
    Run all detectors on input text and return non-overlapping matches sorted by start position.
    If two matches overlap, the longer match is preferred.
    """
    if not text:
        return []

    active_detectors = detectors if detectors is not None else get_default_detectors()
    all_matches: List[Match] = []

    for detector in active_detectors:
        all_matches.extend(detector.detect(text))

    # Sort matches primarily by start ascending, then length descending
    all_matches.sort(key=lambda m: (m.start, -(m.end - m.start)))

    # Filter overlaps (greedy longest-match selection)
    filtered: List[Match] = []
    last_end = -1
    for m in all_matches:
        if m.start >= last_end:
            filtered.append(m)
            last_end = m.end
        else:
            # Overlap detected; current match starts before previous match ended
            continue

    return filtered
