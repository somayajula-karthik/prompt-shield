"""
Session Vault for Prompt Shield.

Maintains bidirectional, format-preserving mappings between real identifiers
and their synthetic surrogates with intra-session consistency and JSON persistence.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from prompt_shield.algorithms.verhoeff import clean_digits
from prompt_shield.engine.generator import SurrogateGenerator


@dataclass
class VaultEntry:
    """Represents a single mapped entity pair."""
    entity_type: str
    real_value: str
    surrogate_value: str
    created_at: str
    occurrence_count: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VaultEntry":
        return cls(
            entity_type=data["entity_type"],
            real_value=data["real_value"],
            surrogate_value=data["surrogate_value"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            occurrence_count=data.get("occurrence_count", 1),
        )


class SessionVault:
    """
    Session vault holding bidirectional mappings (Real <-> Surrogate).
    
    Guarantees:
    - Consistency: The exact same real identifier always maps to the same surrogate within a session.
    - Uniqueness: Two different real identifiers never share the same surrogate.
    - Reversibility: Any generated surrogate (including reformatted variants) can be mapped back.
    - Persistence: Can be exported to and imported from JSON.
    """

    def __init__(self, generator: Optional[SurrogateGenerator] = None):
        self.generator = generator or SurrogateGenerator()
        # Key: canonical real key -> VaultEntry
        self._entries_by_real: Dict[str, VaultEntry] = {}
        # Key: exact surrogate_value -> VaultEntry
        self._entries_by_surrogate: Dict[str, VaultEntry] = {}
        # Set of active surrogates for fast collision prevention
        self._active_surrogates: Set[str] = set()

    @staticmethod
    def canonicalize_token(entity_type: str, value: str) -> str:
        """
        Produce a formatting-independent canonical token for an identifier.
        - AADHAAR: 12 raw digits
        - PHONE: 10 core mobile digits (stripping +91, 91, or leading 0)
        - PAN / IFSC: uppercase trimmed string
        - UPI: lowercase trimmed string
        """
        raw = value.strip()
        if entity_type == "AADHAAR":
            return clean_digits(raw)
        if entity_type == "PHONE":
            digits = clean_digits(raw)
            if len(digits) == 12 and digits.startswith("91"):
                return digits[2:]
            if len(digits) == 11 and digits.startswith("0"):
                return digits[1:]
            return digits
        if entity_type in ("PAN", "IFSC"):
            return "".join(ch for ch in raw.upper() if ch.isalnum())
        if entity_type == "UPI":
            return raw.lower()
        return raw

    @classmethod
    def _normalize_key(cls, entity_type: str, real_value: str) -> str:
        """Create a stable canonical key for lookup."""
        return f"{entity_type}:{cls.canonicalize_token(entity_type, real_value)}"

    def get_or_create_surrogate(self, entity_type: str, real_value: str) -> str:
        """
        Retrieve existing surrogate for a real identifier, or generate and register a new one.
        """
        key = self._normalize_key(entity_type, real_value)

        if key in self._entries_by_real:
            entry = self._entries_by_real[key]
            entry.occurrence_count += 1
            return entry.surrogate_value

        # Generate unique, format-valid surrogate
        if entity_type == "UPI" and "@" in real_value:
            user_part, handle_part = real_value.split("@", 1)
            user_digits = clean_digits(user_part)
            # If the UPI username is a 10-digit Indian mobile number, link its surrogate
            # to the corresponding PHONE surrogate so cross-entity coherence is preserved
            if len(user_digits) == 10 and user_digits[0] in ("6", "7", "8", "9") and user_part.isdigit():
                phone_surrogate = self.get_or_create_surrogate("PHONE", user_digits)
                phone_surr_digits = self.canonicalize_token("PHONE", phone_surrogate)
                handle_lower = handle_part.lower()
                surr_handle = (
                    handle_lower
                    if handle_lower in self.generator.KNOWN_UPI_HANDLES
                    else self.generator._rng.choice(self.generator.KNOWN_UPI_HANDLES)
                )
                candidate = f"{phone_surr_digits}@{surr_handle}"
                if candidate != real_value and candidate not in self._active_surrogates:
                    surrogate = candidate
                else:
                    surrogate = self.generator.generate_surrogate(
                        entity_type=entity_type,
                        original_val=real_value,
                        existing_surrogates=self._active_surrogates,
                    )
            else:
                surrogate = self.generator.generate_surrogate(
                    entity_type=entity_type,
                    original_val=real_value,
                    existing_surrogates=self._active_surrogates,
                )
        else:
            surrogate = self.generator.generate_surrogate(
                entity_type=entity_type,
                original_val=real_value,
                existing_surrogates=self._active_surrogates,
            )

        entry = VaultEntry(
            entity_type=entity_type,
            real_value=real_value,
            surrogate_value=surrogate,
            created_at=datetime.now(timezone.utc).isoformat(),
            occurrence_count=1,
        )

        self._entries_by_real[key] = entry
        self._entries_by_surrogate[surrogate] = entry
        self._active_surrogates.add(surrogate)

        return surrogate

    def get_real_value(self, surrogate_value: str) -> Optional[str]:
        """
        Reverse-lookup: Retrieve original real value from surrogate (exact or canonical match).
        """
        entry = self._entries_by_surrogate.get(surrogate_value)
        if entry:
            return entry.real_value

        for candidate in self._entries_by_surrogate.values():
            if self.canonicalize_token(candidate.entity_type, candidate.surrogate_value) == self.canonicalize_token(
                candidate.entity_type, surrogate_value
            ):
                return candidate.real_value
        return None

    def get_all_entries(self) -> List[VaultEntry]:
        """Return list of all registered mapping entries."""
        return list(self._entries_by_real.values())

    def get_surrogate_map(self) -> Dict[str, str]:
        """Returns mapping from surrogate_value -> real_value for quick string replacement."""
        return {entry.surrogate_value: entry.real_value for entry in self._entries_by_surrogate.values()}

    def summary(self) -> Dict[str, int]:
        """Returns statistics on stored mappings per entity type."""
        counts: Dict[str, int] = {}
        for entry in self._entries_by_real.values():
            counts[entry.entity_type] = counts.get(entry.entity_type, 0) + 1
        return counts

    def to_dict(self) -> dict:
        """Serialize vault contents to a JSON-compatible dictionary."""
        return {
            "version": "1.0",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "total_entities": len(self._entries_by_real),
            "summary": self.summary(),
            "entries": [entry.to_dict() for entry in self._entries_by_real.values()],
        }

    def save(self, filepath: str) -> None:
        """Persist vault state to a JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict, generator: Optional[SurrogateGenerator] = None) -> "SessionVault":
        """Reconstruct a SessionVault from a dictionary."""
        vault = cls(generator=generator)
        entries_data = data.get("entries", [])
        for item in entries_data:
            entry = VaultEntry.from_dict(item)
            key = vault._normalize_key(entry.entity_type, entry.real_value)
            vault._entries_by_real[key] = entry
            vault._entries_by_surrogate[entry.surrogate_value] = entry
            vault._active_surrogates.add(entry.surrogate_value)
        return vault

    @classmethod
    def load(cls, filepath: str, generator: Optional[SurrogateGenerator] = None) -> "SessionVault":
        """Load vault state from a JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Vault file not found at: {filepath}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, generator=generator)
