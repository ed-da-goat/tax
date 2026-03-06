"""
API router for client statements (C5).

Endpoints:
- GET  /clients/{id}/statements         — generate statement data
- GET  /clients/{id}/statements/pdf      — download statement PDF
- POST /clients/{id}/statements/send     — email statement to client
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.services.statement import StatementService

router = APIRouter()


@router.get("/clients/{client_id}/statements", summary="Generate client statement")
async def get_statement(
    client_id: uuid.UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await StatementService.generate_statement(db, client_id, start_date, end_date)


@router.get("/clients/{client_id}/statements/pdf", summary="Download statement PDF")
async def get_statement_pdf(
    client_id: uuid.UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    pdf_bytes = await StatementService.generate_statement_pdf(db, client_id, start_date, end_date)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=statement-{client_id}-{start_date}-{end_date}.pdf"},
    )


@router.post("/clients/{client_id}/statements/send", summary="Email statement to client")
async def send_statement_email(
    client_id: uuid.UUID,
    to_email: str = Query(..., description="Recipient email"),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> dict:
    from app.services.email import send_email, render_statement_email

    data = await StatementService.generate_statement(db, client_id, start_date, end_date)
    pdf_bytes = await StatementService.generate_statement_pdf(db, client_id, start_date, end_date)

    subject, html = render_statement_email(
        client_name=data["client_name"],
        period=data["period"],
        balance=data["total_outstanding"],
    )
    result = await send_email(
        to=to_email,
        subject=subject,
        html_body=html,
        attachments=[{
            "filename": f"statement-{start_date}-{end_date}.pdf",
            "content": pdf_bytes,
            "mime_type": "application/pdf",
        }],
    )
    return result
