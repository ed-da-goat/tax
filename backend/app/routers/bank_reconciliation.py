"""
API router for Bank Reconciliation (module T3).

Endpoints are scoped to /clients/{client_id}/bank-accounts.

Compliance (CLAUDE.md):
- Client isolation: client_id from URL path (rule #4).
- Role enforcement: CPA_OWNER required for completing reconciliation (rule #5, #6).
- Soft deletes only (rule #2).
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.bank_reconciliation import (
    BankAccountCreate,
    BankAccountList,
    BankAccountResponse,
    BankAccountUpdate,
    BankTransactionCreate,
    BankTransactionImport,
    BankTransactionList,
    BankTransactionResponse,
    ReconciliationCreate,
    ReconciliationList,
    ReconciliationMatchRequest,
    ReconciliationResponse,
)
from app.services.bank_reconciliation import (
    BankAccountService,
    BankTransactionService,
    ReconciliationService,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Bank Accounts
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bank account for a client",
)
async def create_bank_account(
    client_id: uuid.UUID,
    data: BankAccountCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankAccountResponse:
    account = await BankAccountService.create(db, client_id, data)
    await db.commit()
    return BankAccountResponse.model_validate(account)


@router.get(
    "",
    response_model=BankAccountList,
    summary="List bank accounts for a client",
)
async def list_bank_accounts(
    client_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankAccountList:
    accounts, total = await BankAccountService.list(db, client_id, skip, limit)
    return BankAccountList(
        items=[BankAccountResponse.model_validate(a) for a in accounts],
        total=total,
    )


@router.get(
    "/{bank_account_id}",
    response_model=BankAccountResponse,
    summary="Get a bank account",
)
async def get_bank_account(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankAccountResponse:
    account = await BankAccountService.get(db, client_id, bank_account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    return BankAccountResponse.model_validate(account)


@router.patch(
    "/{bank_account_id}",
    response_model=BankAccountResponse,
    summary="Update a bank account",
)
async def update_bank_account(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    data: BankAccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankAccountResponse:
    account = await BankAccountService.update(db, client_id, bank_account_id, data)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    await db.commit()
    return BankAccountResponse.model_validate(account)


@router.delete(
    "/{bank_account_id}",
    response_model=BankAccountResponse,
    summary="Soft-delete a bank account",
)
async def delete_bank_account(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> BankAccountResponse:
    account = await BankAccountService.soft_delete(db, client_id, bank_account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found")
    await db.commit()
    return BankAccountResponse.model_validate(account)


# ---------------------------------------------------------------------------
# Bank Transactions
# ---------------------------------------------------------------------------

@router.post(
    "/{bank_account_id}/transactions",
    response_model=BankTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a single bank transaction",
)
async def create_bank_transaction(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    data: BankTransactionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankTransactionResponse:
    txn = await BankTransactionService.create(db, client_id, bank_account_id, data)
    await db.commit()
    return BankTransactionResponse.model_validate(txn)


@router.post(
    "/{bank_account_id}/transactions/import",
    response_model=BankTransactionList,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk import bank statement transactions",
)
async def import_bank_transactions(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    data: BankTransactionImport,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankTransactionList:
    txns = await BankTransactionService.bulk_import(
        db, client_id, bank_account_id, data.transactions,
    )
    await db.commit()
    return BankTransactionList(
        items=[BankTransactionResponse.model_validate(t) for t in txns],
        total=len(txns),
    )


@router.get(
    "/{bank_account_id}/transactions",
    response_model=BankTransactionList,
    summary="List bank transactions for an account",
)
async def list_bank_transactions(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    reconciled: bool | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankTransactionList:
    txns, total = await BankTransactionService.list(
        db, client_id, bank_account_id,
        reconciled=reconciled,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return BankTransactionList(
        items=[BankTransactionResponse.model_validate(t) for t in txns],
        total=total,
    )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

@router.post(
    "/{bank_account_id}/reconciliations",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new reconciliation session",
)
async def create_reconciliation(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    data: ReconciliationCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReconciliationResponse:
    recon = await ReconciliationService.create(db, client_id, bank_account_id, data)
    await db.commit()
    return ReconciliationResponse.model_validate(recon)


@router.get(
    "/{bank_account_id}/reconciliations",
    response_model=ReconciliationList,
    summary="List reconciliation sessions",
)
async def list_reconciliations(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReconciliationList:
    recons, total = await ReconciliationService.list(
        db, client_id, bank_account_id, skip, limit,
    )
    return ReconciliationList(
        items=[ReconciliationResponse.model_validate(r) for r in recons],
        total=total,
    )


@router.get(
    "/{bank_account_id}/reconciliations/{reconciliation_id}",
    response_model=ReconciliationResponse,
    summary="Get a reconciliation session",
)
async def get_reconciliation(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    reconciliation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ReconciliationResponse:
    recon = await ReconciliationService.get(
        db, client_id, bank_account_id, reconciliation_id,
    )
    if recon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reconciliation not found")
    return ReconciliationResponse.model_validate(recon)


@router.post(
    "/{bank_account_id}/transactions/{bank_transaction_id}/match",
    response_model=BankTransactionResponse,
    summary="Match a bank transaction to a journal entry",
)
async def match_transaction(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    bank_transaction_id: uuid.UUID,
    data: ReconciliationMatchRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankTransactionResponse:
    txn = await ReconciliationService.match_transaction(
        db, client_id, bank_account_id,
        bank_transaction_id=data.bank_transaction_id,
        journal_entry_id=data.journal_entry_id,
    )
    await db.commit()
    return BankTransactionResponse.model_validate(txn)


@router.post(
    "/{bank_account_id}/transactions/{bank_transaction_id}/unmatch",
    response_model=BankTransactionResponse,
    summary="Unmatch a reconciled bank transaction",
)
async def unmatch_transaction(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    bank_transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> BankTransactionResponse:
    txn = await ReconciliationService.unmatch_transaction(
        db, client_id, bank_account_id, bank_transaction_id,
    )
    await db.commit()
    return BankTransactionResponse.model_validate(txn)


@router.post(
    "/{bank_account_id}/reconciliations/{reconciliation_id}/complete",
    response_model=ReconciliationResponse,
    summary="Complete a reconciliation (CPA_OWNER only)",
)
async def complete_reconciliation(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID,
    reconciliation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> ReconciliationResponse:
    recon = await ReconciliationService.complete(
        db, client_id, bank_account_id, reconciliation_id, user,
    )
    await db.commit()
    return ReconciliationResponse.model_validate(recon)
