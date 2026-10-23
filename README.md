# Prompt Shield (P1)

> **Use AI assistants without giving them your personal data.**

Prompt Shield is a local privacy-preserving shield that intercepts text before it is submitted to AI assistants (ChatGPT, Claude, Gemini, etc.), detects sensitive Indian personal identifiers, substitutes them with realistic, format-valid surrogates, and provides exact reverse-mapping to restore genuine values into the model's response.

Built for the **Pragya Cyber × Osmania University CCoE AI Security Internship (2026–27)** Qualification Sprint.

---

## The Problem

Millions of users paste sensitive documents into AI models daily—salary slips, financial statements, loan applications, and identification documents containing Aadhaar, PAN, and UPI IDs. Existing redaction tools replace sensitive tokens with placeholders like `XXXX` or `[REDACTED]`, destroying the linguistic and contextual structure of the prompt and resulting in degraded or useless AI responses.

**Prompt Shield solves this through coherent, format-valid surrogate substitution:**
- Replaces identifiers with realistic fake counterparts that pass strict format and checksum validation.
- Preserves context and semantics across multi-turn conversations.
- Restores original values locally on response delivery without transmitting any personal data.

---

## Key Features

1. **Format-Valid Indian Identifier Detection & Surrogacy:**
   - **Aadhaar Numbers**: Validated and synthesized using the **Verhoeff algorithm** (dihedral group $D_5$ checksum).
   - **PAN (Permanent Account Number)**: 10-character alphanumeric structure with category indicators (`P` for individuals) and matching initials.
   - **UPI ID / VPA**: Authentic Indian payment handle detection and valid surrogate handle generation (`@okhdfcbank`, `@oksbi`, `@paytm`, etc.).
   - **IFSC Codes**: Valid RBI bank prefixes with formatted branch designations.
   - **Indian Mobile Numbers**: 10-digit formats starting with 6–9 with optional `+91` or `0` international dialing prefixes.

2. **Session Vault & Consistency:**
   - Maintains bidirectional mappings ($Real \leftrightarrow Surrogate$) so the same entity is substituted consistently throughout the text and across conversational turns.

3. **Zero-Leakage Architecture:**
   - Designed to run 100% locally on-device. No telemetry, no external API calls, zero dependencies required for core execution.

---

## Project Structure

```
prompt_shield/
├── __init__.py
├── cli.py                     # CLI commands (mask, unmask, validate-aadhaar, eval)
├── algorithms/
│   ├── __init__.py
│   └── verhoeff.py            # Verhoeff checksum algorithm (multiplication, permutation, inverse)
├── detectors/
│   ├── __init__.py
│   ├── base.py                # Base detector contract
│   ├── aadhaar.py             # Aadhaar detector + Verhoeff validator
│   ├── pan.py                 # PAN structure detector
│   ├── upi.py                 # UPI ID / VPA detector
│   ├── ifsc.py                # IFSC code detector
│   └── phone.py               # Indian mobile phone detector
├── engine/
│   ├── __init__.py
│   ├── generator.py           # Format-valid surrogate generator
│   ├── vault.py               # Bidirectional session mapping store
│   └── mask.py                # Masking and reverse restoration engine
└── evaluation/
    ├── __init__.py
    ├── dataset.py             # 50 synthetic test samples
    └── metrics.py             # Precision, recall, and F1 scoring
```

---

## Quickstart

### Prerequisites
- Python 3.9+ (Zero third-party dependencies needed for core execution)
- `pytest` (optional, for running tests)

```bash
# Clone the repository
git clone https://github.com/<your-username>/prompt-shield.git
cd prompt-shield

# (Optional) Install development dependencies
pip install -r requirements.txt
```

### Basic Usage

#### 1. Validate an Aadhaar Number using Verhoeff Checksum
```bash
python -m prompt_shield.cli validate-aadhaar "2679 0377 4206"
```

#### 2. Detect Indian Identifiers in Text or Documents
```bash
python -m prompt_shield.cli detect "Client phone: +91 98765 43210, Aadhaar: 2679 0377 4206, PAN: BZRPK4321A, IFSC: SBIN0001234, UPI: user@oksbi"
# Or scan a file:
python -m prompt_shield.cli detect --file document.txt
```

#### 3. Mask Sensitive Identifiers in a Document
```bash
python -m prompt_shield.cli mask --input input.txt --output masked.txt --vault session_vault.json
```

#### 4. Unmask and Restore Real Values from AI Response
```bash
python -m prompt_shield.cli unmask --input ai_response.txt --vault session_vault.json --output restored.txt
```

#### 5. Inspect Session Vault Mappings
```bash
python -m prompt_shield.cli inspect-vault --vault session_vault.json
```

#### 6. Inspect & Validate Synthetic Evaluation Dataset
```bash
python -m prompt_shield.cli inspect-dataset --dataset data/samples_eval.json
```

#### 7. Run Precision & Recall Benchmark Evaluation
```bash
python -m prompt_shield.cli eval --dataset data/samples_eval.json -o data/eval_report.json
```

---

## Documentation

| Document | Contents |
|---|---|
| [docs/REPORT.md](docs/REPORT.md) | Two-page technical note: approach, evaluation, trade-offs, next steps |
| [docs/FAILURES.md](docs/FAILURES.md) | Failure analysis with reproducible evidence and root causes |
| [docs/DEMO.md](docs/DEMO.md) | 10-minute live demo script |
| [scripts/failure_probes.py](scripts/failure_probes.py) | Adversarial probes that reproduce every documented failure |

```bash
python scripts/failure_probes.py
```

---

## Running Unit Tests

```bash
python -m unittest discover tests/
# or with pytest
pytest tests/ -v
```

---

## Responsible Research Policy

In adherence to Section 8 of the project brief:
- **Zero Real Personal Data**: All test data, evaluation corpora, and demonstration inputs are 100% synthesized. No real individual's personal identifiers are ever used or committed.
- **Local Processing**: All detection and transformation logic operates entirely in-memory and on local disk.
