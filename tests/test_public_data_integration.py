"""
Unit tests for Public Registry Integration (RBI IFSC & NPCI UPI directories)
and Hugging Face ai4privacy-schema dataset evaluation.
"""

import json
import unittest
from pathlib import Path
from prompt_shield.detectors import IFSCDetector, UPIDetector
from prompt_shield.evaluation import (
    load_evaluation_dataset,
    validate_dataset,
    evaluate_dataset,
)


class TestPublicDataIntegration(unittest.TestCase):
    def test_public_registries_json_structure(self):
        registry_path = Path("data/public_registries.json")
        self.assertTrue(registry_path.exists(), "data/public_registries.json is missing")

        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("rbi_ifsc_banks", data)
        self.assertIn("npci_upi_handles", data)
        self.assertIn("itd_pan_status_codes", data)
        self.assertGreaterEqual(len(data["rbi_ifsc_banks"]), 50)
        self.assertGreaterEqual(len(data["npci_upi_handles"]), 45)
        self.assertEqual(len(data["itd_pan_status_codes"]), 10)

    def test_ifsc_and_upi_public_registry_metadata_enrichment(self):
        ifsc_detector = IFSCDetector()
        upi_detector = UPIDetector()

        ifsc_matches = ifsc_detector.detect(" Credit to IDFB0040101 and TGBI0000412.")
        self.assertEqual(len(ifsc_matches), 2)
        self.assertEqual(ifsc_matches[0].metadata["bank_name"], "IDFC FIRST Bank")
        self.assertEqual(ifsc_matches[1].metadata["bank_name"], "Telangana Grameena Bank")

        upi_matches = upi_detector.detect("Paid via vikram.rao@tapicici and merchant.hyd@ptsbi.")
        self.assertEqual(len(upi_matches), 2)
        self.assertEqual(upi_matches[0].metadata["psp_app"], "CRED")
        self.assertEqual(upi_matches[0].metadata["sponsor_bank"], "ICICI Bank")
        self.assertEqual(upi_matches[1].metadata["psp_app"], "Paytm")
        self.assertEqual(upi_matches[1].metadata["sponsor_bank"], "State Bank of India")

    def test_hf_ai4privacy_corpus_offset_integrity_and_evaluation(self):
        hf_path = "data/hf_ai4privacy_indian_eval.json"
        self.assertTrue(Path(hf_path).exists())

        samples = load_evaluation_dataset(hf_path)
        self.assertEqual(len(samples), 25)

        is_valid, errors = validate_dataset(samples)
        self.assertTrue(is_valid, f"HF dataset validation errors: {errors}")

        report = evaluate_dataset(samples, strict_span=True)
        self.assertEqual(report.total_samples, 25)
        self.assertEqual(report.positive_samples, 20)
        self.assertEqual(report.negative_samples, 5)
        self.assertEqual(report.overall.tp, 61)
        self.assertEqual(report.overall.fp, 0)
        self.assertEqual(report.overall.fn, 0)
        self.assertEqual(report.overall.precision, 1.0)
        self.assertEqual(report.overall.recall, 1.0)
        self.assertEqual(report.overall.f1, 1.0)


if __name__ == "__main__":
    unittest.main()
