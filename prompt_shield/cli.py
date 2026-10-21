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
from prompt_shield.detectors import detect_all


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

    # Command: detect
    parser_det = subparsers.add_parser(
        "detect",
        help="Scan text or a text file and list detected Indian identifiers (Aadhaar, PAN, UPI, IFSC, Phone).",
    )
    parser_det.add_argument(
        "text",
        nargs="?",
        default=None,
        help="Raw text string to scan",
    )
    parser_det.add_argument(
        "-f", "--file",
        help="Path to text file to scan",
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

    # Command: inspect-vault
    parser_insp = subparsers.add_parser(
        "inspect-vault",
        help="Inspect mappings and statistics stored in a session vault JSON file.",
    )
    parser_insp.add_argument(
        "--vault", required=True, help="Path to session vault JSON file"
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

    elif args.command == "detect":
        target_text = ""
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    target_text = f.read()
            except Exception as e:
                print(f"[ERROR] Failed to read file: {e}", file=sys.stderr)
                return 1
        elif args.text:
            target_text = args.text
        else:
            print("[ERROR] Please provide either a text string or a --file path to scan.", file=sys.stderr)
            return 1

        matches = detect_all(target_text)
        if not matches:
            print("[INFO] No Indian personal identifiers detected.")
            return 0

        print(f"Found {len(matches)} identifier(s):")
        print("-" * 65)
        for idx, m in enumerate(matches, 1):
            detail = ", ".join(f"{k}={v}" for k, v in m.metadata.items())
            print(f"{idx}. [{m.entity_type}] '{m.value}' (span {m.start}:{m.end}) -> {detail}")
        print("-" * 65)
        return 0

    elif args.command == "mask":
        from pathlib import Path
        from prompt_shield.engine import SessionVault, mask_text

        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[ERROR] Input file not found: {args.input}", file=sys.stderr)
            return 1

        try:
            with open(in_path, "r", encoding="utf-8", newline="") as f:
                raw_text = f.read()
        except Exception as e:
            print(f"[ERROR] Could not read input file: {e}", file=sys.stderr)
            return 1

        # Load or create vault
        vault_path = Path(args.vault)
        if vault_path.exists():
            try:
                vault = SessionVault.load(str(vault_path))
            except Exception as e:
                print(f"[ERROR] Failed to load existing vault: {e}", file=sys.stderr)
                return 1
        else:
            vault = SessionVault()

        masked_text, vault, matches = mask_text(raw_text, vault=vault)

        # Write output file
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                f.write(masked_text)
        except Exception as e:
            print(f"[ERROR] Could not write output file: {e}", file=sys.stderr)
            return 1

        # Save updated vault
        try:
            vault.save(str(vault_path))
        except Exception as e:
            print(f"[ERROR] Could not save session vault: {e}", file=sys.stderr)
            return 1

        print(f"[SUCCESS] Masked {len(matches)} identifier(s).")
        print(f"Output written to: {args.output}")
        print(f"Session vault updated: {args.vault}")
        if matches:
            print("-" * 75)
            print(f"{'TYPE':<10} {'ORIGINAL VALUE':<26} {'SURROGATE VALUE':<26}")
            print("-" * 75)
            for m in matches:
                surrogate = vault.get_or_create_surrogate(m.entity_type, m.value)
                print(f"{m.entity_type:<10} {m.value:<26} {surrogate:<26}")
            print("-" * 75)
        return 0

    elif args.command == "unmask":
        from pathlib import Path
        from prompt_shield.engine import SessionVault, unmask_text

        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[ERROR] Input file not found: {args.input}", file=sys.stderr)
            return 1

        vault_path = Path(args.vault)
        if not vault_path.exists():
            print(f"[ERROR] Vault file not found: {args.vault}", file=sys.stderr)
            return 1

        try:
            with open(in_path, "r", encoding="utf-8", newline="") as f:
                masked_content = f.read()
        except Exception as e:
            print(f"[ERROR] Could not read input file: {e}", file=sys.stderr)
            return 1

        try:
            vault = SessionVault.load(str(vault_path))
        except Exception as e:
            print(f"[ERROR] Failed to load session vault: {e}", file=sys.stderr)
            return 1

        restored_text = unmask_text(masked_content, vault=vault)

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                f.write(restored_text)
        except Exception as e:
            print(f"[ERROR] Could not write restored output file: {e}", file=sys.stderr)
            return 1

        print(f"[SUCCESS] Reverse-mapping complete.")
        print(f"Restored file written to: {args.output}")
        return 0

    elif args.command == "inspect-vault":
        from prompt_shield.engine.vault import SessionVault
        try:
            vault = SessionVault.load(args.vault)
        except Exception as e:
            print(f"[ERROR] Failed to load session vault: {e}", file=sys.stderr)
            return 1

        entries = vault.get_all_entries()
        summary = vault.summary()
        print(f"Session Vault: {args.vault}")
        print(f"Total Unique Entities: {len(entries)}")
        print("Breakdown by Type:")
        for entity_type, count in sorted(summary.items()):
            print(f"  - {entity_type}: {count}")
        print("-" * 75)
        print(f"{'TYPE':<10} {'ORIGINAL VALUE':<26} {'SURROGATE VALUE':<26} {'COUNT':<5}")
        print("-" * 75)
        for e in entries:
            print(f"{e.entity_type:<10} {e.real_value:<26} {e.surrogate_value:<26} {e.occurrence_count:<5}")
        print("-" * 75)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
