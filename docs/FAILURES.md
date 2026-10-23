# Failure Analysis — Prompt Shield (P1)

The detector scores 100% precision and recall on the 50-sample benchmark in `data/samples_eval.json`. **That number is optimistic.** I wrote the detectors and the benchmark, so the benchmark mostly contains the formats I had already thought of. To find out where the tool actually breaks, I wrote adversarial probes in [`scripts/failure_probes.py`](../scripts/failure_probes.py). Every failure below is copied from real output of that script, and every input is synthetic.

```bash
python scripts/failure_probes.py
```

---

## Failure 1 — Reverse mapping fails when the LLM reformats a surrogate

**Severity: High.** This is the step the brief calls "the hard part". When it fails, the user is quietly shown wrong information.

**Reproduction (Probe 1):**

```
MASKED PROMPT : Check KYC for Aadhaar 5016 6131 8603 and mobile +91 82601 81590.
  [verbatim                 ] -> 'Aadhaar 2679 0377 4206 is linked to +91 98765 43210.'  (restored correctly)
  [spaces dropped           ] -> 'Aadhaar 501661318603 is linked to 8260181590.'        (SURROGATE SHOWN TO USER)
  [partially redacted by LLM] -> 'Aadhaar XXXX XXXX 8603 is verified.'                  (SURROGATE SHOWN TO USER)
```

**Root cause.** [`UnmaskingEngine.unmask`](../prompt_shield/engine/mask.py) does an exact string replacement against the vault. It only works if the model repeats the surrogate exactly as it was sent. In practice, LLMs often:
- drop or change separators (`5016 6131 8603` → `501661318603`)
- remove the country code (`+91 82601 81590` → `8260181590`)
- mask part of the number themselves (`XXXX XXXX 8603`), out of their own privacy caution

In each case no match is found, so the surrogate goes through unchanged. The last case is the worst one. The user reads "ends in 8603", but their real Aadhaar ends in 4206. Nothing marks the output as wrong.

**Proposed fix.** Normalise before looking up. Keep a second index keyed by the canonical form of each surrogate (digits only for Aadhaar and phone, upper case for PAN and IFSC). Scan the response with the same detectors used on the input, normalise each hit, and look it up. For partial masks such as `XXXX XXXX 8603`, match on the last 4 digits only if exactly one vault entry of that type has that suffix. Also flag any leftover surrogate-shaped token to the user instead of passing it through silently.

---

## Failure 2 — Detection ignores context, so look-alike numbers become false positives

**Severity: Medium.** Wrongly masking a number damages the prompt (an order ID gets replaced with a random phone number), but nothing private leaks.

**Reproduction (Probes 2 and 3):**

```
INPUT : 'Order ID 9123456780 has shipped.'                       DETECT: [PHONE] '9123456780'
INPUT : 'Savings account number 7012345678 at the branch.'       DETECT: [PHONE] '7012345678'
INPUT : 'Invoice total Rs 8000000001 is a typo in the ledger.'   DETECT: [PHONE] '8000000001'

Random 12-digit numbers (first digit 2-9) passing Verhoeff: 928/10000 = 9.3%
INPUT : 'UTR reference 810033076661 for NEFT transfer.'          DETECT: [AADHAAR] '810033076661'
```

**Root cause.** Every detector decides from the token's shape alone and never reads the words around it.
- **Phone:** any 10-digit number starting with 6–9 matches. Indian order IDs, 10-digit bank account numbers and amounts often have that same shape.
- **Aadhaar:** the Verhoeff check digit catches typos, but it is not a strong filter. Probe 3 measured that **9.3% of random 12-digit numbers pass it** (the expected rate is 10%, since a check digit has 10 possible values). Bank UTR and transaction references are commonly 12 digits, so about 1 in 10 of them will be masked as Aadhaar.

The benchmark didn't catch this because its eight negative samples contain no 10-digit or 12-digit numbers in a non-PII context.

**Proposed fix.** Add a context-scoring step after the pattern match. Raise confidence when keywords such as "mobile", "call", "aadhaar" or "UID" appear within about 5 tokens. Lower it for "order", "account", "UTR", "ref", "invoice" or "Rs". Only mask above a tunable threshold. Add numeric look-alikes to the negative benchmark set so that this failure is measured from now on.

---

## Failure 3 — Coverage gaps: names and messy formatting pass through unmasked

**Severity: High for privacy.** These are false negatives, so real personal data reaches the model.

**Reproduction (Probes 4 and 6):**

```
INPUT : Patient Ramesh Rao, DOB 14/02/1961, resides at 12 MG Road, Hyderabad. Aadhaar 2679 0377 4206.
MASKED: Patient Ramesh Rao, DOB 14/02/1961, resides at 12 MG Road, Hyderabad. Aadhaar 4914 1777 6311.

INPUT : 'Aadhaar: 2679 0377\n4206'      DETECT: (nothing detected)
INPUT : 'PAN: BZRPK 4321 A'              DETECT: (nothing detected)
INPUT : 'Mobile: +91 98765  43210'       DETECT: (nothing detected)
INPUT : 'Aadhaar: 2679.0377.4206'        DETECT: (nothing detected)
```

**Root cause.**
1. **Scope:** the tool only detects five structured identifiers. Names, dates of birth and addresses are never detected. In the hospital example above, the Aadhaar is masked but the patient's name, date of birth and address are sent to the model as they are. Together those are enough to identify the person.
2. **Brittle regexes:** each pattern only accepts the separators I listed (one space or one hyphen). Text pasted from PDFs or OCR output often has line breaks, double spaces, dots or spaces between every character, and all of these get through.

**Proposed fix.** (a) Before running the regexes, collapse whitespace runs and allow `[\s.\-]{0,2}` between digit groups, while keeping a mapping back to the original character offsets so spans stay exact. (b) Add a small on-device NER model (e.g. a quantised Indic-NER) for `PERSON`, `LOCATION` and `DATE`. Use culturally consistent surrogate names from the existing `COMMON_FIRST_NAMES` and `COMMON_LAST_NAMES` pools in the generator.

---

## Other observed failures

| # | Failure | Evidence (from probes) | Root cause |
|---|---|---|---|
| 4 | Non-payment `user@host` strings are masked as UPI IDs | `deploy@buildserver`, `karthik@localhost` → `[UPI]` | [`UPIDetector`](../prompt_shield/detectors/upi.py) accepts any handle with no dot as a possible bank handle, so that new PSP handles are still caught. This trades precision for recall. |
| 5 | A UPI ID built from a phone number loses its link to that phone's surrogate | `Call 9876543210 or pay 9876543210@paytm.` → `Call 9259791907 or pay amit.616@paytm.` | Each entity gets its surrogate independently. The model can no longer tell that the VPA and the phone number belong to the same person, which weakens its reasoning. |
| 6 | The vault stores real identifiers in plain text | `session_vault.json` holds `real_value` in clear | No encryption at rest. Anyone who can read the file gets every real value. It should be encrypted with an OS-keychain-held key and deleted when the session ends. |
| 7 | Surrogates keep some real attributes on purpose | PAN 4th character, IFSC bank prefix and UPI handle are copied from the original | A deliberate utility-versus-privacy trade-off. It helps the model (individual vs company, which bank) but leaks a small amount of information about the real value. |

---

## What the benchmark does and does not show

- **It shows** that the detectors are correct on every format they were designed for, and on the eight distractor patterns I chose.
- **It does not show** how the tool performs on real-world text. The dataset and the detectors share the same author's assumptions. A fair next benchmark would be written by someone other than the detector's author, and would include OCR noise, numeric look-alikes and actual LLM responses for the reverse-mapping step.
