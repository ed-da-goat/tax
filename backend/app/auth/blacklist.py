"""
In-memory JWT token blacklist for server-side logout.

Stores revoked token JTI (JWT ID) values with their expiration times.
Tokens are automatically cleaned up after they would have expired anyway.

Note: This blacklist clears on server restart, which is acceptable for a
single-server local deployment. Tokens also expire via the 'exp' claim,
so a restart effectively invalidates all active tokens (users re-login).
"""

from __future__ import annotations

import threading
import time


class TokenBlacklist:
    """Thread-safe in-memory set of revoked JWT IDs."""

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}  # jti -> expiry timestamp
        self._lock = threading.Lock()

    def revoke(self, jti: str, exp: float) -> None:
        """Add a token's JTI to the blacklist until its natural expiry."""
        with self._lock:
            self._revoked[jti] = exp

    def is_revoked(self, jti: str) -> bool:
        """Check if a token JTI has been revoked."""
        with self._lock:
            return jti in self._revoked

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of entries removed."""
        now = time.time()
        with self._lock:
            expired = [jti for jti, exp in self._revoked.items() if exp < now]
            for jti in expired:
                del self._revoked[jti]
            return len(expired)

    def __len__(self) -> int:
        with self._lock:
            return len(self._revoked)


# Singleton instance used across the application
blacklist = TokenBlacklist()
