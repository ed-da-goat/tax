"""
Security middleware for the Georgia CPA Accounting System.

Provides:
- Security response headers (HSTS, X-Frame-Options, CSP, etc.)
- Request body size limiting
- Login attempt rate tracking (in-memory, suitable for single-instance)
"""

import time
import logging
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger("security")

# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
    (b"content-security-policy",
     b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
     b"img-src 'self' data:; frame-ancestors 'none'"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
]

API_CACHE_HEADERS: list[tuple[bytes, bytes]] = [
    (b"cache-control", b"no-store, no-cache, must-revalidate"),
    (b"pragma", b"no-cache"),
]


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware that injects security headers into every response.

    Uses raw ASGI instead of BaseHTTPMiddleware to preserve Set-Cookie
    headers (BaseHTTPMiddleware wraps responses in StreamingResponse
    which can strip cookies).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_api = scope["path"].startswith("/api/")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(SECURITY_HEADERS)
                if is_api:
                    headers.extend(API_CACHE_HEADERS)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


# ---------------------------------------------------------------------------
# Request Body Size Limit Middleware
# ---------------------------------------------------------------------------

# 10 MB for regular requests, file uploads handled separately
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB for file uploads


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding the configured limit."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            is_upload = request.url.path.endswith("/documents") and request.method == "POST"
            limit = MAX_UPLOAD_SIZE if is_upload else MAX_BODY_SIZE
            if size > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Login Rate Limiter (in-memory)
# ---------------------------------------------------------------------------

# Track failed login attempts: {ip: [(timestamp, email), ...]}
_login_attempts: dict[str, list[tuple[float, str]]] = defaultdict(list)
# Track per-email attempts: {email: [(timestamp, ip), ...]}
_email_attempts: dict[str, list[tuple[float, str]]] = defaultdict(list)

# Limits
MAX_ATTEMPTS_PER_IP = 10  # per window
MAX_ATTEMPTS_PER_EMAIL = 5  # per window
RATE_WINDOW_SECONDS = 300  # 5-minute window


def _clean_old_attempts(attempts: list, window: float) -> list:
    """Remove attempts older than the window."""
    cutoff = time.time() - window
    return [a for a in attempts if a[0] > cutoff]


def record_failed_login(ip: str, email: str) -> None:
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    _login_attempts[ip] = _clean_old_attempts(_login_attempts[ip], RATE_WINDOW_SECONDS)
    _login_attempts[ip].append((now, email))
    _email_attempts[email] = _clean_old_attempts(_email_attempts[email], RATE_WINDOW_SECONDS)
    _email_attempts[email].append((now, ip))
    logger.warning(
        "failed_login",
        extra={"ip": ip, "email": email, "ip_attempts": len(_login_attempts[ip])},
    )


def check_login_rate(ip: str, email: str) -> str | None:
    """
    Check if a login attempt should be rate-limited.

    Returns an error message if rate-limited, or None if OK.
    """
    _login_attempts[ip] = _clean_old_attempts(_login_attempts[ip], RATE_WINDOW_SECONDS)
    _email_attempts[email] = _clean_old_attempts(_email_attempts[email], RATE_WINDOW_SECONDS)

    if len(_login_attempts[ip]) >= MAX_ATTEMPTS_PER_IP:
        return "Too many login attempts from this address. Try again in 5 minutes."
    if len(_email_attempts[email]) >= MAX_ATTEMPTS_PER_EMAIL:
        return "Too many login attempts for this account. Try again in 5 minutes."
    return None


def clear_login_attempts(ip: str, email: str) -> None:
    """Clear rate limit tracking on successful login."""
    _login_attempts.pop(ip, None)
    _email_attempts.pop(email, None)
