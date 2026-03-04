"""
Service layer for Bank Reconciliation (module T3).

Compliance (CLAUDE.md):
- Rule #2: AUDIT TRAIL — soft deletes only.
- Rule #4: CLIENT ISOLATION — every query filters by client_id
  (bank_accounts carry client_id; transactions inherit via bank_account_id).
- Rule #5: APPROVAL WORKFLOW — reconciliation completion requires CPA_OWNER.
- Rule #6: Role checks at function level (defense in depth).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.bank_account import BankAccount, BankTransaction, Reconciliation
from app.schemas.bank_reconciliation import (
    BankAccountCreate,
    BankAccountUpdate,
    BankTransactionCreate,
    ReconciliationCreate,
)


class BankAccountService:
    """CRUD for bank accounts scoped to a client."""

    @staticmethod
    async def create(
        db: AsyncSession,
        client_id: uuid.UUID,
        data: BankAccountCreate,
    ) -> BankAccount:
        account = BankAccount(
            client_id=client_id,
            account_name=data.account_name,
            institution_name=data.institution_name,
            account_id=data.account_id,
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
    ) -> BankAccount | None:
        stmt = select(BankAccount).where(
            BankAccount.id == bank_account_id,
            BankAccount.client_id == client_id,
            BankAccount.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[BankAccount], int]:
        base = select(BankAccount).where(
            BankAccount.client_id == client_id,
            BankAccount.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(BankAccount.account_name).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def update(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        data: BankAccountUpdate,
    ) -> BankAccount | None:
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)

        account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account

    @staticmethod
    async def soft_delete(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
    ) -> BankAccount | None:
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            return None

        account.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(account)
        return account


class BankTransactionService:
    """CRUD for bank statement transactions."""

    @staticmethod
    async def create(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        data: BankTransactionCreate,
    ) -> BankTransaction:
        # Verify bank account belongs to client
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        txn = BankTransaction(
            bank_account_id=bank_account_id,
            transaction_date=data.transaction_date,
            description=data.description,
            amount=data.amount,
            transaction_type=data.transaction_type.value,
        )
        db.add(txn)
        await db.flush()
        await db.refresh(txn)
        return txn

    @staticmethod
    async def bulk_import(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        transactions: list[BankTransactionCreate],
    ) -> list[BankTransaction]:
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        created = []
        for data in transactions:
            txn = BankTransaction(
                bank_account_id=bank_account_id,
                transaction_date=data.transaction_date,
                description=data.description,
                amount=data.amount,
                transaction_type=data.transaction_type.value,
            )
            db.add(txn)
            created.append(txn)

        await db.flush()
        for txn in created:
            await db.refresh(txn)
        return created

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        reconciled: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[BankTransaction], int]:
        # Verify bank account belongs to client
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        base = select(BankTransaction).where(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.deleted_at.is_(None),
        )

        if reconciled is not None:
            base = base.where(BankTransaction.is_reconciled == reconciled)
        if date_from is not None:
            base = base.where(BankTransaction.transaction_date >= date_from)
        if date_to is not None:
            base = base.where(BankTransaction.transaction_date <= date_to)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(
            BankTransaction.transaction_date.desc(),
            BankTransaction.created_at.desc(),
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total


class ReconciliationService:
    """Business logic for bank reconciliation sessions."""

    @staticmethod
    async def create(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        data: ReconciliationCreate,
    ) -> Reconciliation:
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        recon = Reconciliation(
            bank_account_id=bank_account_id,
            statement_date=data.statement_date,
            statement_balance=data.statement_balance,
        )
        db.add(recon)
        await db.flush()
        await db.refresh(recon)
        return recon

    @staticmethod
    async def get(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        reconciliation_id: uuid.UUID,
    ) -> Reconciliation | None:
        # Verify bank account belongs to client
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            return None

        stmt = select(Reconciliation).where(
            Reconciliation.id == reconciliation_id,
            Reconciliation.bank_account_id == bank_account_id,
            Reconciliation.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Reconciliation], int]:
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        base = select(Reconciliation).where(
            Reconciliation.bank_account_id == bank_account_id,
            Reconciliation.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = base.order_by(Reconciliation.statement_date.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def match_transaction(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
        journal_entry_id: uuid.UUID,
    ) -> BankTransaction:
        """Match a bank transaction to a journal entry (mark as reconciled)."""
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        stmt = select(BankTransaction).where(
            BankTransaction.id == bank_transaction_id,
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()

        if txn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank transaction not found",
            )

        if txn.is_reconciled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction is already reconciled",
            )

        txn.is_reconciled = True
        txn.reconciled_at = datetime.now(timezone.utc)
        txn.journal_entry_id = journal_entry_id
        txn.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(txn)
        return txn

    @staticmethod
    async def unmatch_transaction(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
    ) -> BankTransaction:
        """Unmatch a previously reconciled bank transaction."""
        account = await BankAccountService.get(db, client_id, bank_account_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found",
            )

        stmt = select(BankTransaction).where(
            BankTransaction.id == bank_transaction_id,
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        txn = result.scalar_one_or_none()

        if txn is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank transaction not found",
            )

        if not txn.is_reconciled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction is not reconciled",
            )

        txn.is_reconciled = False
        txn.reconciled_at = None
        txn.journal_entry_id = None
        txn.updated_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(txn)
        return txn

    @staticmethod
    async def complete(
        db: AsyncSession,
        client_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        reconciliation_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> Reconciliation:
        """
        Complete a reconciliation. CPA_OWNER only.

        Calculates the reconciled balance from matched transactions and
        compares to statement balance.

        Compliance (rule #5): Only CPA_OWNER can complete reconciliation.
        Compliance (rule #6): Role check at function level.
        """
        verify_role(current_user, "CPA_OWNER")

        recon = await ReconciliationService.get(
            db, client_id, bank_account_id, reconciliation_id,
        )
        if recon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reconciliation not found",
            )

        if recon.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reconciliation is already completed",
            )

        # Calculate reconciled balance from matched transactions
        stmt = select(func.coalesce(func.sum(
            case(
                (BankTransaction.transaction_type == "CREDIT", BankTransaction.amount),
                else_=-BankTransaction.amount,
            )
        ), 0)).where(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.is_reconciled.is_(True),
            BankTransaction.deleted_at.is_(None),
        )
        result = await db.execute(stmt)
        reconciled_balance = result.scalar_one()

        recon.reconciled_balance = reconciled_balance
        recon.status = "COMPLETED"
        recon.completed_at = datetime.now(timezone.utc)
        recon.completed_by = uuid.UUID(current_user.user_id)

        await db.flush()
        await db.refresh(recon)
        return recon
