"""
FastAPI application entry point.

Configures CORS, security middleware, rate limiting, registers routers,
and provides the health check endpoint.
Run with: uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.security import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import register_routers

logger = logging.getLogger("app")

# ---------------------------------------------------------------------------
# Rate limiter — 100 req/min global, tighter on auth endpoints
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Validate critical config on startup
    if len(settings.JWT_SECRET) < 32:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET is too short (min 32 chars). "
            "Set a strong JWT_SECRET in .env."
        )
    if len(settings.ENCRYPTION_KEY) < 20:
        raise RuntimeError(
            "CRITICAL: ENCRYPTION_KEY is too short. "
            "Generate a Fernet key: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\" and set ENCRYPTION_KEY in .env"
        )
    yield
    # Shutdown: future cleanup tasks


app = FastAPI(
    title="Georgia CPA Accounting System",
    description="Internal accounting system for a Georgia CPA firm. "
    "Replaces QuickBooks Online with local, compliance-aware tooling.",
    version="0.1.0",
    lifespan=lifespan,
    # Disable docs and schema in production
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# ---------------------------------------------------------------------------
# Rate limiting via slowapi
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Security Headers — must be outermost middleware (runs last on response)
# ---------------------------------------------------------------------------
app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------------------------
# Rate limiting middleware (slowapi)
# ---------------------------------------------------------------------------
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# Request Size Limit — reject oversized payloads early
# ---------------------------------------------------------------------------
app.add_middleware(RequestSizeLimitMiddleware)

# ---------------------------------------------------------------------------
# CORS — allow the React + Vite frontend on localhost
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["Content-Disposition"],
)

# ---------------------------------------------------------------------------
# Audit middleware — logs every request for compliance
# ---------------------------------------------------------------------------
app.add_middleware(AuditMiddleware)

# ---------------------------------------------------------------------------
# Register all routers
# ---------------------------------------------------------------------------
register_routers(app)


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns HTTP 200 if the application is running.
    Future: include DB connectivity, disk space, last backup timestamp
    (see module O4 in CLAUDE.md).
    """
    return {"status": "healthy", "version": app.version}
