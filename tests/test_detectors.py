"""
Unit tests for Aadhaar and PAN detectors.
"""

import unittest
from prompt_shield.detectors.aadhaar import AadhaarDetector
from prompt_shield.detectors.pan import PANDetector
from prompt_shield.detectors import detect_all


class TestDetectors(unittest.TestCase):
    def setUp(self):
        self.aadhaar_detector = AadhaarDetector()
        self.pan_detector = PANDetector()
        # Known valid synthetic Aadhaar numbers generated via Verhoeff
        self.valid_aadhaar_1 = "2679 0377 4206"
        self.valid_aadhaar_2 = "4415-9206-6111"
        self.valid_aadhaar_3 = "690934066215"

    def test_aadhaar_detection_formats(self):
        # Space-separated
        text1 = f"Please verify applicant Aadhaar {self.valid_aadhaar_1} before sanction."
        matches1 = self.aadhaar_detector.detect(text1)
        self.assertEqual(len(matches1), 1)
        self.assertEqual(matches1[0].entity_type, "AADHAAR")
        self.assertEqual(matches1[0].value, self.valid_aadhaar_1)
        self.assertEqual(text1[matches1[0].start : matches1[0].end], self.valid_aadhaar_1)

        # Hyphen-separated
        text2 = f"Reference: {self.valid_aadhaar_2} received."
        matches2 = self.aadhaar_detector.detect(text2)
        self.assertEqual(len(matches2), 1)
        self.assertEqual(matches2[0].value, self.valid_aadhaar_2)

        # Continuous 12 digits
        text3 = f"ID={self.valid_aadhaar_3}"
        matches3 = self.aadhaar_detector.detect(text3)
        self.assertEqual(len(matches3), 1)
        self.assertEqual(matches3[0].value, self.valid_aadhaar_3)

    def test_aadhaar_rejection_rules(self):
        # Invalid checksum (last digit mutated from 6 to 7)
        invalid_checksum = "2679 0377 4207"
        text = f"Invalid number {invalid_checksum} should be ignored."
        matches = self.aadhaar_detector.detect(text)
        self.assertEqual(len(matches), 0)

        # Starting with 0 or 1
        text_leading_zero = "0123 4567 8901"
        self.assertEqual(len(self.aadhaar_detector.detect(text_leading_zero)), 0)

        # Embedded in 16-digit bank account number
        text_bank_acc = "Account: 9267903774206123 is active."
        self.assertEqual(len(self.aadhaar_detector.detect(text_bank_acc)), 0)

    def test_pan_detection_individual(self):
        text = "Form 16 submitted by Ramesh Kumar, PAN: BZRPK4321A."
        matches = self.pan_detector.detect(text)
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.entity_type, "PAN")
        self.assertEqual(match.value, "BZRPK4321A")
        self.assertEqual(text[match.start : match.end], "BZRPK4321A")
        self.assertEqual(match.metadata["holder_type"], "P")
        self.assertTrue(match.metadata["is_individual"])

    def test_pan_detection_company_and_lowercase(self):
        text = "Vendor invoice from Tech Corp, pan: aabct9876c filed on portal."
        matches = self.pan_detector.detect(text)
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.value, "aabct9876c")
        self.assertEqual(match.metadata["normalized"], "AABCT9876C")
        self.assertEqual(match.metadata["holder_type"], "C")
        self.assertFalse(match.metadata["is_individual"])

    def test_pan_rejection_rules(self):
        # Invalid status character 'X'
        text_invalid_status = "Token ABCXE1234F is invalid."
        self.assertEqual(len(self.pan_detector.detect(text_invalid_status)), 0)

        # Invalid sequential zeros
        text_all_zeros = "PAN ABCDP0000A is not issued."
        self.assertEqual(len(self.pan_detector.detect(text_all_zeros)), 0)

        # Part of longer alphanumeric word / git commit hash
        text_hash = "Commit hash 7f8a9aabcp1234c99e12 cannot match PAN."
        self.assertEqual(len(self.pan_detector.detect(text_hash)), 0)

    def test_detect_all_multi_entity(self):
        text = (
            f"Loan application: Name Rajesh Rao, Aadhaar {self.valid_aadhaar_1}, "
            f"and PAN AFKPR8912K attached for processing."
        )
        matches = detect_all(text)
        self.assertEqual(len(matches), 2)

        # Ordered by start position
        self.assertEqual(matches[0].entity_type, "AADHAAR")
        self.assertEqual(matches[0].value, self.valid_aadhaar_1)

        self.assertEqual(matches[1].entity_type, "PAN")
        self.assertEqual(matches[1].value, "AFKPR8912K")

    def test_empty_input(self):
        self.assertEqual(detect_all(""), [])
        self.assertEqual(detect_all("Plain sentence without any personal numbers."), [])


if __name__ == "__main__":
    unittest.main()
