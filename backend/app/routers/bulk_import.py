"""
API router for bulk CSV imports (E3).

Endpoints:
- POST /clients/{id}/import/bills     — import bills from CSV
- POST /clients/{id}/import/invoices  — import invoices from CSV
- GET  /import/template/{type}        — download CSV template
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.services.bulk_import import BulkImportService

router = APIRouter()


@router.post("/clients/{client_id}/import/bills", summary="Bulk import bills from CSV")
async def import_bills(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    content = (await file.read()).decode("utf-8-sig")
    try:
        result = await BulkImportService.import_bills_csv(db, client_id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return result


@router.post("/clients/{client_id}/import/invoices", summary="Bulk import invoices from CSV")
async def import_invoices(
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    content = (await file.read()).decode("utf-8-sig")
    try:
        result = await BulkImportService.import_invoices_csv(db, client_id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return result


@router.get("/import/template/{entity_type}", summary="Download CSV import template")
async def download_template(
    entity_type: str,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    template = BulkImportService.generate_template(entity_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity_type}")
    return Response(
        content=template,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity_type}-template.csv"},
    )
