"""
Unit tests for MaskingEngine, UnmaskingEngine, and Round-Trip Fidelity.
"""

import unittest
from prompt_shield.engine import (
    SessionVault,
    SurrogateGenerator,
    MaskingEngine,
    UnmaskingEngine,
    mask_text,
    unmask_text,
)


class TestMaskingAndUnmasking(unittest.TestCase):
    def setUp(self):
        # Deterministic seed for reproducible testing
        self.generator = SurrogateGenerator(seed=999)
        self.vault = SessionVault(generator=self.generator)
        self.masker = MaskingEngine(vault=self.vault)
        self.unmasker = UnmaskingEngine(vault=self.vault)

    def test_single_entity_mask_and_unmask(self):
        text = "Client's Aadhaar number is 2679 0377 4206 for identity verification."
        masked, matches = self.masker.mask(text)

        # Ensure original Aadhaar is not in masked text
        self.assertNotIn("2679 0377 4206", masked)
        self.assertEqual(len(matches), 1)

        # Unmask and verify round-trip identity
        restored = self.unmasker.unmask(masked)
        self.assertEqual(restored, text)

    def test_all_five_identifiers_round_trip(self):
        original_doc = (
            "APPLICATION FOR LOAN DISBURSAL\n"
            "------------------------------\n"
            "Applicant: Vikram Joshi\n"
            "Mobile: +91 98765 43210\n"
            "Aadhaar: 2679 0377 4206\n"
            "PAN: BZRPK4321A\n"
            "Disbursement Bank IFSC: SBIN0001234\n"
            "Repayment UPI: vikram.joshi@okhdfcbank\n"
            "Please process immediately."
        )

        masked_doc, matches = self.masker.mask(original_doc)
        self.assertEqual(len(matches), 5)

        # Verify none of the real PII exists in masked_doc
        self.assertNotIn("+91 98765 43210", masked_doc)
        self.assertNotIn("2679 0377 4206", masked_doc)
        self.assertNotIn("BZRPK4321A", masked_doc)
        self.assertNotIn("SBIN0001234", masked_doc)
        self.assertNotIn("vikram.joshi@okhdfcbank", masked_doc)

        # Verify layout, newlines, and non-sensitive text are preserved
        self.assertIn("APPLICATION FOR LOAN DISBURSAL", masked_doc)
        self.assertIn("Applicant: Vikram Joshi", masked_doc)

        # Exact bit-for-bit restoration
        restored_doc = self.unmasker.unmask(masked_doc)
        self.assertEqual(restored_doc, original_doc)

    def test_intra_document_consistency_multiple_occurrences(self):
        text = (
            "Primary PAN: BZRPK4321A.\n"
            "Please confirm if BZRPK4321A matches the tax records.\n"
            "Note that BZRPK4321A belongs to an individual."
        )

        masked, matches = self.masker.mask(text)
        self.assertEqual(len(matches), 3)

        # Find the surrogate used for BZRPK4321A
        surrogate_pan = self.vault.get_or_create_surrogate("PAN", "BZRPK4321A")

        # The surrogate must appear exactly 3 times in masked text
        self.assertEqual(masked.count(surrogate_pan), 3)

        # Reverse-mapping restores all 3 occurrences
        restored = self.unmasker.unmask(masked)
        self.assertEqual(restored, text)

    def test_ai_response_simulation(self):
        """
        Simulates an actual AI assistant workflow:
        1. User prompt with sensitive Indian PII is masked by Prompt Shield.
        2. Prompt sent to LLM contains ONLY format-valid surrogates.
        3. LLM replies mentioning the surrogates.
        4. Prompt Shield intercepts response and restores real PII.
        """
        user_prompt = "Review tax liability for PAN BZRPK4321A and Aadhaar 2679 0377 4206."
        masked_prompt, vault, _ = mask_text(user_prompt)

        surr_pan = vault.get_or_create_surrogate("PAN", "BZRPK4321A")
        surr_aadhaar = vault.get_or_create_surrogate("AADHAAR", "2679 0377 4206")

        # Simulated AI Assistant response mentioning the surrogates
        simulated_llm_response = (
            f"Based on PAN {surr_pan} and linked Aadhaar {surr_aadhaar}, "
            f"the individual taxpayer qualifies for rebate under Section 87A."
        )

        # Unmask the AI response
        restored_response = unmask_text(simulated_llm_response, vault)

        expected_response = (
            "Based on PAN BZRPK4321A and linked Aadhaar 2679 0377 4206, "
            "the individual taxpayer qualifies for rebate under Section 87A."
        )
        self.assertEqual(restored_response, expected_response)

    def test_empty_or_neutral_text(self):
        neutral = "This is a simple text with no numbers or sensitive data."
        masked, matches = self.masker.mask(neutral)
        self.assertEqual(masked, neutral)
        self.assertEqual(len(matches), 0)
        self.assertEqual(self.unmasker.unmask(masked), neutral)


if __name__ == "__main__":
    unittest.main()
