"""
Synthetic evaluation dataset builder for Prompt Shield.
Generates 50 hand-crafted synthetic test samples across diverse domains with exact offsets.
Adheres strictly to the Responsible Research Policy (zero real personal data).
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from prompt_shield.algorithms.verhoeff import generate_valid_aadhaar


def make_sample(sample_id: str, domain: str, template: str, entity_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Substitutes placeholder values into template, recording exact character start and end offsets.
    """
    text = template
    entities = []

    # Sort specs by placeholder appearance order to avoid replacement collision
    for spec in entity_specs:
        placeholder = spec["placeholder"]
        val = spec["value"]
        ent_type = spec["type"]

        idx = text.find(placeholder)
        if idx == -1:
            raise ValueError(f"Placeholder '{placeholder}' not found in template for sample {sample_id}")

        text = text[:idx] + val + text[idx + len(placeholder):]
        entities.append({
            "entity_type": ent_type,
            "start": idx,
            "end": idx + len(val),
            "value": val,
        })

    # Sort entities by start offset
    entities.sort(key=lambda e: e["start"])

    return {
        "id": sample_id,
        "domain": domain,
        "text": text,
        "entities": entities,
    }


def generate_fifty_samples() -> List[Dict[str, Any]]:
    # Generate deterministic valid Aadhaar numbers for positive samples
    aadh = [generate_valid_aadhaar(formatted=(i % 2 == 0), seed=i + 500) for i in range(25)]

    samples: List[Dict[str, Any]] = [
        # ==========================================
        # DOMAIN 1: BANKING & LOAN (10 samples)
        # ==========================================
        make_sample(
            "bank_01", "banking",
            "Loan application received for Suresh Iyer. Primary contact [PHONE] and Aadhaar [AADHAAR] submitted.",
            [
                {"placeholder": "[PHONE]", "value": "+91 98765 43210", "type": "PHONE"},
                {"placeholder": "[AADHAAR]", "value": aadh[0], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "bank_02", "banking",
            "Please disburse funds to account with IFSC [IFSC] linked to PAN [PAN].",
            [
                {"placeholder": "[IFSC]", "value": "SBIN0001234", "type": "IFSC"},
                {"placeholder": "[PAN]", "value": "BZRPK4321A", "type": "PAN"},
            ]
        ),
        make_sample(
            "bank_03", "banking",
            "Customer KYC verified with Aadhaar [AADHAAR] and PAN [PAN].",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[1], "type": "AADHAAR"},
                {"placeholder": "[PAN]", "value": "AFKPR8912K", "type": "PAN"},
            ]
        ),
        make_sample(
            "bank_04", "banking",
            "Mandate registered for recurring repayment via UPI [UPI] against phone [PHONE].",
            [
                {"placeholder": "[UPI]", "value": "suresh.iyer@okhdfcbank", "type": "UPI"},
                {"placeholder": "[PHONE]", "value": "9876543210", "type": "PHONE"},
            ]
        ),
        make_sample(
            "bank_05", "banking",
            "Commercial loan file for M/s Apex Tech: Corporate PAN [PAN] and branch IFSC [IFSC].",
            [
                {"placeholder": "[PAN]", "value": "AAACB1234C", "type": "PAN"},
                {"placeholder": "[IFSC]", "value": "HDFC0005678", "type": "IFSC"},
            ]
        ),
        make_sample(
            "bank_06", "banking",
            "RTGS transfer request initiated: Beneficiary IFSC [IFSC] with callback to [PHONE].",
            [
                {"placeholder": "[IFSC]", "value": "ICIC0000999", "type": "IFSC"},
                {"placeholder": "[PHONE]", "value": "+91-87654-32109", "type": "PHONE"},
            ]
        ),
        make_sample(
            "bank_07", "banking",
            "Joint borrower application: Aadhaar [AADHAAR] and mobile [PHONE].",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[2], "type": "AADHAAR"},
                {"placeholder": "[PHONE]", "value": "098765 43210", "type": "PHONE"},
            ]
        ),
        make_sample(
            "bank_08", "banking",
            "Fixed Deposit lien marked for tax audit under PAN [PAN].",
            [
                {"placeholder": "[PAN]", "value": "DKRPJ7712M", "type": "PAN"},
            ]
        ),
        make_sample(
            "bank_09", "banking",
            "Account closure request for IFSC [IFSC] submitted by holder of PAN [PAN].",
            [
                {"placeholder": "[IFSC]", "value": "UTIB0000123", "type": "IFSC"},
                {"placeholder": "[PAN]", "value": "CKLPA4521E", "type": "PAN"},
            ]
        ),
        make_sample(
            "bank_10", "banking",
            "Home loan sanction note: Co-applicant Aadhaar [AADHAAR] verified via OTP on [PHONE].",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[3], "type": "AADHAAR"},
                {"placeholder": "[PHONE]", "value": "+91 78901 23456", "type": "PHONE"},
            ]
        ),

        # ==========================================
        # DOMAIN 2: HEALTHCARE & HOSPITAL (10 samples)
        # ==========================================
        make_sample(
            "health_01", "healthcare",
            "Patient Admission: Ramesh Rao, Emergency Phone: [PHONE], Identity Aadhaar: [AADHAAR].",
            [
                {"placeholder": "[PHONE]", "value": "+91 91234 56789", "type": "PHONE"},
                {"placeholder": "[AADHAAR]", "value": aadh[4], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "health_02", "healthcare",
            "Discharge Summary for Apollo Clinic: Insurance billing under PAN [PAN] cleared.",
            [
                {"placeholder": "[PAN]", "value": "GHRPK9012N", "type": "PAN"},
            ]
        ),
        make_sample(
            "health_03", "healthcare",
            "Diagnostic Lab Report: Fasting Glucose 142 mg/dL. Billing UPI: [UPI].",
            [
                {"placeholder": "[UPI]", "value": "care.billing@paytm", "type": "UPI"},
            ]
        ),
        make_sample(
            "health_04", "healthcare",
            "Doctor teleconsultation booked: Follow up with patient on [PHONE].",
            [
                {"placeholder": "[PHONE]", "value": "9812345678", "type": "PHONE"},
            ]
        ),
        make_sample(
            "health_05", "healthcare",
            "Medical reimbursement claim: Hospital IFSC [IFSC] and patient PAN [PAN] submitted.",
            [
                {"placeholder": "[IFSC]", "value": "BARB0BIMLKO", "type": "IFSC"},
                {"placeholder": "[PAN]", "value": "JKLPB1290K", "type": "PAN"},
            ]
        ),
        make_sample(
            "health_06", "healthcare",
            "Pathology center requisition: Patient Aadhaar [AADHAAR] for health record integration.",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[5], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "health_07", "healthcare",
            "Emergency Ward Triage: Next of kin contact [PHONE], Aadhaar ID [AADHAAR].",
            [
                {"placeholder": "[PHONE]", "value": "+91 69876 54321", "type": "PHONE"},
                {"placeholder": "[AADHAAR]", "value": aadh[6], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "health_08", "healthcare",
            "Pharmacy invoice: Consultation fee paid via UPI [UPI], prescription filed.",
            [
                {"placeholder": "[UPI]", "value": "medicos.delhi@ybl", "type": "UPI"},
            ]
        ),
        make_sample(
            "health_09", "healthcare",
            "Surgeon referral note: Senior consultant contact available at [PHONE].",
            [
                {"placeholder": "[PHONE]", "value": "087654 32109", "type": "PHONE"},
            ]
        ),
        make_sample(
            "health_10", "healthcare",
            "Health insurance cashless settlement: TPA PAN [PAN] and settlement bank IFSC [IFSC].",
            [
                {"placeholder": "[PAN]", "value": "AAACT8921B", "type": "PAN"},
                {"placeholder": "[IFSC]", "value": "KKBK0000214", "type": "IFSC"},
            ]
        ),

        # ==========================================
        # DOMAIN 3: TAX & PAYROLL (10 samples)
        # ==========================================
        make_sample(
            "tax_01", "tax_payroll",
            "Form 16 Part A: Employee PAN [PAN], Employer PAN [PAN_CORP].",
            [
                {"placeholder": "[PAN]", "value": "BNZPS2391L", "type": "PAN"},
                {"placeholder": "[PAN_CORP]", "value": "DELCA1298H", "type": "PAN"},
            ]
        ),
        make_sample(
            "tax_02", "tax_payroll",
            "Salary Slip Sept 2026: Gross Rs. 95,000 credited to IFSC [IFSC] for PAN [PAN].",
            [
                {"placeholder": "[IFSC]", "value": "PUNB0024900", "type": "IFSC"},
                {"placeholder": "[PAN]", "value": "CKLPS9012J", "type": "PAN"},
            ]
        ),
        make_sample(
            "tax_03", "tax_payroll",
            "ITR-1 Sahaj Acknowledgement: Taxpayer linked Aadhaar [AADHAAR] with mobile [PHONE].",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[7], "type": "AADHAAR"},
                {"placeholder": "[PHONE]", "value": "+91 97654 32109", "type": "PHONE"},
            ]
        ),
        make_sample(
            "tax_04", "tax_payroll",
            "Employee Provident Fund nomination: Aadhaar [AADHAAR] registered with UAN.",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[8], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "tax_05", "tax_payroll",
            "Direct tax challan 280: Self assessment payment by PAN [PAN] confirmed.",
            [
                {"placeholder": "[PAN]", "value": "EWMPS4512D", "type": "PAN"},
            ]
        ),
        make_sample(
            "tax_06", "tax_payroll",
            "Consultant retainer payout: Remitted via IFSC [IFSC] to individual PAN [PAN].",
            [
                {"placeholder": "[IFSC]", "value": "CNRB0001020", "type": "IFSC"},
                {"placeholder": "[PAN]", "value": "FKLPM7812G", "type": "PAN"},
            ]
        ),
        make_sample(
            "tax_07", "tax_payroll",
            "HR Onboarding: Verified Aadhaar [AADHAAR], PAN [PAN], and phone [PHONE].",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[9], "type": "AADHAAR"},
                {"placeholder": "[PAN]", "value": "GLKPS3412R", "type": "PAN"},
                {"placeholder": "[PHONE]", "value": "9819234567", "type": "PHONE"},
            ]
        ),
        make_sample(
            "tax_08", "tax_payroll",
            "Gratuity settlement advice: Bank account IFSC [IFSC] verified by finance.",
            [
                {"placeholder": "[IFSC]", "value": "UBIN0531201", "type": "IFSC"},
            ]
        ),
        make_sample(
            "tax_09", "tax_payroll",
            "Advance tax calculation query: Individual PAN [PAN] income slab assessment.",
            [
                {"placeholder": "[PAN]", "value": "HJLPS9041K", "type": "PAN"},
            ]
        ),
        make_sample(
            "tax_10", "tax_payroll",
            "Quarterly TDS Certificate: Deductee PAN [PAN] linked to phone [PHONE].",
            [
                {"placeholder": "[PAN]", "value": "JKLPS1290P", "type": "PAN"},
                {"placeholder": "[PHONE]", "value": "+91-91234-56780", "type": "PHONE"},
            ]
        ),

        # ==========================================
        # DOMAIN 4: E-COMMERCE & PAYMENTS (8 samples)
        # ==========================================
        make_sample(
            "ecom_01", "ecommerce",
            "Order #98124 refund of Rs 1,499 initiated to UPI [UPI].",
            [
                {"placeholder": "[UPI]", "value": "ananya.sharma@okaxis", "type": "UPI"},
            ]
        ),
        make_sample(
            "ecom_02", "ecommerce",
            "Delivery courier update: Delivery executive reaching via mobile [PHONE].",
            [
                {"placeholder": "[PHONE]", "value": "7890123456", "type": "PHONE"},
            ]
        ),
        make_sample(
            "ecom_03", "ecommerce",
            "Payment failed on gateway: Re-attempt payment with UPI [UPI].",
            [
                {"placeholder": "[UPI]", "value": "rohit99@okicici", "type": "UPI"},
            ]
        ),
        make_sample(
            "ecom_04", "ecommerce",
            "Merchant store settlement: Weekly payout transferred to IFSC [IFSC].",
            [
                {"placeholder": "[IFSC]", "value": "YESB0000101", "type": "IFSC"},
            ]
        ),
        make_sample(
            "ecom_05", "ecommerce",
            "Customer support dispute: Transaction ID TXN-9214 linked to VPA [UPI].",
            [
                {"placeholder": "[UPI]", "value": "support.pay@upi", "type": "UPI"},
            ]
        ),
        make_sample(
            "ecom_06", "ecommerce",
            "Cashback credited: Amount of Rs 250 sent to user mobile [PHONE].",
            [
                {"placeholder": "[PHONE]", "value": "+91 89012 34567", "type": "PHONE"},
            ]
        ),
        make_sample(
            "ecom_07", "ecommerce",
            "Vendor billing: Invoice generated under business PAN [PAN] with VPA [UPI].",
            [
                {"placeholder": "[PAN]", "value": "AABCF1209M", "type": "PAN"},
                {"placeholder": "[UPI]", "value": "vendor.hub@ibl", "type": "UPI"},
            ]
        ),
        make_sample(
            "ecom_08", "ecommerce",
            "Wallet top-up confirmation: Rs 5,000 deducted via UPI [UPI].",
            [
                {"placeholder": "[UPI]", "value": "deepak_k@oksbi", "type": "UPI"},
            ]
        ),

        # ==========================================
        # DOMAIN 5: CASUAL & KYC CHAT (4 samples)
        # ==========================================
        make_sample(
            "chat_01", "casual_chat",
            "Hey, you can GPay me the dinner money at [UPI] or call me on [PHONE].",
            [
                {"placeholder": "[UPI]", "value": "karthik.s@okaxis", "type": "UPI"},
                {"placeholder": "[PHONE]", "value": "+91 98490 12345", "type": "PHONE"},
            ]
        ),
        make_sample(
            "chat_02", "casual_chat",
            "Sending you my Aadhaar [AADHAAR] for hotel check-in booking.",
            [
                {"placeholder": "[AADHAAR]", "value": aadh[10], "type": "AADHAAR"},
            ]
        ),
        make_sample(
            "chat_03", "casual_chat",
            "Please send the rent via NEFT to IFSC [IFSC], let me know when done.",
            [
                {"placeholder": "[IFSC]", "value": "IDFB0040101", "type": "IFSC"},
            ]
        ),
        make_sample(
            "chat_04", "casual_chat",
            "HR asked for my PAN [PAN] and photo ID before Monday.",
            [
                {"placeholder": "[PAN]", "value": "MNKPS8912T", "type": "PAN"},
            ]
        ),

        # ==========================================
        # DOMAIN 6: NEGATIVE & DISTRACTOR SAMPLES (8 samples)
        # MUST HAVE ZERO DETECTED ENTITIES
        # ==========================================
        {
            "id": "neg_01",
            "domain": "distractor",
            "text": "Quarterly engineering sprint review at 10:30 AM on 15/10/2026 with 45 attendees. Target: 99.9% uptime.",
            "entities": [],
        },
        {
            "id": "neg_02",
            "domain": "distractor",
            "text": "Invalid Aadhaar test case 2679 0377 4207 (checksum mutated by 1) must be ignored by shield.",
            "entities": [],
        },
        {
            "id": "neg_03",
            "domain": "distractor",
            "text": "Contact our university placement office at coordinator@osmania.ac.in or support@pragyacyber.com.",
            "entities": [],
        },
        {
            "id": "neg_04",
            "domain": "distractor",
            "text": "Dummy string ABCXE1234F is not a PAN because 'X' is an invalid 4th taxpayer status character.",
            "entities": [],
        },
        {
            "id": "neg_05",
            "domain": "distractor",
            "text": "Invalid bank code SBIN1001234 is not an IFSC because the 5th character must be zero.",
            "entities": [],
        },
        {
            "id": "neg_06",
            "domain": "distractor",
            "text": "Please transfer payment to 16-digit debit card number 4111222233334444 (VISA test card).",
            "entities": [],
        },
        {
            "id": "neg_07",
            "domain": "distractor",
            "text": "Git commit SHA-1 hash a59d0dd1234567890abcdef1234567890abcdef1 pushed successfully to origin.",
            "entities": [],
        },
        {
            "id": "neg_08",
            "domain": "distractor",
            "text": "Server metrics: CPU load 18%, 1024MB allocated, response latency 24ms, HTTP 200 OK.",
            "entities": [],
        },
    ]

    return samples


def build_and_save_dataset(output_path: str = "data/samples_eval.json") -> List[Dict[str, Any]]:
    samples = generate_fifty_samples()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)
    return samples


if __name__ == "__main__":
    build_and_save_dataset()
