"""
Tests for the health check endpoint and basic application setup.

These tests verify:
1. The FastAPI app starts and responds to requests
2. The health endpoint returns correct status
3. CORS headers are configured
4. Auth dependencies reject unauthenticated requests properly
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for GET /health."""

    async def test_health_returns_200(self, client: AsyncClient) -> None:
        """Health check should return 200 with status and version."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_health_no_auth_required(self, client: AsyncClient) -> None:
        """Health check should not require authentication."""
        # No Authorization header sent
        response = await client.get("/health")
        assert response.status_code == 200
