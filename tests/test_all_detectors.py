"""
Unit tests for all 5 Indian identifier detectors:
Aadhaar, PAN, UPI ID, IFSC Code, and Mobile Phone Numbers.
"""

import unittest
from prompt_shield.detectors import (
    AadhaarDetector,
    PANDetector,
    UPIDetector,
    IFSCDetector,
    PhoneDetector,
    detect_all,
)


class TestAllDetectors(unittest.TestCase):
    def setUp(self):
        self.aadhaar_detector = AadhaarDetector()
        self.pan_detector = PANDetector()
        self.upi_detector = UPIDetector()
        self.ifsc_detector = IFSCDetector()
        self.phone_detector = PhoneDetector()

    # ------------------ UPI TESTS ------------------
    def test_upi_valid_handles(self):
        text = (
            "Payments made to rahul.sharma@okhdfcbank, 9876543210@paytm, "
            "vendor@upi, and priya123@ybl were confirmed."
        )
        matches = self.upi_detector.detect(text)
        self.assertEqual(len(matches), 4)
        found_values = [m.value for m in matches]
        self.assertIn("rahul.sharma@okhdfcbank", found_values)
        self.assertIn("9876543210@paytm", found_values)
        self.assertIn("vendor@upi", found_values)
        self.assertIn("priya123@ybl", found_values)

        for m in matches:
            self.assertEqual(text[m.start : m.end], m.value)

    def test_upi_rejects_email_addresses(self):
        text = (
            "Contact us at contact@hdfcbank.com, support@company.org, "
            "or john.doe@gmail.com for details."
        )
        matches = self.upi_detector.detect(text)
        self.assertEqual(len(matches), 0)

    # ------------------ IFSC TESTS ------------------
    def test_ifsc_valid_codes(self):
        text = "Transfer branch IFSC is SBIN0001234, secondary branch is HDFC0005678."
        matches = self.ifsc_detector.detect(text)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].value, "SBIN0001234")
        self.assertEqual(matches[0].metadata["bank_prefix"], "SBIN")
        self.assertEqual(matches[1].value, "HDFC0005678")
        self.assertEqual(matches[1].metadata["bank_prefix"], "HDFC")

        for m in matches:
            self.assertEqual(text[m.start : m.end], m.value)

    def test_ifsc_rejection_rules(self):
        # 5th char not '0'
        text_non_zero = "Invalid IFSC SBIN1001234 should be rejected."
        self.assertEqual(len(self.ifsc_detector.detect(text_non_zero)), 0)

        # Embedded inside longer alphanumeric string
        text_embedded = "Hash code ABCSBIN0001234XYZ cannot match."
        self.assertEqual(len(self.ifsc_detector.detect(text_embedded)), 0)

        # Shorter than 11 characters
        text_short = "Code SBIN0123 is too short."
        self.assertEqual(len(self.ifsc_detector.detect(text_short)), 0)

    # ------------------ PHONE TESTS ------------------
    def test_phone_valid_formats(self):
        test_cases = [
            ("Call me at +91 98765 43210 today.", "+91 98765 43210"),
            ("Direct line: +91-87654-32109.", "+91-87654-32109"),
            ("Mobile number is 9123456789.", "9123456789"),
            ("Contact 098765 43210 for billing.", "098765 43210"),
            ("WhatsApp on 78901 23456.", "78901 23456"),
        ]
        for text, expected in test_cases:
            matches = self.phone_detector.detect(text)
            self.assertEqual(len(matches), 1, f"Failed to match for: {text}")
            self.assertEqual(matches[0].value, expected)
            self.assertEqual(text[matches[0].start : matches[0].end], expected)

    def test_phone_rejection_rules(self):
        # Starts with invalid initial digit (e.g. 1-5)
        text_invalid_start = "Call 5123456789 or 1234567890."
        self.assertEqual(len(self.phone_detector.detect(text_invalid_start)), 0)

        # Repetitive digits
        text_repetitive = "Dial 9999999999."
        self.assertEqual(len(self.phone_detector.detect(text_repetitive)), 0)

        # Embedded inside longer 16-digit account number
        text_acc = "Card 9876543210123456 processed."
        self.assertEqual(len(self.phone_detector.detect(text_acc)), 0)

    # ------------------ MULTI-ENTITY INTEGRATION (ALL 5) ------------------
    def test_detect_all_five_identifiers(self):
        # A realistic synthetic banking/loan statement containing all 5 identifier types
        text = (
            "Customer KYC Record: Name Suresh Iyer, Mobile +91 98765 43210, "
            "Aadhaar 2679 0377 4206, PAN BZRPK4321A. "
            "Salary credited to SBI branch IFSC SBIN0001234 via VPA suresh.iyer@oksbi."
        )

        matches = detect_all(text)
        self.assertEqual(len(matches), 5)

        expected_types = ["PHONE", "AADHAAR", "PAN", "IFSC", "UPI"]
        actual_types = [m.entity_type for m in matches]
        self.assertEqual(actual_types, expected_types)

        # Verify values and slices
        self.assertEqual(matches[0].value, "+91 98765 43210")
        self.assertEqual(matches[1].value, "2679 0377 4206")
        self.assertEqual(matches[2].value, "BZRPK4321A")
        self.assertEqual(matches[3].value, "SBIN0001234")
        self.assertEqual(matches[4].value, "suresh.iyer@oksbi")

        for m in matches:
            self.assertEqual(text[m.start : m.end], m.value)

    def test_context_aware_lookalike_rejection(self):
        # 10-digit order IDs, account numbers, and currency amounts should not match PHONE
        self.assertEqual(len(detect_all("Order ID 9123456780 has shipped.")), 0)
        self.assertEqual(len(detect_all("Savings account number 7012345678 at the branch.")), 0)
        self.assertEqual(len(detect_all("Invoice total Rs 8000000001 is a typo in the ledger.")), 0)

        # 12-digit UTR number that happens to pass Verhoeff should not match AADHAAR
        self.assertEqual(len(detect_all("UTR reference 810033076661 for NEFT transfer.")), 0)

        # System/SSH host strings should not match UPI
        self.assertEqual(len(detect_all("SSH into deploy@buildserver tonight.")), 0)
        self.assertEqual(len(detect_all("Ping me as karthik@localhost for the test mail.")), 0)

    def test_ocr_and_pdf_whitespace_tolerant_detection(self):
        # OCR dot-separated, double-spaced, and line-wrapped Aadhaar numbers
        m_dot = detect_all("Aadhaar: 2679.0377.4206")
        self.assertEqual(len(m_dot), 1)
        self.assertEqual(m_dot[0].entity_type, "AADHAAR")
        self.assertEqual(m_dot[0].value, "2679.0377.4206")

        m_wrap = detect_all("Aadhaar: 2679 0377\n4206")
        self.assertEqual(len(m_wrap), 1)
        self.assertEqual(m_wrap[0].entity_type, "AADHAAR")
        self.assertEqual(m_wrap[0].value, "2679 0377\n4206")

        # PDF block-spaced and character-spaced PAN cards
        m_pan_block = detect_all("PAN: BZRPK 4321 A")
        self.assertEqual(len(m_pan_block), 1)
        self.assertEqual(m_pan_block[0].entity_type, "PAN")
        self.assertEqual(m_pan_block[0].metadata["normalized"], "BZRPK4321A")

        m_pan_char = detect_all("PAN: B Z R P K 4 3 2 1 A")
        self.assertEqual(len(m_pan_char), 1)
        self.assertEqual(m_pan_char[0].entity_type, "PAN")
        self.assertEqual(m_pan_char[0].metadata["normalized"], "BZRPK4321A")

        # Double-spaced and dot-separated mobile numbers
        m_phone = detect_all("Mobile: +91 98765  43210")
        self.assertEqual(len(m_phone), 1)
        self.assertEqual(m_phone[0].entity_type, "PHONE")
        self.assertEqual(m_phone[0].value, "+91 98765  43210")


if __name__ == "__main__":
    unittest.main()
