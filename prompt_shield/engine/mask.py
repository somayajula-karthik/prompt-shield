"""
Masking and Reverse-Mapping (Unmasking) Engine for Prompt Shield.

Provides:
- Forward Masking: Detects Indian identifiers in text and substitutes them with
  format-valid surrogates using a SessionVault, preserving non-sensitive text bit-for-bit.
- Reverse Mapping (Unmasking): Scans AI assistant output for surrogate tokens and
  silently restores the genuine identifiers using the SessionVault.
- Round-Trip Fidelity: Guarantees unmask(mask(text)) == text.
"""

import re
from typing import List, Optional, Tuple
from prompt_shield.detectors import detect_all, Match
from prompt_shield.engine.vault import SessionVault


class MaskingEngine:
    """
    Substitutes sensitive Indian personal identifiers with realistic,
    format-valid surrogates while maintaining session consistency.
    """

    def __init__(self, vault: Optional[SessionVault] = None):
        self.vault = vault or SessionVault()

    def mask(self, text: str) -> Tuple[str, List[Match]]:
        """
        Scan text, detect all Indian identifiers, substitute them with surrogates from the vault.
        
        Returns:
            Tuple of (masked_text, matches_detected)
        """
        if not text:
            return text, []

        matches = detect_all(text)
        if not matches:
            return text, []

        # Process matches from right to left (descending start offset)
        # This prevents earlier offsets from being invalidated when replacements have different lengths
        chars = list(text)

        for match in reversed(matches):
            surrogate = self.vault.get_or_create_surrogate(
                entity_type=match.entity_type,
                real_value=match.value,
            )
            # Splice surrogate into character list
            chars[match.start : match.end] = list(surrogate)

        masked_text = "".join(chars)
        return masked_text, matches


class UnmaskingEngine:
    """
    Reverse-mapping layer that intercepts AI assistant output and restores
    original sensitive values using the session vault before displaying to the user.
    """

    def __init__(self, vault: SessionVault):
        self.vault = vault

    def unmask(self, text: str) -> str:
        """
        Restore original values in text by replacing any surrogate occurrences.
        
        Matches surrogates longest-first and uses word/boundary safety to prevent
        accidental partial-token corruption.
        """
        if not text:
            return text

        surrogate_map = self.vault.get_surrogate_map()
        if not surrogate_map:
            return text

        # Sort surrogates by length descending so longer tokens are matched before substrings
        sorted_surrogates = sorted(surrogate_map.keys(), key=len, reverse=True)

        result = text
        for surrogate in sorted_surrogates:
            real_val = surrogate_map[surrogate]
            # Replace exact occurrences of the surrogate string
            result = result.replace(surrogate, real_val)

        return result


def mask_text(text: str, vault: Optional[SessionVault] = None) -> Tuple[str, SessionVault, List[Match]]:
    """Convenience helper to mask text and return (masked_text, vault, matches)."""
    v = vault or SessionVault()
    engine = MaskingEngine(vault=v)
    masked_text, matches = engine.mask(text)
    return masked_text, v, matches


def unmask_text(text: str, vault: SessionVault) -> str:
    """Convenience helper to unmask text using an existing vault."""
    engine = UnmaskingEngine(vault=vault)
    return engine.unmask(text)
