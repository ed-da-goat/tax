"""
API router for Document Management (module D1).

Endpoints are scoped to /clients/{client_id}/documents.

Compliance (CLAUDE.md):
- Client isolation: client_id from URL path (rule #4).
- Soft deletes only (rule #2).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.document import DocumentList, DocumentResponse, DocumentUpdate
from app.services.document import DocumentService

router = APIRouter()


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (PDF or image)",
)
async def upload_document(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    description: str | None = Form(None),
    tags: str | None = Form(None, description="Comma-separated tags"),
    journal_entry_id: uuid.UUID | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a document tagged to a client. Both roles allowed."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    doc = await DocumentService.upload(
        db, client_id, file, user,
        description=description,
        tags=tag_list,
        journal_entry_id=journal_entry_id,
    )
    await db.commit()
    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=DocumentList,
    summary="List documents for a client",
)
async def list_documents(
    client_id: uuid.UUID,
    tags: str | None = Query(None, description="Comma-separated tags to filter by"),
    file_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentList:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    docs, total = await DocumentService.list(
        db, client_id, tags=tag_list, file_type=file_type, skip=skip, limit=limit,
    )
    return DocumentList(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
)
async def get_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentResponse:
    doc = await DocumentService.get(db, client_id, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/download",
    summary="Download the document file",
)
async def download_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    doc = await DocumentService.get(db, client_id, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = DocumentService.get_file_path(doc)
    import os
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk",
        )

    return FileResponse(
        path=file_path,
        filename=doc.file_name,
        media_type=doc.file_type or "application/octet-stream",
    )


@router.get(
    "/{document_id}/view",
    summary="View the document inline in browser (D2)",
)
async def view_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Serve the document for in-browser viewing (inline content-disposition)."""
    doc = await DocumentService.get(db, client_id, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = DocumentService.get_file_path(doc)
    import os
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk",
        )

    # Sanitize filename to prevent header injection (remove CR/LF/quotes)
    import re
    safe_filename = re.sub(r'[\r\n\x00"]', '', doc.file_name or "document")

    return FileResponse(
        path=file_path,
        media_type=doc.file_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename=\"{safe_filename}\""},
    )


@router.get(
    "/search",
    response_model=DocumentList,
    summary="Search documents by client, date, type, and text (D3)",
)
async def search_documents(
    client_id: uuid.UUID,
    q: str | None = Query(None, description="Search in file_name and description"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    file_type: str | None = Query(None),
    date_from: str | None = Query(None, description="Filter by upload date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter by upload date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentList:
    """Search documents with text, tag, type, and date filters (module D3)."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    from datetime import date as date_type
    d_from = date_type.fromisoformat(date_from) if date_from else None
    d_to = date_type.fromisoformat(date_to) if date_to else None

    docs, total = await DocumentService.search(
        db, client_id,
        query=q,
        tags=tag_list,
        file_type=file_type,
        date_from=d_from,
        date_to=d_to,
        skip=skip,
        limit=limit,
    )
    return DocumentList(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document metadata",
)
async def update_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentResponse:
    doc = await DocumentService.update(db, client_id, document_id, data)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.commit()
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Soft-delete a document",
)
async def delete_document(
    client_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> DocumentResponse:
    doc = await DocumentService.soft_delete(db, client_id, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.commit()
    return DocumentResponse.model_validate(doc)
