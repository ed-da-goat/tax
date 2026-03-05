"""
Client portal API endpoints (CP1-CP4).

Portal users, messaging, questionnaires, e-signatures.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.portal import (
    PortalUserCreate, PortalUserResponse, PortalUserList,
    PortalLoginRequest, PortalLoginResponse,
    MessageCreate, MessageResponse, MessageList,
    QuestionnaireCreate, QuestionnaireResponse as QResponse, QuestionnaireList,
    QuestionnaireSubmit,
    SignatureRequestCreate, SignatureRequestResponse, SignatureRequestList,
    SignatureSubmit,
)
from app.services.portal_service import PortalService

router = APIRouter()


# --- Portal Users ---
@router.post("/portal-users", response_model=PortalUserResponse, status_code=status.HTTP_201_CREATED)
async def create_portal_user(
    data: PortalUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    user = await PortalService.create_portal_user(db, data, current_user)
    return PortalUserResponse.model_validate(user)


@router.get("/portal-users", response_model=PortalUserList)
async def list_portal_users(
    client_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    users = await PortalService.list_portal_users(db, client_id)
    return PortalUserList(
        items=[PortalUserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.post("/portal/login", response_model=PortalLoginResponse)
async def portal_login(
    data: PortalLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth import AuthService
    user = await PortalService.authenticate_portal_user(db, data.email, data.password)
    token = AuthService.create_token(
        user_id=str(user.id), role="PORTAL_USER",
        extra_claims={"client_id": str(user.client_id), "portal": True},
    )
    return PortalLoginResponse(
        access_token=token,
        portal_user=PortalUserResponse.model_validate(user),
    )


# --- Messages ---
@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    msg = await PortalService.send_message(db, data, current_user=current_user)
    return MessageResponse.model_validate(msg)


@router.get("/messages/{client_id}", response_model=MessageList)
async def list_messages(
    client_id: UUID,
    thread_id: UUID | None = None,
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await PortalService.list_messages(db, client_id, thread_id, skip, limit)
    return MessageList(
        items=[MessageResponse.model_validate(m) for m in items],
        total=total,
    )


@router.post("/messages/{message_id}/read", response_model=MessageResponse)
async def mark_message_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    msg = await PortalService.mark_read(db, message_id)
    return MessageResponse.model_validate(msg)


# --- Questionnaires ---
@router.post("/questionnaires", response_model=QResponse, status_code=status.HTTP_201_CREATED)
async def create_questionnaire(
    data: QuestionnaireCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    q = await PortalService.create_questionnaire(db, data, current_user)
    return QResponse.model_validate(q)


@router.get("/questionnaires", response_model=QuestionnaireList)
async def list_questionnaires(
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await PortalService.list_questionnaires(
        db, client_id, status_filter, skip, limit
    )
    return QuestionnaireList(
        items=[QResponse.model_validate(q) for q in items],
        total=total,
    )


@router.get("/questionnaires/{questionnaire_id}", response_model=QResponse)
async def get_questionnaire(
    questionnaire_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    q = await PortalService.get_questionnaire(db, questionnaire_id)
    return QResponse.model_validate(q)


@router.post("/questionnaires/{questionnaire_id}/send", response_model=QResponse)
async def send_questionnaire(
    questionnaire_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    q = await PortalService.send_questionnaire(db, questionnaire_id, current_user)
    return QResponse.model_validate(q)


@router.post("/questionnaires/{questionnaire_id}/submit", response_model=QResponse)
async def submit_questionnaire(
    questionnaire_id: UUID,
    data: QuestionnaireSubmit,
    db: AsyncSession = Depends(get_db),
):
    q = await PortalService.submit_responses(db, questionnaire_id, data)
    return QResponse.model_validate(q)


# --- Signature Requests ---
@router.post("/signatures", response_model=SignatureRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_signature_request(
    data: SignatureRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    sig = await PortalService.create_signature_request(db, data, current_user)
    return SignatureRequestResponse.model_validate(sig)


@router.get("/signatures", response_model=SignatureRequestList)
async def list_signatures(
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items = await PortalService.list_signature_requests(db, client_id, status_filter)
    return SignatureRequestList(
        items=[SignatureRequestResponse.model_validate(s) for s in items],
        total=len(items),
    )


@router.post("/signatures/{signing_token}/sign", response_model=SignatureRequestResponse)
async def sign_document(
    signing_token: str,
    data: SignatureSubmit,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    sig = await PortalService.sign_document(db, signing_token, data, ip)
    return SignatureRequestResponse.model_validate(sig)
