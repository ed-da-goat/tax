"""
Fernet symmetric encryption for PII fields (SSN, tax_id, bank account numbers).

All PII is encrypted at the service layer boundary:
- On write: plaintext string -> Fernet token (stored as bytes in DB)
- On read: Fernet token (bytes from DB) -> plaintext string

The ENCRYPTION_KEY must be a valid Fernet key (base64-encoded 32 bytes).
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger("app.crypto")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-init the Fernet cipher from settings."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_pii(plaintext: str | None) -> bytes | None:
    """
    Encrypt a PII string using Fernet symmetric encryption.

    Returns the ciphertext as bytes (suitable for LargeBinary / BYTEA columns).
    Returns None if input is None or empty.
    """
    if not plaintext:
        return None
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_pii(ciphertext: bytes | None) -> str | None:
    """
    Decrypt a Fernet-encrypted PII value back to plaintext string.

    Returns None if input is None or empty.
    Logs a warning and returns None on decryption failure (e.g. key rotation).
    """
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt PII value — possible key mismatch or legacy data")
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string and return the ciphertext as a UTF-8 string (for TEXT columns)."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet token stored as a UTF-8 string."""
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
