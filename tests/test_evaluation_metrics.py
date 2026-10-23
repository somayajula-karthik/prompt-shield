"""
Unit tests for the Evaluation Metrics Engine and Benchmark Runner.
"""

import tempfile
import unittest
from pathlib import Path

from prompt_shield.evaluation import (
    load_evaluation_dataset,
    evaluate_dataset,
    compute_scores,
    EvalSample,
)
from prompt_shield.detectors.base import Match


class TestEvaluationMetrics(unittest.TestCase):
    def test_compute_scores_math(self):
        # Perfect scores
        p, r, f = compute_scores(tp=10, fp=0, fn=0)
        self.assertEqual((p, r, f), (1.0, 1.0, 1.0))

        # Precision 50%, Recall 100%
        p, r, f = compute_scores(tp=10, fp=10, fn=0)
        self.assertEqual(p, 0.5)
        self.assertEqual(r, 1.0)
        self.assertAlmostEqual(f, 0.6667, places=4)

        # Precision 100%, Recall 50%
        p, r, f = compute_scores(tp=10, fp=0, fn=10)
        self.assertEqual(p, 1.0)
        self.assertEqual(r, 0.5)
        self.assertAlmostEqual(f, 0.6667, places=4)

        # All zeros edge case (no ground truth, no predictions -> 100% precision and recall)
        p, r, f = compute_scores(tp=0, fp=0, fn=0)
        self.assertEqual((p, r, f), (1.0, 1.0, 1.0))

        # Complete failure edge case (zero true positives with errors)
        p_fail, r_fail, f_fail = compute_scores(tp=0, fp=5, fn=5)
        self.assertEqual((p_fail, r_fail, f_fail), (0.0, 0.0, 0.0))

    def test_evaluate_on_synthetic_controlled_sample(self):
        # Sample with 1 ground-truth PAN
        sample = EvalSample(
            id="test_01",
            domain="test",
            text="Employee PAN is BZRPK4321A verified.",
            entities=[
                Match(entity_type="PAN", start=16, end=26, value="BZRPK4321A")
            ],
        )

        report = evaluate_dataset([sample])
        pan_metrics = report.metrics_by_type["PAN"]

        self.assertEqual(pan_metrics.tp, 1)
        self.assertEqual(pan_metrics.fp, 0)
        self.assertEqual(pan_metrics.fn, 0)
        self.assertEqual(pan_metrics.precision, 1.0)
        self.assertEqual(pan_metrics.recall, 1.0)
        self.assertEqual(pan_metrics.f1, 1.0)
        self.assertEqual(len(report.discrepancies), 0)

    def test_full_benchmark_dataset_evaluation(self):
        """Runs full evaluation on the official 50-sample dataset."""
        dataset_path = "data/samples_eval.json"
        self.assertTrue(Path(dataset_path).exists())

        samples = load_evaluation_dataset(dataset_path)
        self.assertEqual(len(samples), 50)

        report = evaluate_dataset(samples, strict_span=True)

        # Total evaluation set metrics check
        self.assertEqual(report.total_samples, 50)
        self.assertEqual(report.positive_samples, 42)
        self.assertEqual(report.negative_samples, 8)

        # Overall detection performance must be research-grade
        self.assertGreaterEqual(report.overall.precision, 0.95)
        self.assertGreaterEqual(report.overall.recall, 0.95)
        self.assertGreaterEqual(report.overall.f1, 0.95)

        # Test report saving and loading
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            report.save(tmp_path)
            self.assertTrue(Path(tmp_path).exists())
            rep_dict = report.to_dict()
            self.assertEqual(rep_dict["total_samples"], 50)
            self.assertIn("overall", rep_dict)
            self.assertIn("by_type", rep_dict)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
