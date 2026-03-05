"""
Authentication and user management API routes.

Endpoints:
- POST /api/v1/auth/login      — authenticate, return JWT
- POST /api/v1/auth/users      — create user (CPA_OWNER only)
- GET  /api/v1/auth/me          — get current user from token
- GET  /api/v1/auth/users       — list users (CPA_OWNER only)
- PUT  /api/v1/auth/users/{id}  — update user (CPA_OWNER only)
- DELETE /api/v1/auth/users/{id} — deactivate (CPA_OWNER only)

Compliance:
- Every 403 is logged to permission_log table.
- Role checks at function level (defense in depth).
- Passwords hashed with passlib bcrypt.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.auth.jwt import create_access_token
from app.database import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import auth as auth_service

router = APIRouter()


def _client_ip(request: Request) -> str:
    """Extract client IP from the request."""
    return request.client.host if request.client else "unknown"


async def _log_403(
    db: AsyncSession,
    request: Request,
    user: CurrentUser,
    role_required: str,
) -> None:
    """Log a 403 rejection to the permission_log table."""
    try:
        await auth_service.log_permission_denial(
            db=db,
            user_id=user.user_id,
            endpoint=request.url.path,
            method=request.method,
            role_required=role_required,
            role_provided=user.role,
            ip_address=_client_ip(request),
        )
    except Exception:
        # Logging failure must never prevent the 403 from being returned
        pass


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate with email + password and receive a JWT."""
    from app.middleware.security import (
        check_login_rate,
        clear_login_attempts,
        record_failed_login,
    )

    client_ip = _client_ip(request)

    # Rate limit check
    rate_error = check_login_rate(client_ip, data.email)
    if rate_error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_error,
        )

    user = await auth_service.authenticate(db, data.email, data.password)
    if user is None:
        record_failed_login(client_ip, data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Successful login — clear rate limit tracking
    clear_login_attempts(client_ip, data.email)

    token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        extra_claims={"full_name": user.full_name},
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/users  (CPA_OWNER only)
# ---------------------------------------------------------------------------
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user. CPA_OWNER only."""
    # Defense in depth: function-level role check
    if current_user.role != "CPA_OWNER":
        await _log_403(db, request, current_user, "CPA_OWNER")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Insufficient permissions",
                "required_role": "CPA_OWNER",
            },
        )
    verify_role(current_user, "CPA_OWNER")

    user = await auth_service.create_user(db, data)
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get the current authenticated user's profile."""
    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/users  (CPA_OWNER only)
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all active users. CPA_OWNER only."""
    if current_user.role != "CPA_OWNER":
        await _log_403(db, request, current_user, "CPA_OWNER")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Insufficient permissions",
                "required_role": "CPA_OWNER",
            },
        )
    verify_role(current_user, "CPA_OWNER")

    users = await auth_service.list_users(db)
    return [UserResponse.model_validate(u) for u in users]


# ---------------------------------------------------------------------------
# PUT /api/v1/auth/users/{user_id}  (CPA_OWNER only)
# ---------------------------------------------------------------------------
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's profile. CPA_OWNER only."""
    if current_user.role != "CPA_OWNER":
        await _log_403(db, request, current_user, "CPA_OWNER")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Insufficient permissions",
                "required_role": "CPA_OWNER",
            },
        )
    verify_role(current_user, "CPA_OWNER")

    user = await auth_service.update_user(db, user_id, data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# DELETE /api/v1/auth/users/{user_id}  (CPA_OWNER only)
# ---------------------------------------------------------------------------
@router.delete("/users/{user_id}", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Deactivate (soft-delete) a user. CPA_OWNER only."""
    if current_user.role != "CPA_OWNER":
        await _log_403(db, request, current_user, "CPA_OWNER")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Insufficient permissions",
                "required_role": "CPA_OWNER",
            },
        )
    verify_role(current_user, "CPA_OWNER")

    user = await auth_service.deactivate_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/change-password
# ---------------------------------------------------------------------------
@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Change the current user's password. Requires current password verification."""
    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify current password
    if not auth_service.verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Prevent reusing the same password
    if auth_service.verify_password(data.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Update password
    user.password_hash = auth_service.hash_password(data.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}
