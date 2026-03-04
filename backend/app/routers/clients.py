"""
Client management API endpoints (Module F4).

Endpoints:
    POST   /api/v1/clients       — Create client (CPA_OWNER only)
    GET    /api/v1/clients       — List clients (both roles)
    GET    /api/v1/clients/{id}  — Get single client (both roles)
    PUT    /api/v1/clients/{id}  — Update client (CPA_OWNER only)
    DELETE /api/v1/clients/{id}  — Archive/soft-delete client (CPA_OWNER only)

Compliance (CLAUDE.md):
- Role checks at both route level (require_role dependency) AND
  function/service level (verify_role call inside service methods).
- Soft deletes only — DELETE sets deleted_at, never removes the row.
- All list/get endpoints filter out soft-deleted records.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.models.client import EntityType
from app.schemas.client import (
    ClientCreate,
    ClientList,
    ClientResponse,
    ClientUpdate,
)
from app.services.client import ClientService

router = APIRouter()


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> ClientResponse:
    """Create a new client. CPA_OWNER only."""
    client = await ClientService.create_client(db, data, current_user)
    return ClientResponse.model_validate(client)


@router.get("", response_model=ClientList)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_type: EntityType | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ClientList:
    """List all active clients with optional filters. Both roles."""
    clients, total = await ClientService.list_clients(
        db, skip=skip, limit=limit, entity_type=entity_type, is_active=is_active
    )
    return ClientList(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ClientResponse:
    """Get a single client by ID. Both roles."""
    client = await ClientService.get_client(db, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    data: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> ClientResponse:
    """Update an existing client. CPA_OWNER only."""
    client = await ClientService.update_client(db, client_id, data, current_user)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", response_model=ClientResponse)
async def archive_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> ClientResponse:
    """
    Soft-delete (archive) a client. CPA_OWNER only.

    Compliance: Sets deleted_at timestamp. Never hard-deletes.
    """
    client = await ClientService.archive_client(db, client_id, current_user)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return ClientResponse.model_validate(client)
