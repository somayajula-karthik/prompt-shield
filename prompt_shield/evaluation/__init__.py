"""
Prompt Shield Evaluation Framework.
Provides dataset loading, ground-truth validation, and benchmark metrics.
"""

from prompt_shield.evaluation.dataset import (
    EvalSample,
    load_evaluation_dataset,
    validate_dataset,
)

__all__ = [
    "EvalSample",
    "load_evaluation_dataset",
    "validate_dataset",
]
