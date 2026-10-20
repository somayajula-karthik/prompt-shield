"""
UPI (Unified Payments Interface) VPA / ID detector.
"""

import re
from typing import List, Set
from prompt_shield.detectors.base import BaseDetector, Match


class UPIDetector(BaseDetector):
    """
    Detects Indian UPI IDs / Virtual Payment Addresses (VPAs).
    
    Structure:
    - Format: <username>@<handle>
    - Handles are associated with Indian banks or payment service providers (PSPs)
      such as @okhdfcbank, @oksbi, @okaxis, @okicici, @paytm, @ybl, @upi, etc.
    - Accurately excludes email addresses (e.g. gmail.com, outlook.com).
    - Ignores surrounding sentence punctuation (. , ? ! :) so VPAs at sentence boundaries match cleanly.
    """

    # Alphanumeric boundaries ensure trailing punctuation like '.' or ',' is not absorbed
    UPI_CANDIDATE_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9])([a-zA-Z0-9][a-zA-Z0-9._%+-]*[a-zA-Z0-9]|[a-zA-Z0-9])@"
        r"([a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]|[a-zA-Z0-9])(?![a-zA-Z0-9])"
    )

    # Major Indian Bank and PSP UPI handles
    KNOWN_UPI_HANDLES: Set[str] = {
        # Google Pay
        "okhdfcbank", "oksbi", "okaxis", "okicici",
        # PhonePe
        "ybl", "ibl", "axl",
        # Paytm
        "paytm",
        # BHIM
        "upi",
        # WhatsApp Pay
        "waaxis", "wahdfc", "waicici", "wasbi",
        # Major Banks
        "sbi", "hdfcbank", "icici", "axisbank", "kotak",
        "barodampay", "idfcbank", "pnb", "cnrb", "unionbank",
        "boi", "centralbank", "indus", "kvb", "aubank",
        "rbl", "federal", "dlb", "sib", "fbl", "scb",
        "hsbc", "dbs", "postbank", "airtel", "freecharge",
        "jupiteraxis", "slice", "fam", "amazonpay", "apl",
    }

    # Standard email domains / TLDs to reject
    COMMON_EMAIL_PROVIDERS: Set[str] = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "proton.me", "protonmail.com", "icloud.com", "zoho.com",
        "rediffmail.com", "live.com", "mail.com", "gmx.com",
    }

    COMMON_TLDS: Set[str] = {
        "com", "net", "org", "edu", "gov", "mil", "io", "co",
        "info", "me", "ai", "app", "dev", "tech", "online",
        "xyz", "ac.in", "edu.in", "gov.in", "co.in", "org.in",
    }

    @property
    def entity_type(self) -> str:
        return "UPI"

    def is_valid_upi(self, username: str, handle: str) -> bool:
        """
        Validates whether a username@handle pair is a UPI ID rather than an email address.
        """
        handle_lower = handle.lower().strip()

        # 1. Direct match with known UPI handles
        if handle_lower in self.KNOWN_UPI_HANDLES:
            return True

        # 2. Check if it is a common email provider
        if handle_lower in self.COMMON_EMAIL_PROVIDERS:
            return False

        # 3. Check if handle ends with a known web TLD (indicating an email address)
        for tld in self.COMMON_TLDS:
            if handle_lower.endswith(f".{tld}") or handle_lower == tld:
                return False

        # 4. If handle has no dots and is alphanumeric, it's very likely a custom bank PSP handle
        if "." not in handle_lower and len(handle_lower) >= 2:
            return True

        return False

    def detect(self, text: str) -> List[Match]:
        matches: List[Match] = []
        if not text:
            return matches

        for match in self.UPI_CANDIDATE_PATTERN.finditer(text):
            username = match.group(1)
            handle = match.group(2)
            raw_vpa = match.group(0)

            if self.is_valid_upi(username, handle):
                matches.append(
                    Match(
                        entity_type=self.entity_type,
                        start=match.start(),
                        end=match.end(),
                        value=raw_vpa,
                        confidence=0.98 if handle.lower() in self.KNOWN_UPI_HANDLES else 0.85,
                        metadata={
                            "username": username,
                            "handle": handle.lower(),
                            "is_known_handle": handle.lower() in self.KNOWN_UPI_HANDLES,
                        },
                    )
                )

        return matches
