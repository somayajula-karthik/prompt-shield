# P1: Prompt Shield — Qualification Sprint Progress Report

**Program:** Pragya Cyber × Osmania University CCoE AI Security Internship (2026–27)  
**Project Code:** P1 — Prompt Shield  
**Author:** Somayajula Karthik  
**Date:** October 25, 2026  
**Repository:** [https://github.com/somayajula-karthik/prompt-shield](https://github.com/somayajula-karthik/prompt-shield)

---

## 1. Introduction

Public Large Language Models (LLMs) such as ChatGPT, Google Gemini, and Anthropic Claude are widely used across banking, healthcare, taxation, legal analysis, and software engineering. Users routinely paste raw operational documents—salary slips, tax filings, loan sanction letters, hospital discharge summaries, and KYC forms—directly into web-based AI assistants. Every prompt sent to a public cloud model crosses a trust boundary where personal identifiers may be logged, retained, or inspected.

**Prompt Shield (P1)** is a 100% local, zero-dependency privacy layer designed specifically for **Indian personal and financial identifiers**. Instead of redacting sensitive values with `[REDACTED]` or `XXXX` placeholders that destroy prompt semantics, Prompt Shield intercepts the input locally, replaces each identifier with a **format-valid, checksum-verified synthetic surrogate**, maintains conversational consistency across turns in a local **Session Vault**, and **silently restores the genuine identifiers** in the AI model's response before displaying it to the user.

---

## 2. Problem Statement

The use of public AI assistants on documents containing Indian personal data exposes three core challenges:

1. **Direct Leakage of Sensitive Indian Personal Data:**  
   Professionals and individuals paste documents containing **Aadhaar numbers**, **Permanent Account Numbers (PAN)**, **Unified Payments Interface (UPI) Virtual Payment Addresses**, **Indian Financial System Codes (IFSC)**, and **Indian mobile phone numbers** into cloud-hosted LLMs because not doing so means losing AI assistance altogether.
2. **The "Redaction Trap" (Loss of Prompt Utility):**  
   Traditional redaction tools replace identifiers and figures with static strings (`XXXX` or `[MASKED]`). When multiple entities in a loan application, tax computation, or medical summary are collapsed into `XXXX`, the language model loses entity identity, structural attributes (such as whether a PAN belongs to an Individual or a Company, or which bank an IFSC belongs to), and cross-entity relationships—producing degraded or incorrect answers.
3. **Lack of Indian Identifier & Checksum Coverage in Existing Tools:**  
   Existing open-source and enterprise DLP tools are built around US and EU formats (SSNs, IBANs, US phone numbers). They lack support for Indian specifications such as the **Verhoeff dihedral group $D_5$ checksum** used by 12-digit Aadhaar numbers, Income Tax Department (ITD) 4th-character taxpayer status codes for PAN cards, RBI 11-character IFSC codes, and NPCI UPI handles.

---

## 3. Approaches

Prompt Shield addresses these challenges through a five-stage technical approach:

### 3.1 Three-Layer Hybrid Detection Pipeline
1. **Layer 1 — Boundary-Guarded Syntactic Isolation:**  
   Lookaround regular expressions (`(?<!\d)...(?!\d)` and `(?<![A-Za-z0-9])...(?![A-Za-z0-9])`) isolate candidate spans cleanly without matching inside 16-digit card numbers, SHA-1 commit hashes, or sentence punctuation. Tolerance for OCR and PDF copy-paste artifacts allows detection across dot separators (`2679.0377.4206`), line-wrapped digit blocks (`2679 0377\n4206`), and character-spaced PAN cards (`B Z R P K 4 3 2 1 A`).
2. **Layer 2 — Mathematical & Official Specification Verification:**  
   - **Aadhaar (12 digits):** Enforces UIDAI starting-digit rules (`2–9`) and full **Verhoeff dihedral group $D_5$ checksum validation** (`D_TABLE`, `P_TABLE`, `INV_TABLE`).
   - **PAN (10 characters):** Enforces `[A-Z]{5}[0-9]{4}[A-Z]`, validates the 4th character against official ITD holder status codes (`P`, `C`, `H`, `F`, `A`, `T`, `B`, `L`, `J`, `G`), and rejects `0000` serial blocks.
   - **IFSC (11 characters):** Enforces `^[A-Z]{4}0[A-Z0-9]{6}$`, mandatory 5th character `'0'`, and enriches bank metadata against the published **RBI Scheduled Bank IFSC Registry** (`data/public_registries.json`).
   - **UPI VPA (`user@handle`):** Validates against 54+ official **NPCI Third-Party Application Provider (TPAP) & PSP Bank handles** (`@okhdfcbank`, `@oksbi`, `@ybl`, `@paytm`, `@tapicici`, etc.) while rejecting standard emails (`@gmail.com`, `@yahoo.com`) and DevOps/SSH hostnames (`deploy@buildserver`, `user@localhost`).
   - **Indian Mobile Numbers (10 digits):** Enforces DoT numbering rules (starting digits `6–9` with optional `+91`, `91`, or `0` prefixes) and rejects dummy repeat strings (`9999999999`).
3. **Layer 3 — Local Context-Window Disambiguation:**  
   Inspects a 30–40 character preceding window around unformatted numeric matches to suppress false positives on 10-digit Order IDs, Bank Account numbers, and Rupee amounts, as well as 12-digit NEFT/UTR references and bank account numbers that randomly satisfy the 1-in-10 Verhoeff check digit.

### 3.2 Domain-Preserving Surrogacy & Cross-Entity Coherence
- **Format-Valid Surrogates:** Surrogate Aadhaar numbers pass Verhoeff validation; surrogate PANs preserve the 4th-character taxpayer status (`P` for Individual, `C` for Company) and casing; surrogate IFSCs preserve the 4-letter bank prefix (`SBIN`, `HDFC`, `IDFB`); surrogate UPIs preserve the PSP handle; and surrogate names match regional language origin and character length using the Hugging Face **`adwaith06/indic-synthetic-profiles`** pool.
- **Cross-Entity Phone ↔ UPI Coherence:** When a user's UPI ID is formed from their mobile number (`9876543210` and `9876543210@paytm`), `SessionVault` links both surrogates so the UPI surrogate reuses the exact surrogate phone digits (`7982597919@paytm`).

### 3.3 Three-Tier Resilient Reverse-Mapping
When an AI assistant replies, `UnmaskingEngine` restores genuine values across three tiers:
- **Tier 1 (Exact Match):** Longest-first replacement of verbatim surrogates.
- **Tier 2 (Canonical Reformatted Match):** Restores surrogates even when the LLM strips spaces from an Aadhaar (`3868 5851 8603` → `386858518603`), drops `+91` from a phone number, or alters PAN/IFSC casing.
- **Tier 3 (Partial-Mask Suffix Match):** Restores partial LLM redactions (`XXXX XXXX 8603` → `XXXX XXXX 4206`) when the 4-digit suffix uniquely identifies a vault entry.

---

## 4. Progress Day Wise

All **14 commits** have been pushed across **8 separate calendar days** (`Oct 17, 19, 20, 21, 22, 23, 24, 25`) to [github.com/somayajula-karthik/prompt-shield](https://github.com/somayajula-karthik/prompt-shield):

| Sprint Day | Calendar Date | Commit Hash(es) | Work Completed | Cumulative Unit Tests |
| :---: | :---: | :---: | :--- | :---: |
| **Day 1** | `2026-10-17` | `0f3105b`, `a59d0dd` | Initialized repository structure, README, `.gitignore`, and implemented the **Verhoeff dihedral group $D_5$ checksum algorithm** (`verhoeff.py`), Aadhaar validator/generator, and CLI subcommands (`validate-aadhaar`, `generate-aadhaar`). | **8 / 8 PASS** |
| **Day 2** | `2026-10-19` | `722ea8e` | Designed `BaseDetector` and `Match` dataclasses (`base.py`), implemented **`AadhaarDetector`** (`aadhaar.py`) and **`PANDetector`** (`pan.py`) with ITD holder-type validation, and added CLI `detect`. | **15 / 15 PASS** |
| **Day 3** | `2026-10-20` | `9b4aa43` | Implemented **`UPIDetector`** (`upi.py`), **`IFSCDetector`** (`ifsc.py`), and **`PhoneDetector`** (`phone.py`), plus greedy longest-span overlap resolution in `detect_all()`. | **22 / 22 PASS** |
| **Day 4** | `2026-10-21` | `16bece0`, `06a3136` | Built **`SurrogateGenerator`** (`generator.py`), persistent bidirectional **`SessionVault`** (`vault.py`), and **`MaskingEngine` / `UnmaskingEngine`** (`mask.py`) with right-to-left offset splicing and byte-identical round-trip restoration (`mask`, `unmask`, `inspect-vault`). | **36 / 36 PASS** |
| **Day 5** | `2026-10-22` | `2172b09` | Constructed the **50-sample hand-labelled synthetic evaluation dataset** (`data/samples_eval.json`) via `builder.py` (42 positive samples with 64 entities across 5 domains + 8 negative distractors) and offset validator (`dataset.py`). | **42 / 42 PASS** |
| **Day 6** | `2026-10-23` | `3ebab29`, `7416dd0`, `4ec36e2`, `517284e` | Built the **Precision/Recall/$F_1$ evaluation harness** (`metrics.py`), authored the technical report (`docs/REPORT.md`), failure analysis (`docs/FAILURES.md`), and 7 adversarial probes (`scripts/failure_probes.py`), and hardened the engine with **3-tier resilient unmasking**, **context-window look-alike filtering**, and **Phone ↔ UPI surrogate coherence**. | **49 / 49 PASS** |
| **Day 7** | `2026-10-24` | `aba3bb1` | Added **OCR and PDF whitespace-tolerant detection** for dot-separated (`2679.0377.4206`), double-spaced, and line-wrapped (`2679 0377\n4206`) Aadhaar numbers, spaced PANs (`B Z R P K 4 3 2 1 A`), and mobile numbers. | **50 / 50 PASS** |
| **Day 8** | `2026-10-25` | `b3531c3`, `4dea9d3` | Integrated **public RBI IFSC & NPCI UPI registries** (`data/public_registries.json`), added the **Hugging Face `ai4privacy` evaluation corpus** (`data/hf_ai4privacy_indian_eval.json`), and downloaded & integrated **100 real multi-script Indian profiles from Hugging Face `adwaith06/indic-synthetic-profiles`** (`data/hf_indic_synthetic_profiles.json`, 500 entities across 8 Indian languages, achieving **100.0% Precision, Recall, and $F_1$**). | **55 / 55 PASS** |

---

## 5. Future Work to Be Done

In Phases 1–3 of the internship, we plan to extend Prompt Shield across six areas:

1. **Chrome / Firefox Manifest V3 Browser Extension:**  
   Embed the detection, substitution, and resilient reverse-mapping engine directly into ChatGPT, Claude, and Gemini web interfaces using content scripts, IndexedDB session vaults, and a real-time **Transparency Panel** showing every active substitution.
2. **On-Device NER for Unstructured PII (Names, Addresses, Dates of Birth):**  
   Integrate a quantized local transformer model (via ONNX Runtime Web / `transformers.js`) alongside the `adwaith06/indic-synthetic-profiles` regional vocabulary to detect unstructured person names and street addresses in real time.
3. **Additional Indian Identifiers (ABHA Health IDs & RTO Vehicle Numbers):**  
   Add detectors and format-valid surrogate generators for 14-digit Ayushman Bharat Health Account (ABHA) IDs and Indian vehicle registration numbers (`TS 09 EK 4321`).
4. **Band-Preserving Numerical Surrogacy for Salaries & Tax Figures:**  
   Perturb salary and income figures within the same Indian income-tax slab so tax calculations remain mathematically accurate while masking exact compensation amounts.
5. **Encrypted Session Vault at Rest:**  
   Encrypt persisted vault mappings using AES-GCM backed by an ephemeral session key or OS keychain integration, with automatic session expiry.
6. **Live Multi-Turn Browser Benchmark (100+ Conversations):**  
   Evaluate end-to-end round-trip fidelity and keystroke latency (`< 10 ms`) against live LLM responses using Playwright automation.

---

## 6. Conclusion

Across the 8-day Qualification Sprint, Prompt Shield has progressed from foundational mathematical checksum verification (Verhoeff dihedral group $D_5$) to a complete, resilient local CLI privacy layer covering five core Indian identifiers (**Aadhaar, PAN, UPI, IFSC, and Mobile Numbers**). Evaluated across **175 total benchmark samples**—our 50-sample self-constructed benchmark (`64` entities), 25-sample Hugging Face `ai4privacy` corpus (`61` entities), and 100 third-party multi-script profiles from Hugging Face `adwaith06/indic-synthetic-profiles` (`500` entities + `300` distractors)—Prompt Shield achieves **100.0% Precision, 100.0% Recall, and 100.0% $F_1$** across all **625 ground-truth entities** and **55 passing unit tests**, while transparently documenting and mitigating real-world adversarial edge cases.
