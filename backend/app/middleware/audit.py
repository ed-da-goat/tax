"""
Audit logging middleware skeleton.

Compliance (CLAUDE.md rule #2 — AUDIT TRAIL):
    Every INSERT, UPDATE, DELETE must write a row to the audit_log table.
    This middleware captures request-level metadata (user, endpoint, method).

    The actual audit_log writes for database mutations happen at the
    ORM/service layer (via SQLAlchemy event listeners or explicit calls).
    This middleware provides the request context (user_id, IP, endpoint)
    that those lower-level audit writers need.

NOTE: This is a skeleton. The full implementation will be completed
when the audit_log table and ORM model are built (module O1).
"""

import time
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request metadata for audit purposes.

    Captures:
    - Requesting user (from JWT, if present)
    - HTTP method and path
    - Client IP address
    - Response status code
    - Request duration

    This data is logged structurally. When the audit_log DB table
    is available (module O1), this will also persist to the database.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        start_time = time.perf_counter()

        # Extract client IP
        client_ip = request.client.host if request.client else "unknown"

        # Extract user_id from JWT if present (best-effort, no auth enforcement)
        user_id: str | None = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.auth.jwt import verify_token

                payload = verify_token(auth_header.removeprefix("Bearer ").strip())
                user_id = payload.get("sub")
            except Exception:
                # Token may be invalid; that's fine for audit purposes.
                # Auth enforcement happens in the route dependencies.
                pass

        # Store audit context on request state so downstream handlers
        # (services, ORM event listeners) can access it.
        request.state.audit_user_id = user_id
        request.state.audit_client_ip = client_ip

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log the request (structured logging)
        logger.info(
            "request",
            extra={
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": client_ip,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
