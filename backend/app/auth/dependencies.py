"""
FastAPI dependencies for authentication and role-based access control.

Compliance requirements (CLAUDE.md):
- Every API endpoint must check role before executing.
- 403 responses: {"error": "Insufficient permissions", "required_role": "<role>"}
- require_role works at the FUNCTION level, not just route level (defense in depth).
- Payroll finalization must verify CPA_OWNER at function level (rule #6).
"""

from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.auth.blacklist import blacklist
from app.auth.jwt import verify_token

# ---------------------------------------------------------------------------
# Security scheme — auto_error=False so we can fall back to cookie
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# User representation returned by auth dependencies
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user extracted from a valid JWT."""

    user_id: str
    role: str

    @property
    def is_cpa_owner(self) -> bool:
        return self.role == "CPA_OWNER"

    @property
    def is_associate(self) -> bool:
        return self.role == "ASSOCIATE"


# ---------------------------------------------------------------------------
# Core auth dependency — extracts and validates the JWT
# Reads from HTTP-Only cookie first, falls back to Authorization header.
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> CurrentUser:
    """
    Extract the current user from the HTTP-Only cookie or Bearer token.

    Priority: cookie 'access_token' > Authorization header.
    Raises HTTP 401 if no valid token is found.
    """
    # Try HTTP-Only cookie first (browser clients)
    raw_token = request.cookies.get("access_token")

    # Fall back to Authorization: Bearer header (API clients)
    if not raw_token and credentials:
        raw_token = credentials.credentials

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
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

    # Check if token has been revoked (server-side logout)
    jti = payload.get("jti")
    if jti and blacklist.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=payload["sub"],
        role=payload["role"],
    )


# ---------------------------------------------------------------------------
# Role enforcement dependency factory
# ---------------------------------------------------------------------------
def require_role(required_role: str) -> Callable[..., CurrentUser]:
    """
    Return a FastAPI dependency that enforces a specific role.

    Usage as a route dependency:
        @router.post("/payroll/finalize")
        async def finalize_payroll(
            user: CurrentUser = Depends(require_role("CPA_OWNER")),
        ):
            ...

    Usage at the function level (defense in depth, per CLAUDE.md rule #6):
        def finalize_payroll_logic(user: CurrentUser):
            verify_role(user, "CPA_OWNER")
            ...

    On failure returns HTTP 403:
        {"error": "Insufficient permissions", "required_role": "<role>"}
    """

    async def _role_checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "required_role": required_role,
                },
            )
        return current_user

    return _role_checker


# ---------------------------------------------------------------------------
# Function-level role check (defense in depth — CLAUDE.md rule #6)
# ---------------------------------------------------------------------------
def verify_role(user: CurrentUser, required_role: str) -> None:
    """
    Verify a user has the required role at the function/service level.

    Call this inside business logic functions as a second layer of
    defense, in addition to the route-level require_role dependency.

    Raises HTTPException 403 with the standard error format.
    """
    if user.role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Insufficient permissions",
                "required_role": required_role,
            },
        )
