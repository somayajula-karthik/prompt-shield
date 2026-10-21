"""
Unit tests for SurrogateGenerator and SessionVault.
"""

import tempfile
import unittest
from pathlib import Path

from prompt_shield.engine.generator import SurrogateGenerator
from prompt_shield.engine.vault import SessionVault
from prompt_shield.algorithms.verhoeff import validate_aadhaar, validate_verhoeff
from prompt_shield.detectors.pan import PANDetector
from prompt_shield.detectors.ifsc import IFSCDetector
from prompt_shield.detectors.upi import UPIDetector
from prompt_shield.detectors.phone import PhoneDetector


class TestSurrogateGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = SurrogateGenerator(seed=123)
        self.pan_detector = PANDetector()
        self.ifsc_detector = IFSCDetector()
        self.upi_detector = UPIDetector()
        self.phone_detector = PhoneDetector()

    def test_aadhaar_surrogate_validity_and_formatting(self):
        # Space formatted
        orig_spaced = "2679 0377 4206"
        surr_spaced = self.gen.generate_aadhaar(orig_spaced)
        self.assertNotEqual(surr_spaced, orig_spaced)
        self.assertEqual(len(surr_spaced), 14)  # with 2 spaces
        self.assertTrue(validate_aadhaar(surr_spaced))
        self.assertTrue(validate_verhoeff(surr_spaced))

        # Hyphen formatted
        orig_hyphen = "4415-9206-6111"
        surr_hyphen = self.gen.generate_aadhaar(orig_hyphen)
        self.assertEqual(len(surr_hyphen), 14)
        self.assertIn("-", surr_hyphen)
        self.assertTrue(validate_aadhaar(surr_hyphen))

        # Continuous
        orig_cont = "690934066215"
        surr_cont = self.gen.generate_aadhaar(orig_cont)
        self.assertEqual(len(surr_cont), 12)
        self.assertTrue(validate_aadhaar(surr_cont))

    def test_pan_surrogate_structure_and_status_preservation(self):
        # Individual PAN (4th char P)
        orig_p = "BZRPK4321A"
        surr_p = self.gen.generate_pan(orig_p)
        self.assertNotEqual(surr_p, orig_p)
        self.assertEqual(len(surr_p), 10)
        self.assertEqual(surr_p[3], "P")
        self.assertTrue(self.pan_detector.validate_pan(surr_p))

        # Company PAN (4th char C)
        orig_c = "AAACB1234C"
        surr_c = self.gen.generate_pan(orig_c)
        self.assertEqual(surr_c[3], "C")
        self.assertTrue(self.pan_detector.validate_pan(surr_c))

        # Lowercase preservation
        orig_lower = "bzrpk4321a"
        surr_lower = self.gen.generate_pan(orig_lower)
        self.assertTrue(surr_lower.islower())
        self.assertTrue(self.pan_detector.validate_pan(surr_lower.upper()))

    def test_upi_surrogate_validity(self):
        orig_upi = "rahul.sharma@okhdfcbank"
        surr_upi = self.gen.generate_upi(orig_upi)
        self.assertNotEqual(surr_upi, orig_upi)
        parts = surr_upi.split("@")
        self.assertEqual(len(parts), 2)
        self.assertTrue(self.upi_detector.is_valid_upi(parts[0], parts[1]))

    def test_ifsc_surrogate_validity(self):
        orig_ifsc = "SBIN0001234"
        surr_ifsc = self.gen.generate_ifsc(orig_ifsc)
        self.assertNotEqual(surr_ifsc, orig_ifsc)
        self.assertEqual(len(surr_ifsc), 11)
        self.assertEqual(surr_ifsc[4], "0")
        self.assertTrue(self.ifsc_detector.validate_ifsc(surr_ifsc))

    def test_phone_surrogate_formats(self):
        # Country code +91 with space
        orig_phone1 = "+91 98765 43210"
        surr_phone1 = self.gen.generate_phone(orig_phone1)
        self.assertNotEqual(surr_phone1, orig_phone1)
        self.assertTrue(surr_phone1.startswith("+91 "))
        self.assertTrue(self.phone_detector.validate_phone(surr_phone1))

        # Plain 10 digits
        orig_phone2 = "9876543210"
        surr_phone2 = self.gen.generate_phone(orig_phone2)
        self.assertEqual(len(surr_phone2), 10)
        self.assertTrue(self.phone_detector.validate_phone(surr_phone2))


class TestSessionVault(unittest.TestCase):
    def setUp(self):
        self.vault = SessionVault(generator=SurrogateGenerator(seed=42))

    def test_consistency_across_repeated_lookups(self):
        real_aadhaar = "2679 0377 4206"
        surrogate_1 = self.vault.get_or_create_surrogate("AADHAAR", real_aadhaar)
        surrogate_2 = self.vault.get_or_create_surrogate("AADHAAR", real_aadhaar)
        surrogate_3 = self.vault.get_or_create_surrogate("AADHAAR", real_aadhaar)

        # Consistency: exact same surrogate returned every time
        self.assertEqual(surrogate_1, surrogate_2)
        self.assertEqual(surrogate_2, surrogate_3)

        # Occurrence counter tracked
        entries = self.vault.get_all_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].occurrence_count, 3)

    def test_exact_reversibility(self):
        real_pan = "BZRPK4321A"
        surrogate_pan = self.vault.get_or_create_surrogate("PAN", real_pan)
        restored = self.vault.get_real_value(surrogate_pan)
        self.assertEqual(restored, real_pan)

    def test_uniqueness_across_different_entities(self):
        phone_1 = "+91 98765 43210"
        phone_2 = "+91 87654 32109"
        surr_1 = self.vault.get_or_create_surrogate("PHONE", phone_1)
        surr_2 = self.vault.get_or_create_surrogate("PHONE", phone_2)
        self.assertNotEqual(surr_1, surr_2)

    def test_vault_persistence_save_and_load(self):
        self.vault.get_or_create_surrogate("AADHAAR", "2679 0377 4206")
        self.vault.get_or_create_surrogate("PAN", "BZRPK4321A")
        self.vault.get_or_create_surrogate("UPI", "user@oksbi")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            self.vault.save(tmp_path)
            self.assertTrue(Path(tmp_path).exists())

            # Load into a fresh vault instance
            loaded_vault = SessionVault.load(tmp_path)
            self.assertEqual(len(loaded_vault.get_all_entries()), 3)
            self.assertEqual(loaded_vault.summary()["AADHAAR"], 1)
            self.assertEqual(loaded_vault.summary()["PAN"], 1)
            self.assertEqual(loaded_vault.summary()["UPI"], 1)

            # Check that reverse mappings still work perfectly
            surrogate_map = self.vault.get_surrogate_map()
            for surrogate, real in surrogate_map.items():
                self.assertEqual(loaded_vault.get_real_value(surrogate), real)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
