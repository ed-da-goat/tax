"""
Transaction history importer for QuickBooks Online migration (module M4).

Imports parsed QBO transactions into the GL as journal entries. Uses the
CoA mapper (M3) to resolve accounts. Creates proper double-entry journal
entries from QBO's single-line transaction format.

This module writes to the database, creating journal entries and their
line items for each imported transaction.

Compliance (CLAUDE.md):
- Rule #1: DOUBLE-ENTRY — every journal entry has balanced debits/credits.
- Rule #2: AUDIT TRAIL — no hard deletes, all writes audited.
- Rule #4: CLIENT ISOLATION — all records tagged with client_id.
- Rule #5: APPROVAL — imported transactions are created as POSTED
           (historical data approved by CPA_OWNER during migration).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chart_of_accounts import ChartOfAccounts
from app.models.journal_entry import JournalEntry, JournalEntryLine

from .coa_mapper import MappedAccount
from .models import ParsedTransaction


@dataclass
class ImportedTransaction:
    """Record of a successfully imported transaction."""

    journal_entry_id: uuid.UUID
    original_transaction: ParsedTransaction
    account_name: str
    contra_account_name: str | None


@dataclass
class SkippedTransaction:
    """Record of a transaction that was skipped during import."""

    original: ParsedTransaction
    reason: str


@dataclass
class ImportResult:
    """Complete result of a transaction import operation."""

    imported: list[ImportedTransaction] = field(default_factory=list)
    skipped: list[SkippedTransaction] = field(default_factory=list)
    total_input: int = 0
    total_imported: int = 0
    total_skipped: int = 0


class TransactionImporter:
    """
    Imports QBO parsed transactions into the GL as journal entries.

    For each transaction, creates a journal entry with two lines:
    - Debit/Credit on the named account
    - Opposing entry on the split (contra) account

    QBO transactions use signed amounts:
    - Positive amount in a Bank account = DEBIT (increase)
    - Negative amount in a Bank account = CREDIT (decrease)
    - The 'Split' field indicates the contra account
    """

    def __init__(self, cpa_owner_user_id: str) -> None:
        self._cpa_owner_user_id = cpa_owner_user_id

    async def _resolve_account(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        account_name: str,
    ) -> uuid.UUID | None:
        """Look up an account ID by name for a given client."""
        stmt = select(ChartOfAccounts.id).where(
            ChartOfAccounts.client_id == client_id,
            ChartOfAccounts.account_name == account_name,
            ChartOfAccounts.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _resolve_account_fuzzy(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        account_name: str,
    ) -> uuid.UUID | None:
        """Look up an account ID by name with case-insensitive matching."""
        stmt = select(ChartOfAccounts.id).where(
            ChartOfAccounts.client_id == client_id,
            ChartOfAccounts.account_name.ilike(account_name),
            ChartOfAccounts.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def import_transactions(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        transactions: list[ParsedTransaction],
    ) -> ImportResult:
        """
        Import a list of parsed QBO transactions as journal entries.

        Parameters
        ----------
        db : AsyncSession
            Database session.
        client_id : uuid.UUID
            The client these transactions belong to.
        transactions : list[ParsedTransaction]
            Transactions from QBOParser.parse_transactions().

        Returns
        -------
        ImportResult
            Contains imported/skipped transactions and counts.
        """
        result = ImportResult(total_input=len(transactions))

        for txn in transactions:
            # Resolve the primary account
            account_id = await self._resolve_account(db, client_id, txn.account)
            if account_id is None:
                account_id = await self._resolve_account_fuzzy(db, client_id, txn.account)
            if account_id is None:
                result.skipped.append(SkippedTransaction(
                    original=txn,
                    reason=f"Account '{txn.account}' not found in chart of accounts",
                ))
                continue

            # Resolve the contra (split) account
            contra_account_id = None
            if txn.split and txn.split.strip() and txn.split.strip() != "-Split-":
                contra_account_id = await self._resolve_account(db, client_id, txn.split)
                if contra_account_id is None:
                    contra_account_id = await self._resolve_account_fuzzy(
                        db, client_id, txn.split,
                    )

            if contra_account_id is None:
                # If no contra account, skip (can't make a balanced entry)
                result.skipped.append(SkippedTransaction(
                    original=txn,
                    reason=f"Contra account '{txn.split}' not found or is a multi-split transaction",
                ))
                continue

            # Determine debit/credit based on amount sign
            abs_amount = abs(txn.amount)
            if abs_amount == Decimal("0"):
                result.skipped.append(SkippedTransaction(
                    original=txn,
                    reason="Zero amount transaction",
                ))
                continue

            # Create journal entry as DRAFT first (DB trigger prevents
            # inserting as POSTED without line items)
            je = JournalEntry(
                client_id=client_id,
                entry_date=txn.date,
                description=txn.memo or f"{txn.transaction_type}: {txn.name or 'Unknown'}",
                reference_number=txn.num,
                status="DRAFT",
                created_by=uuid.UUID(self._cpa_owner_user_id),
            )
            db.add(je)
            await db.flush()

            # Positive amount = debit the primary account, credit the contra
            # Negative amount = credit the primary account, debit the contra
            if txn.amount > 0:
                primary_debit = abs_amount
                primary_credit = Decimal("0.00")
                contra_debit = Decimal("0.00")
                contra_credit = abs_amount
            else:
                primary_debit = Decimal("0.00")
                primary_credit = abs_amount
                contra_debit = abs_amount
                contra_credit = Decimal("0.00")

            # Primary account line
            primary_line = JournalEntryLine(
                journal_entry_id=je.id,
                account_id=account_id,
                debit=primary_debit,
                credit=primary_credit,
                description=txn.memo or f"{txn.transaction_type}: {txn.name or ''}",
            )
            db.add(primary_line)

            # Contra account line
            contra_line = JournalEntryLine(
                journal_entry_id=je.id,
                account_id=contra_account_id,
                debit=contra_debit,
                credit=contra_credit,
                description=txn.memo or f"{txn.transaction_type}: {txn.name or ''}",
            )
            db.add(contra_line)

            await db.flush()

            # Now post the entry (lines exist, trigger will allow it)
            je.status = "POSTED"
            je.approved_by = uuid.UUID(self._cpa_owner_user_id)
            je.posted_at = datetime.now(timezone.utc)
            await db.flush()

            result.imported.append(ImportedTransaction(
                journal_entry_id=je.id,
                original_transaction=txn,
                account_name=txn.account,
                contra_account_name=txn.split,
            ))

        result.total_imported = len(result.imported)
        result.total_skipped = len(result.skipped)
        return result
