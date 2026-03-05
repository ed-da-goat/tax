"""
Tax e-filing services (Phase 8B).

Provides submission tracking and integration stubs for:
- TaxBandits API (1099, W-2, 940, 941)
- Georgia DOR FSET (G-7 withholding via SFTP + XML)
- Manual filing record-keeping
"""

from .tax_filing_service import TaxFilingService

__all__ = [
    "TaxFilingService",
]
