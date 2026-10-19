"""
Identifier detectors for Prompt Shield.
"""

from typing import List, Optional
from prompt_shield.detectors.base import BaseDetector, Match
from prompt_shield.detectors.aadhaar import AadhaarDetector
from prompt_shield.detectors.pan import PANDetector

__all__ = [
    "BaseDetector",
    "Match",
    "AadhaarDetector",
    "PANDetector",
    "get_default_detectors",
    "detect_all",
]


def get_default_detectors() -> List[BaseDetector]:
    """Returns instances of all currently active detectors."""
    return [
        AadhaarDetector(),
        PANDetector(),
    ]


def detect_all(text: str, detectors: Optional[List[BaseDetector]] = None) -> List[Match]:
    """
    Run all detectors on input text and return non-overlapping matches sorted by start position.
    If two matches overlap, the longer match or higher confidence match is preferred.
    """
    if not text:
        return []

    active_detectors = detectors if detectors is not None else get_default_detectors()
    all_matches: List[Match] = []

    for detector in active_detectors:
        all_matches.extend(detector.detect(text))

    # Sort matches primarily by start ascending, then length descending
    all_matches.sort(key=lambda m: (m.start, -(m.end - m.start)))

    # Filter overlaps
    filtered: List[Match] = []
    last_end = -1
    for m in all_matches:
        if m.start >= last_end:
            filtered.append(m)
            last_end = m.end
        else:
            # Overlap detected; skip smaller/later match
            continue

    return filtered
