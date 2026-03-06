"""
API router for global search (D1).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.services.search import SearchService

router = APIRouter()


@router.get("/search", summary="Global search across all entities")
async def global_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await SearchService.search(db, q, limit)
