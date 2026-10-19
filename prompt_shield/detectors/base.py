"""
Base detector interfaces and data models for Prompt Shield.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass(frozen=True)
class Match:
    """Represents a detected identifier in text."""
    entity_type: str
    start: int
    end: int
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class BaseDetector(ABC):
    """Abstract base class for all identifier detectors."""

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """The identifier type this detector handles (e.g. 'AADHAAR', 'PAN')."""
        pass

    @abstractmethod
    def detect(self, text: str) -> List[Match]:
        """
        Scan input text and return all non-overlapping valid matches.
        
        Args:
            text: Arbitrary input string to scan.
            
        Returns:
            List of Match objects with character start/end offsets.
        """
        pass
