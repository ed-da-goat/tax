"""
Time tracking API endpoints (PM1).

Endpoints:
    POST   /api/v1/time-entries          — Create time entry
    GET    /api/v1/time-entries          — List time entries (filterable)
    GET    /api/v1/time-entries/{id}     — Get single entry
    PUT    /api/v1/time-entries/{id}     — Update entry
    DELETE /api/v1/time-entries/{id}     — Soft-delete entry
    POST   /api/v1/time-entries/submit   — Submit entries for approval
    POST   /api/v1/time-entries/approve  — Approve submitted entries (CPA_OWNER)
    POST   /api/v1/timers               — Start timer
    POST   /api/v1/timers/{id}/stop     — Stop timer
    GET    /api/v1/timers/active        — Get active timer
    POST   /api/v1/timers/{id}/convert  — Convert timer to time entry
    POST   /api/v1/staff-rates          — Set staff rate (CPA_OWNER)
    GET    /api/v1/reports/utilization   — Utilization report
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, require_role
from app.database import get_db
from app.schemas.time_entry import (
    TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse, TimeEntryList,
    TimerSessionCreate, TimerSessionResponse, StaffRateCreate, StaffRateResponse,
    UtilizationReport,
)
from app.services.time_tracking import TimeTrackingService

router = APIRouter()


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    data: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    entry = await TimeTrackingService.create_time_entry(db, data, current_user)
    return TimeEntryResponse.model_validate(entry)


@router.get("/time-entries", response_model=TimeEntryList)
async def list_time_entries(
    user_id: UUID | None = None,
    client_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await TimeTrackingService.list_time_entries(
        db, user_id, client_id, date_from, date_to, status_filter, skip, limit
    )
    return TimeEntryList(
        items=[TimeEntryResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get("/time-entries/{entry_id}", response_model=TimeEntryResponse)
async def get_time_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    entry = await TimeTrackingService.get_time_entry(db, entry_id)
    return TimeEntryResponse.model_validate(entry)


@router.put("/time-entries/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    entry_id: UUID,
    data: TimeEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    entry = await TimeTrackingService.update_time_entry(db, entry_id, data, current_user)
    return TimeEntryResponse.model_validate(entry)


@router.delete("/time-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    await TimeTrackingService.delete_time_entry(db, entry_id, current_user)


@router.post("/time-entries/submit", response_model=list[TimeEntryResponse])
async def submit_time_entries(
    entry_ids: list[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    entries = await TimeTrackingService.submit_time_entries(db, entry_ids, current_user)
    return [TimeEntryResponse.model_validate(e) for e in entries]


@router.post("/time-entries/approve", response_model=list[TimeEntryResponse])
async def approve_time_entries(
    entry_ids: list[UUID],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    entries = await TimeTrackingService.approve_time_entries(db, entry_ids, current_user)
    return [TimeEntryResponse.model_validate(e) for e in entries]


# --- Timers ---
@router.post("/timers", response_model=TimerSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_timer(
    data: TimerSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    timer = await TimeTrackingService.start_timer(db, data, current_user)
    return TimerSessionResponse.model_validate(timer)


@router.post("/timers/{timer_id}/stop", response_model=TimerSessionResponse)
async def stop_timer(
    timer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    timer = await TimeTrackingService.stop_timer(db, timer_id, current_user)
    return TimerSessionResponse.model_validate(timer)


@router.get("/timers/active", response_model=TimerSessionResponse | None)
async def get_active_timer(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    timer = await TimeTrackingService.get_active_timer(db, current_user)
    return TimerSessionResponse.model_validate(timer) if timer else None


@router.post("/timers/{timer_id}/convert", response_model=TimeEntryResponse)
async def convert_timer(
    timer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    entry = await TimeTrackingService.convert_timer_to_entry(db, timer_id, current_user)
    return TimeEntryResponse.model_validate(entry)


# --- Staff Rates ---
@router.post("/staff-rates", response_model=StaffRateResponse, status_code=status.HTTP_201_CREATED)
async def set_staff_rate(
    data: StaffRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("CPA_OWNER")),
):
    rate = await TimeTrackingService.set_staff_rate(db, data, current_user)
    return StaffRateResponse.model_validate(rate)


# --- Utilization ---
@router.get("/reports/utilization", response_model=list[UtilizationReport])
async def utilization_report(
    date_from: date,
    date_to: date,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    return await TimeTrackingService.utilization_report(db, date_from, date_to)
