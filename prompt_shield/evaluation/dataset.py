"""
Dataset structures and validation utilities for benchmark evaluation.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
from prompt_shield.detectors.base import Match


VALID_ENTITY_TYPES: Set[str] = {"AADHAAR", "PAN", "UPI", "IFSC", "PHONE"}


@dataclass
class EvalSample:
    """A hand-labelled evaluation sample with ground truth entity annotations."""
    id: str
    domain: str
    text: str
    entities: List[Match]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "domain": self.domain,
            "text": self.text,
            "entities": [m.to_dict() for m in self.entities],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvalSample":
        entities = [
            Match(
                entity_type=item["entity_type"],
                start=item["start"],
                end=item["end"],
                value=item["value"],
                confidence=item.get("confidence", 1.0),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("entities", [])
        ]
        return cls(
            id=data["id"],
            domain=data["domain"],
            text=data["text"],
            entities=entities,
        )


def load_evaluation_dataset(filepath: str) -> List[EvalSample]:
    """
    Load evaluation samples from a JSON dataset file.
    Automatically detects and converts both native Prompt Shield datasets
    (`text` + `entities`) and Hugging Face ai4privacy-format datasets
    (`source_text` + `privacy_mask`).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    from prompt_shield.evaluation.hf_adapter import (
        from_hf_ai4privacy_record,
        from_indic_synthetic_profile_row,
    )

    if isinstance(data, dict) and "profiles" in data:
        profiles = data["profiles"]
        return [
            from_indic_synthetic_profile_row(row, index=idx)
            for idx, row in enumerate(profiles)
        ]

    if not isinstance(data, list):
        raise ValueError("Evaluation dataset JSON must contain an array of sample objects or a Hugging Face profiles payload.")

    samples: List[EvalSample] = []
    for idx, item in enumerate(data):
        if "source_text" in item or "privacy_mask" in item:
            samples.append(from_hf_ai4privacy_record(item, index=idx))
        elif "aadhaar" in item and "pan" in item and "bank_account_ifsc" in item:
            samples.append(from_indic_synthetic_profile_row(item, index=idx))
        else:
            samples.append(EvalSample.from_dict(item))
    return samples


def validate_dataset(samples: List[EvalSample]) -> Tuple[bool, List[str]]:
    """
    Validates integrity of evaluation dataset.
    
    Verifies:
    1. Exact character offset slice match: text[start:end] == value for every annotation.
    2. Valid entity types.
    3. No overlapping ground-truth annotations within the same sample.
    4. Unique sample IDs.
    
    Returns:
        (is_valid: bool, error_messages: List[str])
    """
    errors: List[str] = []
    seen_ids: Set[str] = set()

    for sample in samples:
        # Check unique ID
        if sample.id in seen_ids:
            errors.append(f"Duplicate sample ID: '{sample.id}'")
        seen_ids.add(sample.id)

        # Check entity annotations
        sorted_entities = sorted(sample.entities, key=lambda m: (m.start, m.end))
        last_end = -1

        for ent in sorted_entities:
            # Check valid entity type
            if ent.entity_type not in VALID_ENTITY_TYPES:
                errors.append(
                    f"Sample '{sample.id}': Invalid entity type '{ent.entity_type}'."
                )

            # Check bounds within text length
            if ent.start < 0 or ent.end > len(sample.text) or ent.start >= ent.end:
                errors.append(
                    f"Sample '{sample.id}': Invalid span bounds [{ent.start}:{ent.end}] for text length {len(sample.text)}."
                )
                continue

            # Check slice match
            actual_slice = sample.text[ent.start : ent.end]
            if actual_slice != ent.value:
                errors.append(
                    f"Sample '{sample.id}': Text slice mismatch for entity [{ent.entity_type}]. "
                    f"Expected '{ent.value}', got '{actual_slice}' at span [{ent.start}:{ent.end}]."
                )

            # Check overlap
            if ent.start < last_end:
                errors.append(
                    f"Sample '{sample.id}': Overlapping entities detected at span [{ent.start}:{ent.end}]."
                )
            last_end = ent.end

    return len(errors) == 0, errors


def dataset_summary(samples: List[EvalSample]) -> Dict[str, any]:
    """Generates statistics on the evaluation dataset."""
    domain_counts: Dict[str, int] = {}
    entity_counts: Dict[str, int] = {k: 0 for k in VALID_ENTITY_TYPES}
    samples_with_entities = 0
    negative_samples = 0

    for s in samples:
        domain_counts[s.domain] = domain_counts.get(s.domain, 0) + 1
        if s.entities:
            samples_with_entities += 1
            for ent in s.entities:
                entity_counts[ent.entity_type] = entity_counts.get(ent.entity_type, 0) + 1
        else:
            negative_samples += 1

    return {
        "total_samples": len(samples),
        "positive_samples": samples_with_entities,
        "negative_samples": negative_samples,
        "domains": domain_counts,
        "entity_counts": entity_counts,
        "total_entities": sum(entity_counts.values()),
    }
