"""PII encryption utilities.

Uses Fernet symmetric encryption to protect PII at rest in the database.
Fields with pii_level MEDIUM or HIGH are encrypted before storage and
decrypted on retrieval.

The encryption key is loaded from environment variables — never hardcoded.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from src.config.agent_config import PIILevel


def generate_key() -> str:
    """Generate a new Fernet encryption key.

    Run this once and store the result in your .env file as PII_ENCRYPTION_KEY.
    """
    return Fernet.generate_key().decode()


def encrypt_pii(value: str, key: str) -> str:
    """Encrypt a PII value using Fernet symmetric encryption.

    Args:
        value: The plaintext PII value.
        key: Fernet encryption key from environment.

    Returns:
        Base64-encoded encrypted string.
    """
    if not value or not key:
        return value
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(value.encode()).decode()


def decrypt_pii(encrypted_value: str, key: str) -> str:
    """Decrypt a PII value.

    Args:
        encrypted_value: The encrypted string.
        key: Fernet encryption key from environment.

    Returns:
        Decrypted plaintext string.

    Raises:
        InvalidToken: If the key is wrong or data is corrupted.
    """
    if not encrypted_value or not key:
        return encrypted_value
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(encrypted_value.encode()).decode()


def should_encrypt(pii_level: PIILevel) -> bool:
    """Determine whether a field should be encrypted based on its PII level.

    MEDIUM and HIGH PII fields are always encrypted at rest.
    LOW fields are not encrypted (e.g., company name — public info).
    NONE fields are never encrypted.
    """
    return pii_level in (PIILevel.MEDIUM, PIILevel.HIGH)
