"""
FastAPI application entry point.

Configures CORS, registers routers, and provides the health check endpoint.
Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.routers import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup: future DB pool initialization, migration checks, etc.
    yield
    # Shutdown: future cleanup tasks


app = FastAPI(
    title="Georgia CPA Accounting System",
    description="Internal accounting system for a Georgia CPA firm. "
    "Replaces QuickBooks Online with local, compliance-aware tooling.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the React + Vite frontend on localhost
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Audit middleware — logs every request for compliance (skeleton)
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
