# Prompt Shield — Technical Note (P1, Qualification Sprint)

**Author:** Karthik Somayajula · **Repository:** github.com/somayajula-karthik/prompt-shield

## 1. Problem

People paste salary slips, loan forms and discharge summaries into public AI assistants. The usual redaction approach replaces sensitive values with `XXXX` or `[REDACTED]`, which removes the structure the model needs, so the answers get worse. Most open-source PII tools also target US and EU formats and miss Indian identifiers. Prompt Shield instead replaces each Indian identifier with a **realistic, format-valid surrogate** before the text leaves the machine, and **maps the surrogates back** to the real values in the model's response.

## 2. Approach

```
input text ─► detectors ─► vault (real ↔ surrogate) ─► masked text ─► LLM
                                   │
user  ◄── restored text ◄── reverse mapper ◄──────────── LLM response
```

- **Detection** ([`detectors/`](../prompt_shield/detectors)). There are five detectors, each a boundary-guarded regex followed by a structural validator. `detect_all` merges their results and resolves overlaps by keeping the longest match.
- **Surrogate generation** ([`engine/generator.py`](../prompt_shield/engine/generator.py)). Each surrogate passes the same validator as a real value would, and copies the original's formatting (spaces, hyphens, `+91`, letter case).
- **Session vault** ([`engine/vault.py`](../prompt_shield/engine/vault.py)). A bidirectional map that guarantees *consistency* (one real value always gets the same surrogate, across turns) and *uniqueness* (two real values never share a surrogate). It persists to JSON so a session can continue later.
- **Masking and reverse mapping** ([`engine/mask.py`](../prompt_shield/engine/mask.py)). Replacements are applied from right to left so character offsets stay valid. Unmasking replaces surrogates longest-first. Files are read and written with `newline=""`, which makes the round trip **byte-identical**, CRLF line endings included.
- **Zero runtime dependencies.** Everything uses the Python standard library and runs locally, with no network calls.

| Identifier | Validation | Surrogate keeps |
|---|---|---|
| **Aadhaar** | 12 digits, first digit 2–9, **Verhoeff checksum** (dihedral group D₅) | Separator style; a valid check digit is recomputed |
| **PAN** | `AAAAA9999A`, 4th character in the ITD holder-type set, digits ≠ `0000` | Holder type (P/C/H/F…), case |
| **UPI VPA** | `user@handle`; known PSP handles accepted; email domains and TLDs rejected | PSP handle |
| **IFSC** | `AAAA0XXXXXX`, 5th character must be `0` | Bank prefix |
| **Mobile** | 10 digits starting 6–9; optional `+91`, `91` or `0`; repeated-digit strings rejected | Prefix and grouping |

## 3. Evaluation

The benchmark has **50 hand-built synthetic samples** in six domains: banking 10, healthcare 10, tax and payroll 10, e-commerce 8, casual chat 4, and **8 adversarial distractors**. They contain **64 annotated entities**. Every annotation is checked automatically so that `text[start:end] == value`. Matching is strict: the entity type, start offset and end offset must all agree.

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Aadhaar | 11 | 0 | 0 | 100% | 100% | 100% |
| PAN | 18 | 0 | 0 | 100% | 100% | 100% |
| IFSC | 11 | 0 | 0 | 100% | 100% | 100% |
| Phone | 15 | 0 | 0 | 100% | 100% | 100% |
| UPI | 9 | 0 | 0 | 100% | 100% | 100% |
| **Overall** | **64** | **0** | **0** | **100%** | **100%** | **100%** |

Reproduce with `python -m prompt_shield.cli eval`. The repository also has 45 unit tests, covering Verhoeff test vectors, single-digit and transposition detection, surrogate validity, vault persistence and round-trip fidelity.

**These numbers should not be read as real-world accuracy.** I wrote both the detectors and the benchmark, so the benchmark tests the formats I already expected. Adversarial probes ([`scripts/failure_probes.py`](../scripts/failure_probes.py)) found seven failure modes that the benchmark misses. They are summarised below and covered in full in [FAILURES.md](FAILURES.md).

## 4. Failures

1. **Reverse mapping breaks when the LLM reformats a surrogate.** Exact string matching fails when the model drops spaces, removes `+91`, or masks part of the number itself (`XXXX XXXX 8603`). The surrogate's last four digits are then shown to the user as if they were real. *Fix:* match on normalised forms, match unique suffixes, and flag any surrogate-shaped text that is left over.
2. **Detection ignores context.** Any 10-digit number starting 6–9 is treated as a phone number, so order IDs and account numbers get masked. **9.3% of random 12-digit numbers pass Verhoeff**, so 12-digit UTR references are sometimes masked as Aadhaar. *Fix:* adjust confidence using nearby keywords.
3. **Coverage gaps.** Names, dates of birth and addresses are never detected. Identifiers split by line breaks, double spaces or dots (common in PDF and OCR text) are missed. *Fix:* normalise whitespace before matching while keeping offsets, and add an on-device NER model.

## 5. Design trade-offs

- **Utility vs. privacy in surrogates.** Keeping the PAN holder type, IFSC bank prefix and UPI handle helps the model reason (individual vs. company, which bank), but it reveals a small amount about the real value. A future version should make each of these configurable.
- **Recall over precision for UPI.** Accepting unknown dot-less handles catches new payment providers, but it also flags strings like `deploy@buildserver`.
- **Vault security.** The vault currently stores real values as plain text on disk. That is acceptable for a CLI prototype but not for a product. It needs encryption at rest with a keychain-held key, and should be deleted when the session ends.

## 6. Next steps

1. Normalised and suffix-based reverse mapping. This is the most valuable fix, because the current behaviour shows the user wrong values without any warning.
2. Context-aware confidence scoring, plus numeric look-alikes in the negative test set.
3. On-device NER for names, places and dates, with culturally consistent name surrogates.
4. A benchmark written by someone other than the detector's author, including OCR noise and real LLM responses for the reverse-mapping step.
5. A browser extension that runs this pipeline on the chat input box and response stream, with a network trace showing that no real identifiers are sent.

## 7. Lessons learned

The checksum turned out to be the easy part. The hard parts were the edges of the problem: text the model rewrites, numbers that look like identifiers but aren't, and inputs nobody planned for. A benchmark you build yourself mostly confirms the assumptions you already had. The probe script found more about the tool's real weaknesses than the 100% score did.
