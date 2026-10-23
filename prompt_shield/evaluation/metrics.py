"""
Benchmark evaluation metrics engine for Prompt Shield.
Computes True Positives (TP), False Positives (FP), False Negatives (FN),
Precision, Recall, and F1-score per entity class and overall.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from prompt_shield.detectors import detect_all, BaseDetector, Match
from prompt_shield.evaluation.dataset import EvalSample, VALID_ENTITY_TYPES


@dataclass
class EntityMetrics:
    """Evaluation metrics for a specific entity type or aggregate."""
    entity_type: str
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    support: int  # Total ground-truth entities (TP + FN)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Discrepancy:
    """Records an error (false positive or false negative) for diagnostic failure analysis."""
    sample_id: str
    error_type: str  # "FALSE_NEGATIVE" (missed) or "FALSE_POSITIVE" (hallucinated)
    entity_type: str
    value: str
    start: int
    end: int
    context_snippet: str

    def to_dict(self) -> dict:
        return asdict(self)


class EvaluationReport:
    """Contains comprehensive benchmark evaluation metrics and diagnostics."""

    def __init__(
        self,
        total_samples: int,
        positive_samples: int,
        negative_samples: int,
        metrics_by_type: Dict[str, EntityMetrics],
        overall: EntityMetrics,
        discrepancies: List[Discrepancy],
    ):
        self.total_samples = total_samples
        self.positive_samples = positive_samples
        self.negative_samples = negative_samples
        self.metrics_by_type = metrics_by_type
        self.overall = overall
        self.discrepancies = discrepancies

    def to_dict(self) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_samples": self.total_samples,
            "positive_samples": self.positive_samples,
            "negative_samples": self.negative_samples,
            "overall": self.overall.to_dict(),
            "by_type": {k: v.to_dict() for k, v in self.metrics_by_type.items()},
            "discrepancies_count": len(self.discrepancies),
            "discrepancies": [d.to_dict() for d in self.discrepancies],
        }

    def save(self, filepath: str) -> None:
        """Saves evaluation report to JSON file."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def compute_scores(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Computes Precision, Recall, and F1 given TP, FP, FN counts."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def evaluate_dataset(
    samples: List[EvalSample],
    detectors: Optional[List[BaseDetector]] = None,
    strict_span: bool = True,
) -> EvaluationReport:
    """
    Evaluates detector performance against hand-labelled ground truth samples.
    
    Args:
        samples: List of EvalSample objects with ground-truth entity spans.
        detectors: Optional list of detectors to evaluate (defaults to all active).
        strict_span: If True, requires exact character start and end match.
                     If False, matches if spans overlap and entity type agrees.
                     
    Returns:
        EvaluationReport with precision, recall, and F1 per type and overall.
    """
    stats: Dict[str, Dict[str, int]] = {
        ent_type: {"tp": 0, "fp": 0, "fn": 0} for ent_type in VALID_ENTITY_TYPES
    }
    discrepancies: List[Discrepancy] = []

    positive_samples = 0
    negative_samples = 0

    for sample in samples:
        if sample.entities:
            positive_samples += 1
        else:
            negative_samples += 1

        predictions: List[Match] = detect_all(sample.text, detectors=detectors)
        ground_truth: List[Match] = sample.entities

        matched_preds: Set[int] = set()

        for gt in ground_truth:
            matched_idx = None
            for p_idx, pred in enumerate(predictions):
                if p_idx in matched_preds:
                    continue

                if pred.entity_type != gt.entity_type:
                    continue

                if strict_span:
                    is_match = (pred.start == gt.start and pred.end == gt.end)
                else:
                    is_match = max(pred.start, gt.start) < min(pred.end, gt.end)

                if is_match:
                    matched_idx = p_idx
                    break

            if matched_idx is not None:
                matched_preds.add(matched_idx)
                stats[gt.entity_type]["tp"] += 1
            else:
                stats[gt.entity_type]["fn"] += 1
                snippet_start = max(0, gt.start - 20)
                snippet_end = min(len(sample.text), gt.end + 20)
                discrepancies.append(
                    Discrepancy(
                        sample_id=sample.id,
                        error_type="FALSE_NEGATIVE",
                        entity_type=gt.entity_type,
                        value=gt.value,
                        start=gt.start,
                        end=gt.end,
                        context_snippet=sample.text[snippet_start:snippet_end],
                    )
                )

        # Unmatched predictions are False Positives
        for p_idx, pred in enumerate(predictions):
            if p_idx not in matched_preds:
                # Ensure type is tracked in stats
                if pred.entity_type not in stats:
                    stats[pred.entity_type] = {"tp": 0, "fp": 0, "fn": 0}
                stats[pred.entity_type]["fp"] += 1

                snippet_start = max(0, pred.start - 20)
                snippet_end = min(len(sample.text), pred.end + 20)
                discrepancies.append(
                    Discrepancy(
                        sample_id=sample.id,
                        error_type="FALSE_POSITIVE",
                        entity_type=pred.entity_type,
                        value=pred.value,
                        start=pred.start,
                        end=pred.end,
                        context_snippet=sample.text[snippet_start:snippet_end],
                    )
                )

    # Compute metrics per type
    metrics_by_type: Dict[str, EntityMetrics] = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for ent_type, counts in stats.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        p, r, f = compute_scores(tp, fp, fn)
        metrics_by_type[ent_type] = EntityMetrics(
            entity_type=ent_type,
            tp=tp,
            fp=fp,
            fn=fn,
            precision=p,
            recall=r,
            f1=f,
            support=tp + fn,
        )
        total_tp += tp
        total_fp += fp
        total_fn += fn

    # Overall aggregate metrics (micro-average across all entities)
    overall_p, overall_r, overall_f = compute_scores(total_tp, total_fp, total_fn)
    overall = EntityMetrics(
        entity_type="OVERALL",
        tp=total_tp,
        fp=total_fp,
        fn=total_fn,
        precision=overall_p,
        recall=overall_r,
        f1=overall_f,
        support=total_tp + total_fn,
    )

    return EvaluationReport(
        total_samples=len(samples),
        positive_samples=positive_samples,
        negative_samples=negative_samples,
        metrics_by_type=metrics_by_type,
        overall=overall,
        discrepancies=discrepancies,
    )
