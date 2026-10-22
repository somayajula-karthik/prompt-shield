"""
Unit tests for the 50-sample synthetic evaluation dataset and validation framework.
"""

import unittest
from pathlib import Path
from prompt_shield.evaluation.dataset import (
    load_evaluation_dataset,
    validate_dataset,
    dataset_summary,
    VALID_ENTITY_TYPES,
)


class TestEvaluationDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_path = "data/samples_eval.json"
        cls.assertTrue(
            cls,
            Path(cls.dataset_path).exists(),
            f"Dataset not found at: {cls.dataset_path}",
        )
        cls.samples = load_evaluation_dataset(cls.dataset_path)

    def test_sample_count_is_fifty(self):
        """The internship brief strictly mandates 50 hand-labelled test samples."""
        self.assertEqual(len(self.samples), 50)

    def test_dataset_character_offset_integrity(self):
        """Verifies every single entity span matches the exact substring in text."""
        is_valid, errors = validate_dataset(self.samples)
        self.assertTrue(is_valid, f"Dataset validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_all_five_identifier_types_present(self):
        summary = dataset_summary(self.samples)
        entity_counts = summary["entity_counts"]

        # Ensure all 5 target identifier types are covered
        for ent_type in VALID_ENTITY_TYPES:
            count = entity_counts.get(ent_type, 0)
            self.assertGreater(
                count, 0, f"Entity type '{ent_type}' has 0 samples in evaluation set."
            )

        self.assertGreaterEqual(summary["total_entities"], 50)

    def test_domain_diversity(self):
        summary = dataset_summary(self.samples)
        domains = summary["domains"]
        self.assertGreaterEqual(len(domains), 5)
        self.assertIn("banking", domains)
        self.assertIn("healthcare", domains)
        self.assertIn("tax_payroll", domains)
        self.assertIn("ecommerce", domains)
        self.assertIn("distractor", domains)

    def test_negative_distractor_samples(self):
        """Ensures distractor samples have zero entities to test false-positive resistance."""
        negative_samples = [s for s in self.samples if s.domain == "distractor"]
        self.assertGreaterEqual(len(negative_samples), 5)
        for s in negative_samples:
            self.assertEqual(
                len(s.entities),
                0,
                f"Negative sample '{s.id}' unexpectedly contains entities.",
            )

    def test_unique_sample_ids(self):
        ids = [s.id for s in self.samples]
        self.assertEqual(len(ids), len(set(ids)), "Found duplicate sample IDs in dataset.")


if __name__ == "__main__":
    unittest.main()
