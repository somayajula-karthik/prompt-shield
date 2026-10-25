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
from prompt_shield.evaluation.hf_adapter import (
    HF_LABEL_MAP,
    from_hf_ai4privacy_record,
    build_hf_ai4privacy_indian_corpus,
    save_hf_corpus,
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
    "HF_LABEL_MAP",
    "from_hf_ai4privacy_record",
    "build_hf_ai4privacy_indian_corpus",
    "save_hf_corpus",
    "EntityMetrics",
    "Discrepancy",
    "EvaluationReport",
    "evaluate_dataset",
    "compute_scores",
]
