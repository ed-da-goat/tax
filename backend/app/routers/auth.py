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

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.blacklist import blacklist
from app.auth.dependencies import CurrentUser, get_current_user, require_role, verify_role
from app.auth.jwt import create_access_token, verify_token
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
limiter = Limiter(key_func=get_remote_address)
bearer_scheme = HTTPBearer()


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
@limiter.limit("10/minute")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate with email + password and receive a JWT.

    Sets an HTTP-Only cookie with the JWT for browser clients.
    Also returns the token in the response body for API clients.
    """
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

    # Check if 2FA is enabled
    has_2fa = bool(
        user.totp_secret_encrypted
        and not user.totp_secret_encrypted.startswith("PENDING:")
    )
    if has_2fa:
        totp_code = getattr(data, "totp_code", None)
        if not totp_code:
            # Return a challenge — don't issue a token yet
            return LoginResponse(
                access_token="",
                token_type="bearer",
                user=UserResponse.model_validate(user),
                requires_2fa=True,
            )
        # Verify TOTP
        import pyotp
        from app.crypto import decrypt_value
        secret = decrypt_value(user.totp_secret_encrypted)
        totp = pyotp.TOTP(secret)
        if not totp.verify(totp_code, valid_window=0):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

    token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        extra_claims={"full_name": user.full_name},
    )

    # Set HTTP-Only cookie for browser clients (XSS-safe)
    from app.config import settings

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="strict",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/api",
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
) -> dict[str, str]:
    """Invalidate the current JWT by adding its jti to the blacklist.

    Reads the token from the HTTP-Only cookie or Authorization header.
    Clears the cookie on logout.
    """
    # Try cookie first, then Authorization header
    raw_token = request.cookies.get("access_token")
    if not raw_token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_token(raw_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    exp = payload.get("exp", 0)
    if jti:
        blacklist.revoke(jti, float(exp))

    # Clear the HTTP-Only cookie
    response.delete_cookie(key="access_token", path="/api")

    return {"message": "Successfully logged out"}


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


# ---------------------------------------------------------------------------
# 2FA Endpoints (C6)
# ---------------------------------------------------------------------------
@router.post("/2fa/setup", summary="Set up TOTP 2FA")
@limiter.limit("5/minute")
async def setup_2fa(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a TOTP secret and return QR code data for authenticator apps."""
    import pyotp
    import qrcode
    import io
    import base64
    from app.crypto import encrypt_value

    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.totp_secret_encrypted:
        raise HTTPException(status_code=400, detail="2FA is already enabled. Disable it first.")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="Georgia CPA Firm",
    )

    # Generate QR code as base64 PNG
    qr = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    # Store encrypted secret (not yet enabled — user must verify first)
    # We store with a pending prefix so verify can activate it
    user.totp_secret_encrypted = "PENDING:" + encrypt_value(secret)
    await db.commit()

    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_b64}",
        "provisioning_uri": provisioning_uri,
        "message": "Scan the QR code with your authenticator app, then call /2fa/verify to activate.",
    }


@router.post("/2fa/verify", summary="Verify and activate 2FA")
@limiter.limit("5/minute")
async def verify_2fa(
    request: Request,
    code: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify a TOTP code to activate 2FA. Must be called after /2fa/setup."""
    import pyotp
    from app.crypto import decrypt_value

    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.totp_secret_encrypted or not user.totp_secret_encrypted.startswith("PENDING:"):
        raise HTTPException(status_code=400, detail="No pending 2FA setup. Call /2fa/setup first.")

    encrypted_secret = user.totp_secret_encrypted.replace("PENDING:", "", 1)
    secret = decrypt_value(encrypted_secret)
    totp = pyotp.TOTP(secret)

    if not totp.verify(code, valid_window=0):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Activate: remove PENDING prefix
    from app.crypto import encrypt_value
    user.totp_secret_encrypted = encrypt_value(secret)
    await db.commit()

    return {"message": "2FA has been activated successfully", "enabled": True}


@router.post("/2fa/disable", summary="Disable 2FA")
@limiter.limit("5/minute")
async def disable_2fa(
    request: Request,
    code: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable 2FA for the current user. Requires a valid TOTP code."""
    import pyotp
    from app.crypto import decrypt_value

    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.totp_secret_encrypted or user.totp_secret_encrypted.startswith("PENDING:"):
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    secret = decrypt_value(user.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)

    if not totp.verify(code, valid_window=0):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.totp_secret_encrypted = None
    await db.commit()

    return {"message": "2FA has been disabled", "enabled": False}


# ---------------------------------------------------------------------------
# Forgot Password (E2)
# ---------------------------------------------------------------------------
class ForgotPasswordRequest(BaseModel):
    """POST /api/v1/auth/forgot-password request body."""
    email: str


@router.post("/forgot-password", summary="Request password reset")
@limiter.limit("5/minute")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Request a password reset token. Always returns success to prevent email enumeration."""
    from app.services.password_reset import request_password_reset
    from app.services.email import send_email

    email = data.email
    result = await request_password_reset(db, email)

    # If token was generated and email is configured, send it
    if result.get("token"):
        reset_url = f"https://localhost/reset-password?token={result['token']}"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Password Reset</h2>
            <p>A password reset was requested for your account.</p>
            <p><a href="{reset_url}" style="display: inline-block; padding: 10px 24px;
                background: #2563eb; color: white; text-decoration: none; border-radius: 6px;">
                Reset Password
            </a></p>
            <p style="color: #6b7280; font-size: 12px;">
                This link expires in {result['expires_minutes']} minutes.
                If you didn't request this, ignore this email.
            </p>
        </div>
        """
        await send_email(to=email, subject="Password Reset Request", html_body=html)

    return {"message": "If an account with that email exists, a reset link has been sent."}


class ResetPasswordRequest(BaseModel):
    """POST /api/v1/auth/reset-password request body."""
    token: str
    new_password: str


@router.post("/reset-password", summary="Reset password with token")
@limiter.limit("5/minute")
async def reset_password_endpoint(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset password using a valid reset token."""
    from app.services.password_reset import reset_password

    # Validate password strength
    from app.schemas.auth import _validate_password_strength
    try:
        _validate_password_strength(data.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    success = await reset_password(db, data.token, data.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    await db.commit()
    return {"message": "Password has been reset successfully"}


@router.get("/2fa/status", summary="Check 2FA status")
async def get_2fa_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if 2FA is enabled for the current user."""
    user = await auth_service.get_user(db, uuid.UUID(current_user.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    enabled = bool(
        user.totp_secret_encrypted
        and not user.totp_secret_encrypted.startswith("PENDING:")
    )
    return {"enabled": enabled}
