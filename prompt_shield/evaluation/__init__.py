"""
Prompt Shield Evaluation Framework.
Provides dataset loading, ground-truth validation, and benchmark metrics.
"""

from prompt_shield.evaluation.dataset import (
    EvalSample,
    load_evaluation_dataset,
    validate_dataset,
    dataset_summary,
    VALID_ENTITY_TYPES,
)
from prompt_shield.evaluation.metrics import (
    EntityMetrics,
    Discrepancy,
    EvaluationReport,
    evaluate_dataset,
    compute_scores,
)

__all__ = [
    "EvalSample",
    "load_evaluation_dataset",
    "validate_dataset",
    "dataset_summary",
    "VALID_ENTITY_TYPES",
    "EntityMetrics",
    "Discrepancy",
    "EvaluationReport",
    "evaluate_dataset",
    "compute_scores",
]
