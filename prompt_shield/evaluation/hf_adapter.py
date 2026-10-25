"""
Adapter and corpus builder for Hugging Face public PII dataset schemas
(e.g., ai4privacy/pii-masking-300k and IndicNER span-annotation formats).

Maps public dataset entity labels (IN_AADHAAR, AADHAAR_NUMBER, IN_PAN, TAXNUM,
PHONENUMBER, TELEPHONENUM, IN_IFSC, IN_UPI, etc.) to Prompt Shield's canonical
5-class Indian identifier schema while computing exact character offsets.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from prompt_shield.detectors.base import Match
from prompt_shield.evaluation.dataset import EvalSample


# Mapping from Hugging Face / ai4privacy / Presidio / Indic PII labels to Prompt Shield types
HF_LABEL_MAP: Dict[str, str] = {
    "AADHAAR": "AADHAAR",
    "IN_AADHAAR": "AADHAAR",
    "AADHAAR_NUMBER": "AADHAAR",
    "UIDAI": "AADHAAR",
    "SOCIALSECURITYNUMBER": "AADHAAR",
    "PAN": "PAN",
    "IN_PAN": "PAN",
    "PAN_NUMBER": "PAN",
    "TAXNUM": "PAN",
    "UPI": "UPI",
    "IN_UPI": "UPI",
    "UPI_ID": "UPI",
    "VPA": "UPI",
    "IFSC": "IFSC",
    "IN_IFSC": "IFSC",
    "IFSC_CODE": "IFSC",
    "BANK_ROUTING": "IFSC",
    "PHONE": "PHONE",
    "IN_PHONE": "PHONE",
    "PHONENUMBER": "PHONE",
    "TELEPHONENUM": "PHONE",
    "MOBILE_NUMBER": "PHONE",
}


def from_hf_ai4privacy_record(record: dict, index: int = 0) -> EvalSample:
    """
    Convert a single Hugging Face ai4privacy-formatted record:
      {
        "uid": "hf_ind_01",
        "domain": "banking",
        "source_text": "...",
        "privacy_mask": [
          {"label": "IN_AADHAAR", "start": 10, "end": 24, "value": "2679 0377 4206"},
          ...
        ]
      }
    into a Prompt Shield EvalSample.
    """
    sample_id = str(record.get("uid") or record.get("id") or f"hf_sample_{index:02d}")
    domain = str(record.get("domain") or record.get("category") or "public_hf_corpus")
    source_text = str(record.get("source_text") or record.get("text") or "")
    mask_items = record.get("privacy_mask") or record.get("entities") or []

    entities: List[Match] = []
    for item in mask_items:
        raw_label = str(item.get("label") or item.get("entity_type") or "").upper().strip()
        mapped_type = HF_LABEL_MAP.get(raw_label)
        if not mapped_type:
            continue

        entities.append(
            Match(
                entity_type=mapped_type,
                start=int(item["start"]),
                end=int(item["end"]),
                value=str(item["value"]),
                confidence=1.0,
                metadata={"source_label": raw_label, "schema": "hf_ai4privacy"},
            )
        )

    return EvalSample(
        id=sample_id,
        domain=domain,
        text=source_text,
        entities=entities,
    )


def _compile_hf_template(
    uid: str,
    domain: str,
    template: str,
) -> dict:
    """
    Compiles a template containing {{HF_LABEL::VALUE}} placeholders into a
    Hugging Face ai4privacy-schema record with exact character offsets.
    """
    pattern = re.compile(r"\{\{([A-Z_]+)::(.*?)\}\}", re.DOTALL)
    clean_parts: List[str] = []
    privacy_mask: List[dict] = []

    last_idx = 0
    current_offset = 0

    for match in pattern.finditer(template):
        prefix = template[last_idx : match.start()]
        clean_parts.append(prefix)
        current_offset += len(prefix)

        hf_label = match.group(1)
        val = match.group(2)

        start_pos = current_offset
        end_pos = start_pos + len(val)
        clean_parts.append(val)
        current_offset = end_pos

        privacy_mask.append(
            {
                "label": hf_label,
                "start": start_pos,
                "end": end_pos,
                "value": val,
            }
        )
        last_idx = match.end()

    suffix = template[last_idx:]
    clean_parts.append(suffix)
    source_text = "".join(clean_parts)

    return {
        "uid": uid,
        "dataset_schema": "ai4privacy/pii-masking-indian-synthetic",
        "domain": domain,
        "source_text": source_text,
        "privacy_mask": privacy_mask,
    }


def build_hf_ai4privacy_indian_corpus() -> List[dict]:
    """
    Builds a 25-record held-out synthetic evaluation corpus formatted in the
    Hugging Face ai4privacy (`source_text` + `privacy_mask`) schema.
    Includes:
    - Expanded RBI/NPCI registry codes (IDFB, FDRL, AUBL, @ptsbi, @tapicici, @jupiteraxis)
    - OCR / PDF whitespace-corrupted Aadhaar, PAN, and Mobile tokens
    - Multi-turn conversational AI prompts
    - Negative look-alike distractors (UTR numbers, Order IDs, SSH hosts, emails)
    """
    raw_specs: List[Tuple[str, str, str]] = [
        (
            "hf_ind_01",
            "banking_kyc",
            "User: Please summarize this KYC note for IDFC FIRST branch {{IN_IFSC::IDFB0040101}}: customer UID {{IN_AADHAAR::2679 0377 4206}}, Tax ID {{TAXNUM::BZRPK4321A}}, and CRED Autopay VPA {{IN_UPI::vikram.rao@tapicici}}.",
        ),
        (
            "hf_ind_02",
            "ocr_scanned_pdf",
            "Extracted OCR from scanned PAN & Aadhaar card:\nUIDAI No: {{IN_AADHAAR::4415.9206.6111}}\nPermanent Account No: {{IN_PAN::A F K P R 8 9 1 2 K}}\nRegistered Cell: {{PHONENUMBER::+91 98765  43210}}",
        ),
        (
            "hf_ind_03",
            "ocr_scanned_pdf",
            "PDF Table Row 4: Applicant Aadhaar {{IN_AADHAAR::2679 0377\n4206}} | Block-spaced PAN {{IN_PAN::BZRPK 4321 A}} | Federal Bank IFSC {{IN_IFSC::FDRL0001422}}.",
        ),
        (
            "hf_ind_04",
            "upi_fintech",
            "Reconcile UPI settlements across Paytm {{IN_UPI::merchant.hyd@ptsbi}}, Jupiter {{IN_UPI::arjun.m@jupiteraxis}}, and MobiKwik {{IN_UPI::suresh88@ikwik}}.",
        ),
        (
            "hf_ind_05",
            "healthcare_ehr",
            "Discharge Summary — Patient Aadhaar {{AADHAAR_NUMBER::690934066215}}, Emergency Contact {{TELEPHONENUM::091234 56789}}, TPA Firm PAN {{IN_PAN::AAACF4321D}}, Refund Bank {{IN_IFSC::AUBL0002011}}.",
        ),
        (
            "hf_ind_06",
            "tax_audit",
            "Compare Section 80C deductions for HUF assessee {{TAXNUM::BZRHK5511E}} and Trust assessee {{TAXNUM::AABTT2299F}} holding account at Bandhan Bank {{IN_IFSC::BDBL0001599}}.",
        ),
        (
            "hf_ind_07",
            "multi_turn_chat",
            "Turn 1: Check loan eligibility for mobile {{PHONENUMBER::9876543210}} and Paytm VPA {{IN_UPI::9876543210@paytm}}.\nTurn 2: Also link Saraswat Co-op Bank IFSC {{IN_IFSC::SRCB0000123}}.",
        ),
        (
            "hf_ind_08",
            "payroll_compliance",
            "Form 16 Part B: Employee PAN {{IN_PAN::ghppk1122m}}, Aadhaar {{IN_AADHAAR::5857-0839-3474}}, Salary Credited to Karnataka Bank {{IN_IFSC::KARB0000210}}.",
        ),
        (
            "hf_ind_09",
            "ecommerce_refund",
            "Customer requested instant refund of Rs 2,499 to Navi UPI {{IN_UPI::neha.sharma@naviaxis}} or callback on {{PHONENUMBER::+91-87654-32109}}.",
        ),
        (
            "hf_ind_10",
            "rural_banking",
            "PM-KISAN beneficiary verification: Telangana Grameena Bank IFSC {{IN_IFSC::TGBI0000412}}, Aadhaar {{IN_AADHAAR::5016 6131 8603}}, Mobile {{PHONENUMBER::78901 23456}}.",
        ),
        (
            "hf_ind_11",
            "corporate_vendor",
            "Vendor onboarding for Company PAN {{IN_PAN::AAACB1234C}}, Local Authority PAN {{IN_PAN::AAJLM9988B}}, and India Post Payments Bank IFSC {{IN_IFSC::IPOS0000001}}.",
        ),
        (
            "hf_ind_12",
            "insurance_claim",
            "Motor claim settlement: Policyholder UID {{IN_AADHAAR::4952 8926 4966}}, Equitas Small Finance Bank {{IN_IFSC::ESFB0009001}}, WhatsApp Pay {{IN_UPI::claimant@wahdfc}}.",
        ),
        (
            "hf_ind_13",
            "legal_affidavit",
            "Deponent Aadhaar {{IN_AADHAAR::4914 1777 6311}} and PAN {{IN_PAN::DFRPP7744B}} verified before notary; contact number {{PHONENUMBER::+91 70123 45678}}.",
        ),
        (
            "hf_ind_14",
            "wealth_management",
            "CAMS consolidated statement for Folio linked to PAN {{IN_PAN::KLMPP3456Q}}, mobile {{PHONENUMBER::9988776655}}, and Standard Chartered IFSC {{IN_IFSC::SCBL0036001}}.",
        ),
        (
            "hf_ind_15",
            "education_scholarship",
            "National Scholarship Portal DBT record: Student Aadhaar {{IN_AADHAAR::9319 1675 1719}}, Ujjivan Bank IFSC {{IN_IFSC::UJVN0001122}}, FamPay VPA {{IN_UPI::rohit19@fam}}.",
        ),
        (
            "hf_ind_16",
            "telecom_kyc",
            "e-KYC SIM activation for subscriber {{PHONENUMBER::+91 63012 34567}} with Aadhaar {{IN_AADHAAR::2336 5020 2122}} and Airtel Payments Bank {{IN_UPI::sub6301@airtel}}.",
        ),
        (
            "hf_ind_17",
            "real_estate_tds",
            "Form 26QB property TDS challan: Buyer PAN {{IN_PAN::PQRPT6789L}}, Seller PAN {{IN_PAN::UVWPY1234Z}}, Remitter Bank IFSC {{IN_IFSC::COSB0000012}}.",
        ),
        (
            "hf_ind_18",
            "microfinance",
            "SHG loan ledger: Utkarsh Small Finance Bank {{IN_IFSC::UTKS0001050}}, Group Leader Aadhaar {{IN_AADHAAR::2679 0377 4206}}, Contact {{PHONENUMBER::81234 56789}}.",
        ),
        (
            "hf_ind_19",
            "upi_mandate",
            "Recurring IPO ASBA mandate via Slice {{IN_UPI::investor.hyd@slice}} and Amazon Pay {{IN_UPI::primeuser@rapl}} linked to PAN {{IN_PAN::MNBPC4321P}}.",
        ),
        (
            "hf_ind_20",
            "nri_remittance",
            "NRO account tax certificate: DBS Bank India {{IN_IFSC::DBSS0IN0811}}, Depositor PAN {{IN_PAN::ZXCPP9876K}}, Indian contact {{PHONENUMBER::+91 94401 23456}}.",
        ),
        # 5 Challenging Negative / Distractor Samples in Hugging Face schema
        (
            "hf_ind_21",
            "distractor_lookalike",
            "Order ID 9123456780 and NEFT UTR reference 810033076661 were billed for Rs 8000000001 on savings account number 7012345678.",
        ),
        (
            "hf_ind_22",
            "distractor_devops",
            "SSH into deploy@buildserver or ping karthik@localhost after pushing commit 7f8a9aabcp1234c99e12 to staging.",
        ),
        (
            "hf_ind_23",
            "distractor_invalid_checksum",
            "Rejected KYC test vectors: mutated Aadhaar 2679 0377 4207, invalid PAN ABCXE1234F, and malformed IFSC SBIN1001234.",
        ),
        (
            "hf_ind_24",
            "distractor_emails_and_cards",
            "Email billing@hdfcbank.com or support@osmania.ac.in regarding 16-digit card 9876543210123456.",
        ),
        (
            "hf_ind_25",
            "distractor_clinical_vitals",
            "Patient BP 120/80 mmHg, HbA1c 6.4%, fasting glucose 142 mg/dL, and dummy test line 9999999999.",
        ),
    ]

    return [_compile_hf_template(uid, domain, tpl) for uid, domain, tpl in raw_specs]


def save_hf_corpus(filepath: str = "data/hf_ai4privacy_indian_eval.json") -> List[dict]:
    records = build_hf_ai4privacy_indian_corpus()
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    return records


if __name__ == "__main__":
    saved = save_hf_corpus()
    print(f"Saved {len(saved)} Hugging Face ai4privacy-format records to data/hf_ai4privacy_indian_eval.json")
