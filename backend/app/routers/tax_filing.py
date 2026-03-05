"""
API router for Tax E-Filing (Phase 8B).

Endpoints for managing tax filing submissions, including:
- CRUD for submission records
- TaxBandits integration (W-2, 1099-NEC, 941)
- Georgia FSET integration (G-7)

Compliance (CLAUDE.md):
- Rule #4: Client isolation via client_id path parameter.
- Rule #6: Filing submission requires CPA_OWNER (defense in depth).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.tax_filing import (
    TaxFilingCreate,
    TaxFilingList,
    TaxFilingResponse,
    TaxFilingUpdate,
)
from app.services.tax_filing.tax_filing_service import TaxFilingService

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filing_to_response(f) -> TaxFilingResponse:
    return TaxFilingResponse(
        id=f.id,
        created_at=f.created_at,
        updated_at=f.updated_at,
        client_id=f.client_id,
        form_type=f.form_type,
        tax_year=f.tax_year,
        tax_quarter=f.tax_quarter,
        filing_period_start=f.filing_period_start,
        filing_period_end=f.filing_period_end,
        provider=f.provider,
        provider_submission_id=f.provider_submission_id,
        provider_reference=f.provider_reference,
        status=f.status,
        submitted_at=f.submitted_at,
        accepted_at=f.accepted_at,
        rejected_at=f.rejected_at,
        rejection_reason=f.rejection_reason,
        submitted_by=f.submitted_by,
    )


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=TaxFilingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tax filing submission record (CPA_OWNER only)",
)
async def create_filing(
    client_id: uuid.UUID,
    data: TaxFilingCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> TaxFilingResponse:
    filing = await TaxFilingService.create(db, client_id, data, user)
    await db.commit()
    return _filing_to_response(filing)


@router.get(
    "",
    response_model=TaxFilingList,
    summary="List tax filing submissions for a client",
)
async def list_filings(
    client_id: uuid.UUID,
    form_type: str | None = Query(None),
    tax_year: int | None = Query(None),
    provider: str | None = Query(None),
    filing_status: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaxFilingList:
    filings, total = await TaxFilingService.list(
        db, client_id,
        form_type=form_type,
        tax_year=tax_year,
        provider=provider,
        status_filter=filing_status,
        skip=skip,
        limit=limit,
    )
    return TaxFilingList(
        items=[_filing_to_response(f) for f in filings],
        total=total,
    )


@router.get(
    "/{submission_id}",
    response_model=TaxFilingResponse,
    summary="Get a single tax filing submission",
)
async def get_filing(
    client_id: uuid.UUID,
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TaxFilingResponse:
    filing = await TaxFilingService.get(db, client_id, submission_id)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    return _filing_to_response(filing)


@router.patch(
    "/{submission_id}",
    response_model=TaxFilingResponse,
    summary="Update a tax filing submission (CPA_OWNER only)",
)
async def update_filing(
    client_id: uuid.UUID,
    submission_id: uuid.UUID,
    data: TaxFilingUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> TaxFilingResponse:
    filing = await TaxFilingService.update(db, client_id, submission_id, data, user)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    await db.commit()
    return _filing_to_response(filing)


@router.delete(
    "/{submission_id}",
    response_model=TaxFilingResponse,
    summary="Soft-delete a tax filing submission (CPA_OWNER only)",
)
async def delete_filing(
    client_id: uuid.UUID,
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> TaxFilingResponse:
    filing = await TaxFilingService.soft_delete(db, client_id, submission_id, user)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    await db.commit()
    return _filing_to_response(filing)
