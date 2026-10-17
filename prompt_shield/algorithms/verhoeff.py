"""
Verhoeff Checksum Algorithm Implementation.

The Verhoeff algorithm uses the dihedral group D5 to detect all single-digit errors
and all transposition errors involving two adjacent digits.
It is the official checksum algorithm used for Indian Aadhaar (12-digit) numbers.
"""

import random
from typing import Union

# Multiplication table d(j, k) based on dihedral group D5
D_TABLE = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

# Permutation table p(pos % 8, digit)
P_TABLE = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

# Inverse table inv(j)
INV_TABLE = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def clean_digits(number: Union[str, int]) -> str:
    """Normalize input by extracting only numeric characters."""
    raw = str(number).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits


def validate_verhoeff(number: Union[str, int]) -> bool:
    """
    Validate a number containing a Verhoeff check digit at its end.
    
    Returns True if the check digit is valid, False otherwise.
    """
    digits = clean_digits(number)
    if not digits:
        return False

    c = 0
    # Process digits from right to left (index 0 is the check digit)
    for i, ch in enumerate(reversed(digits)):
        digit = int(ch)
        p_val = P_TABLE[i % 8][digit]
        c = D_TABLE[c][p_val]

    return c == 0


def compute_verhoeff_checksum(base_number: Union[str, int]) -> int:
    """
    Compute the Verhoeff check digit for a given base number.
    
    The check digit will be appended at the end of base_number.
    """
    digits = clean_digits(base_number)
    if not digits:
        raise ValueError("Cannot compute checksum for an empty digit sequence.")

    c = 0
    # Process digits from right to left, starting at position 1
    # (since the check digit will occupy position 0)
    for i, ch in enumerate(reversed(digits), start=1):
        digit = int(ch)
        p_val = P_TABLE[i % 8][digit]
        c = D_TABLE[c][p_val]

    return INV_TABLE[c]


def generate_verhoeff_number(base_number: Union[str, int]) -> str:
    """
    Appends the Verhoeff check digit to the base number, returning a valid number.
    """
    digits = clean_digits(base_number)
    checksum = compute_verhoeff_checksum(digits)
    return f"{digits}{checksum}"


def validate_aadhaar(aadhaar: str) -> bool:
    """
    Validate an Indian Aadhaar number.
    
    Rules:
    - Exactly 12 numeric digits (ignoring spaces or hyphens)
    - First digit cannot be '0' or '1'
    - Must satisfy the Verhoeff checksum algorithm
    """
    cleaned = clean_digits(aadhaar)
    if len(cleaned) != 12:
        return False
    if cleaned[0] in ("0", "1"):
        return False
    return validate_verhoeff(cleaned)


def generate_valid_aadhaar(formatted: bool = False, seed: int = None) -> str:
    """
    Generate a random, format-valid synthetic 12-digit Aadhaar number with a valid Verhoeff checksum.
    
    UIDAI rules respected:
    - 12 digits
    - First digit in 2..9
    - Verhoeff check digit at index 11
    
    If formatted=True, returns in 'XXXX XXXX XXXX' format.
    """
    rng = random.Random(seed) if seed is not None else random
    # First digit must be 2..9
    first_digit = str(rng.randint(2, 9))
    # Next 10 digits can be 0..9
    middle_digits = "".join(str(rng.randint(0, 9)) for _ in range(10))
    base_11 = first_digit + middle_digits
    check_digit = compute_verhoeff_checksum(base_11)
    full_12 = f"{base_11}{check_digit}"

    if formatted:
        return f"{full_12[:4]} {full_12[4:8]} {full_12[8:]}"
    return full_12
