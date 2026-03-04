"""
Vendor management API endpoints (Module T1 — Accounts Payable).

Endpoints:
    POST   /api/v1/clients/{client_id}/vendors       — Create vendor
    GET    /api/v1/clients/{client_id}/vendors       — List vendors
    GET    /api/v1/clients/{client_id}/vendors/{id}  — Get single vendor
    PUT    /api/v1/clients/{client_id}/vendors/{id}  — Update vendor
    DELETE /api/v1/clients/{client_id}/vendors/{id}  — Archive/soft-delete vendor

Compliance (CLAUDE.md):
- Client isolation: all queries scoped by client_id from URL path.
- Soft deletes only — DELETE sets deleted_at, never removes the row.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.vendor import VendorCreate, VendorList, VendorResponse, VendorUpdate
from app.services.vendor import VendorService

router = APIRouter()


@router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vendor(
    client_id: UUID,
    data: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> VendorResponse:
    """Create a new vendor for a client. Both roles."""
    vendor = await VendorService.create_vendor(db, client_id, data)
    return VendorResponse.model_validate(vendor)


@router.get("", response_model=VendorList)
async def list_vendors(
    client_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> VendorList:
    """List vendors for a client with optional name search. Both roles."""
    vendors, total = await VendorService.list_vendors(
        db, client_id, skip=skip, limit=limit, search=search
    )
    return VendorList(
        items=[VendorResponse.model_validate(v) for v in vendors],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    client_id: UUID,
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> VendorResponse:
    """Get a single vendor by ID. Both roles."""
    vendor = await VendorService.get_vendor(db, client_id, vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return VendorResponse.model_validate(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    client_id: UUID,
    vendor_id: UUID,
    data: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> VendorResponse:
    """Update an existing vendor. Both roles."""
    vendor = await VendorService.update_vendor(db, client_id, vendor_id, data)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return VendorResponse.model_validate(vendor)


@router.delete("/{vendor_id}", response_model=VendorResponse)
async def archive_vendor(
    client_id: UUID,
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> VendorResponse:
    """
    Soft-delete (archive) a vendor. Both roles.

    Compliance: Sets deleted_at timestamp. Never hard-deletes.
    """
    vendor = await VendorService.archive_vendor(db, client_id, vendor_id)
    if vendor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return VendorResponse.model_validate(vendor)
