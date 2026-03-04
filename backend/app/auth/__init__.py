"""
Authentication and authorization package.

Implements JWT-based auth with two roles per CLAUDE.md:
- CPA_OWNER: full access (approve, post, payroll, exports, admin)
- ASSOCIATE: limited access (view, draft entry, upload, draft reports)

Every endpoint must check role before executing. 403 responses use:
    {"error": "Insufficient permissions", "required_role": "<role>"}
"""

from app.auth.dependencies import get_current_user, require_role
from app.auth.jwt import create_access_token, verify_token

__all__ = [
    "create_access_token",
    "get_current_user",
    "require_role",
    "verify_token",
]
