"""
Router registry.

All API routers are registered here and mounted onto the FastAPI app.
Builder agents add their routers to this module as they complete each module.

Usage in main.py:
    from app.routers import register_routers
    register_routers(app)
"""

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    """
    Mount all API routers onto the FastAPI application.

    Builder agents: when you create a new router, import it here and
    add an `app.include_router(...)` call with the appropriate prefix
    and tags.

    Example:
        from app.routers.clients import router as clients_router
        app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])
    """
    # --- Phase 1 routers (Foundation) ---
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    from app.routers.clients import router as clients_router
    app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])

    from app.routers.chart_of_accounts import router as coa_router
    app.include_router(coa_router, prefix="/api/v1", tags=["chart-of-accounts"])

    # --- Phase 2 routers (Transactions) ---
    # from app.routers.ap import router as ap_router
    # app.include_router(ap_router, prefix="/api/v1/ap", tags=["accounts-payable"])

    # --- Phase 3 routers (Document Management) ---
    # from app.routers.documents import router as documents_router
    # app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])

    # --- Phase 4 routers (Payroll) ---
    # from app.routers.payroll import router as payroll_router
    # app.include_router(payroll_router, prefix="/api/v1/payroll", tags=["payroll"])

    # --- Phase 5 routers (Tax Exports) ---
    # from app.routers.tax_exports import router as tax_router
    # app.include_router(tax_router, prefix="/api/v1/tax", tags=["tax-exports"])

    # --- Phase 6 routers (Reporting) ---
    # from app.routers.reports import router as reports_router
    # app.include_router(reports_router, prefix="/api/v1/reports", tags=["reports"])

    pass  # Remove when all routers are added
