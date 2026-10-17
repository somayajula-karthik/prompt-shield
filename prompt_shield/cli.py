"""
Prompt Shield Command Line Interface (CLI).
"""

import argparse
import sys
from prompt_shield import __version__
from prompt_shield.algorithms.verhoeff import (
    validate_aadhaar,
    generate_valid_aadhaar,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shield",
        description="Prompt Shield: Indian Identifier Detection, Masking & Reversal Engine.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: validate-aadhaar
    parser_val = subparsers.add_parser(
        "validate-aadhaar",
        help="Validate a 12-digit Indian Aadhaar number using the Verhoeff checksum algorithm.",
    )
    parser_val.add_argument(
        "aadhaar",
        type=str,
        help="Aadhaar number string to validate (e.g. '2345 6789 0123' or '234567890123')",
    )

    # Command: generate-aadhaar
    parser_gen = subparsers.add_parser(
        "generate-aadhaar",
        help="Generate a synthetic, format-valid 12-digit Aadhaar number with valid Verhoeff checksum.",
    )
    parser_gen.add_argument(
        "--formatted",
        action="store_true",
        help="Format output as 4-digit groups (XXXX XXXX XXXX)",
    )
    parser_gen.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of synthetic Aadhaar numbers to generate (default: 1)",
    )

    # Command: mask (placeholder for Day 5 integration)
    parser_mask = subparsers.add_parser(
        "mask",
        help="Mask Indian identifiers in an input file with format-valid surrogates.",
    )
    parser_mask.add_argument(
        "-i", "--input", required=True, help="Path to input text file"
    )
    parser_mask.add_argument(
        "-o", "--output", required=True, help="Path to output masked file"
    )
    parser_mask.add_argument(
        "--vault",
        default="vault.json",
        help="Path to session vault file (default: vault.json)",
    )

    # Command: unmask (placeholder for Day 5 integration)
    parser_unmask = subparsers.add_parser(
        "unmask",
        help="Unmask an AI assistant response file and restore original identifiers using session vault.",
    )
    parser_unmask.add_argument(
        "-i", "--input", required=True, help="Path to masked input file"
    )
    parser_unmask.add_argument(
        "--vault", required=True, help="Path to session vault JSON file"
    )
    parser_unmask.add_argument(
        "-o", "--output", required=True, help="Path to restored output file"
    )

    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "validate-aadhaar":
        is_valid = validate_aadhaar(args.aadhaar)
        if is_valid:
            print(f"[VALID] '{args.aadhaar}' is a format-valid Aadhaar with correct Verhoeff checksum.")
            return 0
        else:
            print(f"[INVALID] '{args.aadhaar}' is NOT a valid Aadhaar number.")
            return 1

    elif args.command == "generate-aadhaar":
        count = max(1, args.count)
        for _ in range(count):
            print(generate_valid_aadhaar(formatted=args.formatted))
        return 0

    elif args.command == "mask":
        print("[INFO] Full masking engine scheduled for Day 5 per timeline.")
        return 0

    elif args.command == "unmask":
        print("[INFO] Full reverse mapping engine scheduled for Day 5 per timeline.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
