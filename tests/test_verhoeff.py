"""
Tests for the Verhoeff checksum algorithm and Aadhaar utilities.
"""

import unittest
from prompt_shield.algorithms.verhoeff import (
    validate_verhoeff,
    compute_verhoeff_checksum,
    generate_verhoeff_number,
    validate_aadhaar,
    generate_valid_aadhaar,
    clean_digits,
)


class TestVerhoeffAlgorithm(unittest.TestCase):
    def test_clean_digits(self):
        self.assertEqual(clean_digits("1234 5678 9012"), "123456789012")
        self.assertEqual(clean_digits(" 987-654-3210 "), "9876543210")
        self.assertEqual(clean_digits("ABC123XYZ45"), "12345")

    def test_known_verhoeff_vectors(self):
        # Known test vectors from Verhoeff standard examples:
        # Base: 236 -> checksum: 3 -> Full: 2363
        self.assertEqual(compute_verhoeff_checksum("236"), 3)
        self.assertTrue(validate_verhoeff("2363"))

        # Base: 142857 -> checksum: 0
        chk = compute_verhoeff_checksum("142857")
        self.assertTrue(validate_verhoeff(f"142857{chk}"))

        # Base: 0
        chk0 = compute_verhoeff_checksum("0")
        self.assertEqual(chk0, 4)
        self.assertTrue(validate_verhoeff("04"))

    def test_single_digit_error_detection(self):
        valid = "2363"
        self.assertTrue(validate_verhoeff(valid))
        # Changing any single digit must cause validation to fail
        for idx in range(len(valid)):
            for replacement in range(10):
                if str(replacement) != valid[idx]:
                    mutated = valid[:idx] + str(replacement) + valid[idx + 1 :]
                    self.assertFalse(
                        validate_verhoeff(mutated),
                        f"Expected {mutated} to fail Verhoeff check",
                    )

    def test_adjacent_transposition_error_detection(self):
        valid = "2363"
        self.assertTrue(validate_verhoeff(valid))
        # Swap adjacent digits (0 and 1: 3263, 1 and 2: 2633)
        self.assertFalse(validate_verhoeff("3263"))
        self.assertFalse(validate_verhoeff("2633"))

    def test_generate_verhoeff_number(self):
        base = "987654321"
        result = generate_verhoeff_number(base)
        self.assertTrue(result.startswith(base))
        self.assertEqual(len(result), len(base) + 1)
        self.assertTrue(validate_verhoeff(result))

    def test_aadhaar_validation_rules(self):
        # Starts with 0 -> invalid
        base_with_0 = "01234567890"
        aadhaar_0 = generate_verhoeff_number(base_with_0)
        self.assertTrue(validate_verhoeff(aadhaar_0))  # passes math
        self.assertFalse(validate_aadhaar(aadhaar_0))  # fails Aadhaar policy (cannot start with 0)

        # Starts with 1 -> invalid
        base_with_1 = "12345678901"
        aadhaar_1 = generate_verhoeff_number(base_with_1)
        self.assertFalse(validate_aadhaar(aadhaar_1))  # fails Aadhaar policy (cannot start with 1)

        # Invalid length (e.g. 11 or 13 digits)
        self.assertFalse(validate_aadhaar("23456789012"))
        self.assertFalse(validate_aadhaar("2345678901234"))

    def test_generated_synthetic_aadhaar_pool(self):
        # Generate 100 random synthetic Aadhaar numbers and test all properties
        for seed in range(100):
            aadhaar = generate_valid_aadhaar(seed=seed)
            self.assertEqual(len(aadhaar), 12)
            self.assertIn(aadhaar[0], "23456789")
            self.assertTrue(validate_aadhaar(aadhaar))

    def test_formatted_aadhaar(self):
        formatted = generate_valid_aadhaar(formatted=True, seed=42)
        parts = formatted.split(" ")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertEqual(len(part), 4)
        self.assertTrue(validate_aadhaar(formatted))


if __name__ == "__main__":
    unittest.main()
