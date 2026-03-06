#!/usr/bin/env python3
"""
One-time migration script: encrypt existing plaintext PII in the database.

Tables/columns affected:
- clients.tax_id_encrypted
- vendors.tax_id_encrypted
- employees.ssn_encrypted
- employee_bank_accounts.account_number_encrypted
- employee_bank_accounts.routing_number (new: stored as encrypted bytes)

Idempotent: skips rows that are already Fernet-encrypted (value starts with b'gAAAAA').
Runs inside a single transaction; rolls back on any error.

Usage:
    cd backend
    .venv/bin/python -m scripts.migrate_encrypt_pii
"""

import sys
import os

# Ensure backend/ is on the path so `app.*` imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from cryptography.fernet import Fernet

from app.config import settings


def is_already_encrypted(value: bytes | None) -> bool:
    """Check if a bytes value is already a Fernet token (starts with gAAAAA)."""
    if value is None:
        return True  # Nothing to encrypt
    if isinstance(value, memoryview):
        value = bytes(value)
    return value[:5] == b"gAAAAA"


def encrypt_value(fernet: Fernet, value: bytes | str | None) -> bytes | None:
    """Encrypt a plaintext value. Returns None if input is None."""
    if value is None:
        return None
    if isinstance(value, memoryview):
        value = bytes(value)
    if isinstance(value, bytes):
        plaintext = value.decode("utf-8", errors="replace")
    else:
        plaintext = str(value)
    return fernet.encrypt(plaintext.encode("utf-8"))


def migrate_table(
    cursor,
    fernet: Fernet,
    table: str,
    column: str,
    id_column: str = "id",
) -> int:
    """Encrypt all non-null, non-encrypted values in a table column."""
    cursor.execute(
        f"SELECT {id_column}, {column} FROM {table} WHERE {column} IS NOT NULL"
    )
    rows = cursor.fetchall()
    count = 0
    for row_id, raw_value in rows:
        if is_already_encrypted(raw_value):
            continue
        encrypted = encrypt_value(fernet, raw_value)
        cursor.execute(
            f"UPDATE {table} SET {column} = %s WHERE {id_column} = %s",
            (psycopg2.Binary(encrypted), row_id),
        )
        count += 1
    return count


def main() -> None:
    key = settings.ENCRYPTION_KEY
    if key == "CHANGE-ME-GENERATE-A-REAL-FERNET-KEY":
        print("ERROR: ENCRYPTION_KEY is not set. Configure it in .env first.")
        sys.exit(1)

    fernet = Fernet(key.encode())

    # Use synchronous psycopg2 for the migration
    db_url = settings.DATABASE_URL_SYNC
    # Parse SQLAlchemy URL to psycopg2 format
    # postgresql+psycopg2://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    dsn = db_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        cursor = conn.cursor()

        tables = [
            ("clients", "tax_id_encrypted"),
            ("vendors", "tax_id_encrypted"),
            ("employees", "ssn_encrypted"),
            ("employee_bank_accounts", "account_number_encrypted"),
        ]

        print("Encrypting existing PII data...")
        print("=" * 50)

        total = 0
        for table, column in tables:
            count = migrate_table(cursor, fernet, table, column)
            total += count
            print(f"  {table}.{column}: {count} rows encrypted")

        conn.commit()
        print("=" * 50)
        print(f"Done. {total} total rows encrypted.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: Migration failed, rolled back. {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
