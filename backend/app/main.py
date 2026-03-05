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

from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.security import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import register_routers

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Validate critical config on startup
    if settings.JWT_SECRET == "CHANGE-ME-IN-PRODUCTION" and not settings.DEBUG:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET is set to default value. "
            "Set a strong JWT_SECRET environment variable before running in production."
        )
    if settings.JWT_SECRET == "CHANGE-ME-IN-PRODUCTION":
        logger.warning(
            "JWT_SECRET is using the default development value. "
            "Set a strong secret before deploying."
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
# Security Headers — must be outermost middleware (runs last on response)
# ---------------------------------------------------------------------------
app.add_middleware(SecurityHeadersMiddleware)

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
