"""
API router for tax form data exports (modules X1-X9).

All export endpoints are CPA_OWNER only (per CLAUDE.md role permissions).
Defense in depth: verify_role at function level for all endpoints.

Compliance (CLAUDE.md):
- Rule #4: CLIENT ISOLATION — client_id from URL path.
- Rule #6: Defense in depth — both route and function level role checks.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, require_role, verify_role
from app.database import get_db
from fastapi.responses import Response

from app.schemas.form_1099 import Form1099NECSummaryResponse
from app.schemas.tax_exports import (
    Form1065Data,
    Form1120Data,
    Form1120SData,
    Form500Data,
    Form600Data,
    FormG7Data,
    FormST3Data,
    ScheduleCData,
    TaxDocumentChecklist,
)
from app.schemas.w2 import W2SummaryResponse
from app.services.payroll.w2_generator import W2GeneratorService
from app.services.tax_exports import (
    Form1065Service,
    Form1120SService,
    Form1120Service,
    Form500Service,
    Form600Service,
    FormG7Service,
    FormST3Service,
    ScheduleCService,
    TaxChecklistService,
)
from app.services.tax_exports_1099 import Form1099NECService

router = APIRouter()


# ---------------------------------------------------------------------------
# X1 — Georgia Form G-7
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/g7",
    response_model=FormG7Data,
    summary="Generate Georgia Form G-7 data (quarterly payroll withholding)",
)
async def get_form_g7(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    quarter: int = Query(..., ge=1, le=4),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> FormG7Data:
    """Generate Georgia Form G-7 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await FormG7Service.generate(db, client_id, tax_year, quarter)


# ---------------------------------------------------------------------------
# X2 — Georgia Form 500
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/form-500",
    response_model=Form500Data,
    summary="Generate Georgia Form 500 data (individual income)",
)
async def get_form_500(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form500Data:
    """Generate Georgia Form 500 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form500Service.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X3 — Georgia Form 600
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/form-600",
    response_model=Form600Data,
    summary="Generate Georgia Form 600 data (corporate income)",
)
async def get_form_600(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form600Data:
    """Generate Georgia Form 600 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form600Service.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X4 — Georgia Form ST-3
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/st3",
    response_model=FormST3Data,
    summary="Generate Georgia Form ST-3 data (sales tax)",
)
async def get_form_st3(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> FormST3Data:
    """Generate Georgia Form ST-3 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await FormST3Service.generate(db, client_id, tax_year, period_start, period_end)


# ---------------------------------------------------------------------------
# X5 — Federal Schedule C
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/schedule-c",
    response_model=ScheduleCData,
    summary="Generate Federal Schedule C data (sole proprietors)",
)
async def get_schedule_c(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> ScheduleCData:
    """Generate Federal Schedule C data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await ScheduleCService.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X6 — Federal Form 1120-S
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/form-1120s",
    response_model=Form1120SData,
    summary="Generate Federal Form 1120-S data (S-Corps)",
)
async def get_form_1120s(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form1120SData:
    """Generate Federal Form 1120-S data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form1120SService.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X7 — Federal Form 1120
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/form-1120",
    response_model=Form1120Data,
    summary="Generate Federal Form 1120 data (C-Corps)",
)
async def get_form_1120(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form1120Data:
    """Generate Federal Form 1120 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form1120Service.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X8 — Federal Form 1065
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/form-1065",
    response_model=Form1065Data,
    summary="Generate Federal Form 1065 data (Partnerships/LLCs)",
)
async def get_form_1065(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form1065Data:
    """Generate Federal Form 1065 data. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form1065Service.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# X9 — Tax Document Checklist
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/checklist",
    response_model=TaxDocumentChecklist,
    summary="Generate tax document checklist",
)
async def get_tax_checklist(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> TaxDocumentChecklist:
    """Generate per-client tax document checklist by entity type. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await TaxChecklistService.generate(db, client_id, tax_year)


# ---------------------------------------------------------------------------
# W-2 Generation
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/w2",
    response_model=W2SummaryResponse,
    summary="Generate W-2 data for all employees",
)
async def get_w2_data(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> W2SummaryResponse:
    """Generate W-2 data for all employees of a client. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await W2GeneratorService.get_w2_data(db, client_id, tax_year)


@router.get(
    "/clients/{client_id}/w2/{employee_id}/pdf",
    summary="Generate single W-2 PDF",
    response_class=Response,
)
async def get_w2_pdf(
    client_id: uuid.UUID,
    employee_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Generate a single employee W-2 PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    summary = await W2GeneratorService.get_w2_data(db, client_id, tax_year)
    w2 = next((w for w in summary.w2s if w.employee_id == employee_id), None)
    if w2 is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No W-2 data for this employee")
    pdf_bytes = W2GeneratorService.generate_w2_pdf(w2, summary.employer_name, summary.employer_address)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=w2_{employee_id}_{tax_year}.pdf"},
    )


@router.get(
    "/clients/{client_id}/w2/pdf",
    summary="Generate batch W-2 PDF for all employees",
    response_class=Response,
)
async def get_w2_batch_pdf(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Generate batch W-2 PDF for all employees. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    summary = await W2GeneratorService.get_w2_data(db, client_id, tax_year)
    pdf_bytes = W2GeneratorService.generate_batch_w2_pdf(summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=w2_batch_{client_id}_{tax_year}.pdf"},
    )


# ---------------------------------------------------------------------------
# 1099-NEC Generation
# ---------------------------------------------------------------------------


@router.get(
    "/clients/{client_id}/1099-nec",
    response_model=Form1099NECSummaryResponse,
    summary="Generate 1099-NEC data for eligible vendors",
)
async def get_1099_nec_data(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Form1099NECSummaryResponse:
    """Generate 1099-NEC data for all eligible vendors. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    return await Form1099NECService.get_1099_data(db, client_id, tax_year)


@router.get(
    "/clients/{client_id}/1099-nec/{vendor_id}/pdf",
    summary="Generate single 1099-NEC PDF",
    response_class=Response,
)
async def get_1099_nec_pdf(
    client_id: uuid.UUID,
    vendor_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Generate a single vendor 1099-NEC PDF. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    summary = await Form1099NECService.get_1099_data(db, client_id, tax_year)
    form = next((f for f in summary.forms if f.vendor_id == vendor_id), None)
    if form is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No 1099-NEC data for this vendor")
    pdf_bytes = Form1099NECService.generate_1099_pdf(form, summary.payer_name, summary.payer_address)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=1099nec_{vendor_id}_{tax_year}.pdf"},
    )


@router.get(
    "/clients/{client_id}/1099-nec/pdf",
    summary="Generate batch 1099-NEC PDF for all eligible vendors",
    response_class=Response,
)
async def get_1099_nec_batch_pdf(
    client_id: uuid.UUID,
    tax_year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_role("CPA_OWNER")),
) -> Response:
    """Generate batch 1099-NEC PDF for all eligible vendors. CPA_OWNER only."""
    verify_role(user, "CPA_OWNER")
    summary = await Form1099NECService.get_1099_data(db, client_id, tax_year)
    pdf_bytes = Form1099NECService.generate_batch_1099_pdf(summary)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=1099nec_batch_{client_id}_{tax_year}.pdf"},
    )
