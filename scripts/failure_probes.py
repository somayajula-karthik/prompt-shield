"""
Adversarial failure probes for Prompt Shield.

Each probe feeds a deliberately difficult (fully synthetic) input to the tool and
prints what actually happens. These are the reproducible evidence behind
docs/FAILURES.md. Run from the repository root:

    python scripts/failure_probes.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prompt_shield.algorithms.verhoeff import validate_verhoeff  # noqa: E402
from prompt_shield.detectors import detect_all  # noqa: E402
from prompt_shield.engine import SessionVault, SurrogateGenerator, mask_text, unmask_text  # noqa: E402


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show(text: str) -> None:
    matches = detect_all(text)
    print(f"INPUT : {text!r}")
    if not matches:
        print("DETECT: (nothing detected)")
    for m in matches:
        print(f"DETECT: [{m.entity_type}] {m.value!r}")


def probe_reverse_mapping_reformat() -> None:
    header("PROBE 1 - Reverse mapping breaks when the LLM reformats a surrogate")
    vault = SessionVault(generator=SurrogateGenerator(seed=7))
    prompt = "Check KYC for Aadhaar 2679 0377 4206 and mobile +91 98765 43210."
    masked, vault, _ = mask_text(prompt, vault=vault)
    surr_aadhaar = vault.get_or_create_surrogate("AADHAAR", "2679 0377 4206")
    surr_phone = vault.get_or_create_surrogate("PHONE", "+91 98765 43210")
    print(f"MASKED PROMPT : {masked}")

    compact_aadhaar = surr_aadhaar.replace(" ", "")
    bare_phone = surr_phone.replace("+91 ", "").replace(" ", "")
    responses = {
        "verbatim": f"Aadhaar {surr_aadhaar} is linked to {surr_phone}.",
        "spaces dropped": f"Aadhaar {compact_aadhaar} is linked to {bare_phone}.",
        "partially redacted by LLM": f"Aadhaar XXXX XXXX {surr_aadhaar[-4:]} is verified.",
    }
    for label, resp in responses.items():
        restored = unmask_text(resp, vault)
        leaked = [s for s in (surr_aadhaar, compact_aadhaar, surr_phone, bare_phone, surr_aadhaar[-4:]) if s in restored]
        status = "SURROGATE SHOWN TO USER" if leaked else "restored correctly"
        print(f"  [{label:<26}] -> {restored!r}  ({status})")


def probe_phone_false_positives() -> None:
    header("PROBE 2 - Any 10-digit number starting 6-9 is treated as a phone number")
    for text in [
        "Order ID 9123456780 has shipped.",
        "Savings account number 7012345678 at the branch.",
        "Invoice total Rs 8000000001 is a typo in the ledger.",
    ]:
        show(text)


def probe_aadhaar_checksum_collisions() -> None:
    header("PROBE 3 - Random 12-digit numbers pass Verhoeff about 1 time in 10")
    rng = random.Random(2026)
    trials = 10_000
    passes = 0
    for _ in range(trials):
        candidate = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(11))
        if validate_verhoeff(candidate):
            passes += 1
    print(f"Random 12-digit numbers (first digit 2-9) passing Verhoeff: {passes}/{trials} = {passes / trials:.1%}")
    rng = random.Random(11)
    while True:
        candidate = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(11))
        if validate_verhoeff(candidate):
            break
    show(f"UTR reference {candidate} for NEFT transfer.")


def probe_split_and_noisy_formats() -> None:
    header("PROBE 4 - Identifiers split by line breaks or OCR-style spacing are missed")
    for text in [
        "Aadhaar: 2679 0377\n4206",
        "PAN: BZRPK 4321 A",
        "PAN: B Z R P K 4 3 2 1 A",
        "Mobile: +91 98765  43210",
        "Aadhaar: 2679.0377.4206",
    ]:
        show(text)


def probe_upi_heuristic() -> None:
    header("PROBE 5 - Unknown dot-less handles are assumed to be UPI IDs")
    for text in [
        "SSH into deploy@buildserver tonight.",
        "Ping me as karthik@localhost for the test mail.",
        "Pay vendor@newfintechbank for the invoice.",
    ]:
        show(text)


def probe_names_not_covered() -> None:
    header("PROBE 6 - Names, addresses and dates of birth pass through unmasked")
    text = "Patient Ramesh Rao, DOB 14/02/1961, resides at 12 MG Road, Hyderabad. Aadhaar 2679 0377 4206."
    masked, _, _ = mask_text(text, vault=SessionVault(generator=SurrogateGenerator(seed=1)))
    print(f"INPUT : {text}")
    print(f"MASKED: {masked}")


def probe_phone_inside_upi() -> None:
    header("PROBE 7 - Phone-number UPI IDs lose their link to the phone surrogate")
    vault = SessionVault(generator=SurrogateGenerator(seed=3))
    text = "Call 9876543210 or pay 9876543210@paytm."
    masked, vault, _ = mask_text(text, vault=vault)
    print(f"INPUT : {text}")
    print(f"MASKED: {masked}")


if __name__ == "__main__":
    probe_reverse_mapping_reformat()
    probe_phone_false_positives()
    probe_aadhaar_checksum_collisions()
    probe_split_and_noisy_formats()
    probe_upi_heuristic()
    probe_names_not_covered()
    probe_phone_inside_upi()
