"""
UPI (Unified Payments Interface) VPA / ID detector.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set
from prompt_shield.detectors.base import BaseDetector, Match


def _load_npci_upi_registry() -> Dict[str, Dict[str, str]]:
    registry_path = Path(__file__).resolve().parents[2] / "data" / "public_registries.json"
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("npci_upi_handles", {})
        except Exception:
            pass
    return {}


NPCI_UPI_REGISTRY: Dict[str, Dict[str, str]] = _load_npci_upi_registry()


class UPIDetector(BaseDetector):
    """
    Detects Indian UPI IDs / Virtual Payment Addresses (VPAs).
    
    Structure:
    - Format: <username>@<handle>
    - Handles are associated with Indian banks or payment service providers (PSPs)
      such as @okhdfcbank, @oksbi, @okaxis, @okicici, @paytm, @ybl, @upi, etc.
    - Accurately excludes email addresses (e.g. gmail.com, outlook.com) and system/SSH
      host strings (e.g. deploy@buildserver, user@localhost).
    - Ignores surrounding sentence punctuation (. , ? ! :) so VPAs at sentence boundaries match cleanly.
    """

    # Alphanumeric boundaries ensure trailing punctuation like '.' or ',' is not absorbed
    UPI_CANDIDATE_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9])([a-zA-Z0-9][a-zA-Z0-9._%+-]*[a-zA-Z0-9]|[a-zA-Z0-9])@"
        r"([a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]|[a-zA-Z0-9])(?![a-zA-Z0-9])"
    )

    # Major Indian Bank and PSP UPI handles (merged with NPCI public registry)
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
    } | set(NPCI_UPI_REGISTRY.keys())

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

    # System / DevOps hostnames to reject when dot-less
    NON_PAYMENT_HOSTS: Set[str] = {
        "localhost", "buildserver", "server", "staging", "production",
        "prod", "devserver", "testserver", "ubuntu", "debian", "centos",
        "docker", "k8s", "internal", "localdomain", "workstation", "host",
    }

    SSH_CONTEXT_PATTERN = re.compile(
        r"\b(?:ssh|scp|sftp|rsync|git|ping|telnet|login)\b",
        re.IGNORECASE,
    )

    @property
    def entity_type(self) -> str:
        return "UPI"

    def is_valid_upi(self, username: str, handle: str) -> bool:
        """
        Validates whether a username@handle pair is a UPI ID rather than an email address
        or system hostname.
        """
        handle_lower = handle.lower().strip()

        # 1. Direct match with known UPI handles
        if handle_lower in self.KNOWN_UPI_HANDLES:
            return True

        # 2. Reject known non-payment system hostnames
        if handle_lower in self.NON_PAYMENT_HOSTS:
            return False

        # 3. Check if it is a common email provider
        if handle_lower in self.COMMON_EMAIL_PROVIDERS:
            return False

        # 4. Check if handle ends with a known web TLD (indicating an email address)
        for tld in self.COMMON_TLDS:
            if handle_lower.endswith(f".{tld}") or handle_lower == tld:
                return False

        # 5. If handle has no dots and is alphanumeric, accept as custom bank PSP handle
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

            if not self.is_valid_upi(username, handle):
                continue

            # If handle is not in KNOWN_UPI_HANDLES, reject when preceded by SSH/shell context
            handle_lower = handle.lower()
            if handle_lower not in self.KNOWN_UPI_HANDLES:
                window_start = max(0, match.start() - 30)
                preceding = text[window_start : match.start()]
                if self.SSH_CONTEXT_PATTERN.search(preceding):
                    continue

            handle_info = NPCI_UPI_REGISTRY.get(handle_lower, {})
            matches.append(
                Match(
                    entity_type=self.entity_type,
                    start=match.start(),
                    end=match.end(),
                    value=raw_vpa,
                    confidence=0.98 if handle_lower in self.KNOWN_UPI_HANDLES else 0.85,
                    metadata={
                        "username": username,
                        "handle": handle_lower,
                        "is_known_handle": handle_lower in self.KNOWN_UPI_HANDLES,
                        "psp_app": handle_info.get("psp_app", "Custom Bank PSP"),
                        "sponsor_bank": handle_info.get("sponsor_bank", "Unknown"),
                    },
                )
            )

        return matches
