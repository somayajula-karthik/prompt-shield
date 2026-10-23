"""
Masking and Reverse-Mapping (Unmasking) Engine for Prompt Shield.

Provides:
- Forward Masking: Detects Indian identifiers in text and substitutes them with
  format-valid surrogates using a SessionVault, preserving non-sensitive text bit-for-bit.
- Resilient Reverse Mapping (Unmasking): Scans AI assistant output for exact surrogates,
  canonical/reformatted surrogate variants (dropped spaces, stripped +91 prefix, case changes),
  and LLM partial-mask suffixes (e.g. 'XXXX XXXX 8603'), restoring genuine identifiers.
- Round-Trip Fidelity: Guarantees unmask(mask(text)) == text.
"""

import re
from typing import Dict, List, Optional, Tuple
from prompt_shield.algorithms.verhoeff import clean_digits
from prompt_shield.detectors import detect_all, Match
from prompt_shield.engine.vault import SessionVault, VaultEntry


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

    Handles three restoration tiers:
    1. Exact surrogate match (restores exact original value).
    2. Canonical reformatted variant (e.g. LLM stripped spaces in Aadhaar, dropped '+91 '
       in phone number, or changed PAN/IFSC/UPI casing).
    3. Partial-mask suffix match (e.g. LLM wrote 'XXXX XXXX 8603' or '******1590'),
       resolved when a unique vault entry owns that 4-digit suffix.
    """

    PARTIAL_MASK_PATTERN = re.compile(
        r"((?:[Xx\*]{2,4}[\s-]?){1,3})(\d{4})(?!\d)"
    )

    def __init__(self, vault: SessionVault):
        self.vault = vault

    @staticmethod
    def _format_like_observed(entry: VaultEntry, observed: str) -> str:
        """
        When the LLM reformats a surrogate (e.g. drops spaces from Aadhaar or strips '+91'
        from a phone number), restore the real value in the exact original user format
        by default, or preserve compact form if appropriate.
        """
        return entry.real_value

    def _build_variant_map(self) -> Dict[str, str]:
        """
        Builds a lookup table mapping both exact surrogates and common LLM-reformatted
        variants (compact digits, bare 10-digit phones, hyphen/space swaps, case variants)
        to their real values.
        """
        variants: Dict[str, str] = {}
        for entry in self.vault.get_all_entries():
            surr = entry.surrogate_value
            real = entry.real_value
            etype = entry.entity_type

            # Tier 1: Exact match always takes precedence
            variants[surr] = real

            # Tier 2: Reformatted variants by identifier type
            if etype == "AADHAAR":
                s_digits = clean_digits(surr)
                if len(s_digits) == 12:
                    variants.setdefault(s_digits, real)
                    variants.setdefault(f"{s_digits[:4]} {s_digits[4:8]} {s_digits[8:]}", real)
                    variants.setdefault(f"{s_digits[:4]}-{s_digits[4:8]}-{s_digits[8:]}", real)

            elif etype == "PHONE":
                s_core = SessionVault.canonicalize_token("PHONE", surr)
                if len(s_core) == 10:
                    variants.setdefault(s_core, real)
                    variants.setdefault(f"{s_core[:5]} {s_core[5:]}", real)
                    variants.setdefault(f"{s_core[:5]}-{s_core[5:]}", real)
                    variants.setdefault(f"+91 {s_core[:5]} {s_core[5:]}", real)
                    variants.setdefault(f"+91-{s_core[:5]}-{s_core[5:]}", real)
                    variants.setdefault(f"+91{s_core}", real)
                    variants.setdefault(f"0{s_core}", real)

            elif etype in ("PAN", "IFSC"):
                variants.setdefault(surr.upper(), real)
                variants.setdefault(surr.lower(), real)

            elif etype == "UPI":
                variants.setdefault(surr.lower(), real)
                variants.setdefault(surr.upper(), real)

        return variants

    def _resolve_partial_masks(self, text: str) -> str:
        """
        Restores real trailing 4 digits in LLM-redacted expressions like
        'XXXX XXXX 8603' or '******1590' when the 4-digit suffix uniquely matches
        a single numeric surrogate in the vault.
        """
        suffix_map: Dict[str, List[str]] = {}
        for entry in self.vault.get_all_entries():
            if entry.entity_type in ("AADHAAR", "PHONE"):
                s_digits = clean_digits(entry.surrogate_value)
                r_digits = clean_digits(entry.real_value)
                if len(s_digits) >= 4 and len(r_digits) >= 4:
                    s_last4 = s_digits[-4:]
                    r_last4 = r_digits[-4:]
                    suffix_map.setdefault(s_last4, []).append(r_last4)

        if not suffix_map:
            return text

        def _replace_match(m: re.Match) -> str:
            mask_prefix = m.group(1)
            obs_last4 = m.group(2)
            candidates = suffix_map.get(obs_last4, [])
            # Only substitute when unambiguous (unique suffix in session vault)
            if len(set(candidates)) == 1:
                return f"{mask_prefix}{candidates[0]}"
            return m.group(0)

        return self.PARTIAL_MASK_PATTERN.sub(_replace_match, text)

    def unmask(self, text: str) -> str:
        """
        Restore original values in text by replacing exact surrogates, canonical
        reformatted variants, and unambiguous partial-mask suffixes.
        """
        if not text:
            return text

        variant_map = self._build_variant_map()
        if not variant_map:
            return text

        # Sort keys longest-first so full formatted strings match before bare 10-digit substrings
        sorted_variants = sorted(variant_map.keys(), key=len, reverse=True)

        result = text
        for variant in sorted_variants:
            if variant in result:
                result = result.replace(variant, variant_map[variant])

        # Tier 3: Resolve partial masks like 'XXXX XXXX 8603'
        result = self._resolve_partial_masks(result)
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
