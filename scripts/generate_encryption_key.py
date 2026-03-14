#!/usr/bin/env python3
"""Generate a Fernet encryption key for PII encryption.

Run this once and add the output to your .env file as PII_ENCRYPTION_KEY.

Usage:
    python scripts/generate_encryption_key.py
"""

from cryptography.fernet import Fernet


def main() -> None:
    key = Fernet.generate_key().decode()
    print("Generated Fernet encryption key:")
    print(f"\nPII_ENCRYPTION_KEY={key}")
    print("\nAdd this to your .env file. Do NOT commit the .env file to git.")


if __name__ == "__main__":
    main()
