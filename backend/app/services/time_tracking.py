"""
Service layer for Time Tracking (PM1).

Features: time entries, timer sessions, staff rates, utilization reporting.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.time_entry import TimeEntry, TimeEntryStatus, StaffRate, TimerSession
from app.models.user import User
from app.schemas.time_entry import (
    TimeEntryCreate, TimeEntryUpdate, StaffRateCreate, TimerSessionCreate,
)


class TimeTrackingService:

    @staticmethod
    async def create_time_entry(
        db: AsyncSession, data: TimeEntryCreate, current_user: CurrentUser,
    ) -> TimeEntry:
        rate = data.hourly_rate
        if rate is None:
            rate = await TimeTrackingService._get_user_rate(db, current_user.user_id, data.entry_date)
        amount = None
        if rate and data.is_billable:
            amount = (Decimal(data.duration_minutes) / Decimal("60")) * rate

        entry = TimeEntry(
            client_id=data.client_id,
            user_id=current_user.user_id,
            date=data.entry_date,  # maps to DB column 'date'
            duration_minutes=data.duration_minutes,
            description=data.description,
            is_billable=data.is_billable,
            hourly_rate=rate,
            amount=amount,
            status=TimeEntryStatus.DRAFT,
            service_type=data.service_type,
            workflow_task_id=data.workflow_task_id,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def list_time_entries(
        db: AsyncSession,
        user_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[TimeEntry], int]:
        query = select(TimeEntry).where(TimeEntry.deleted_at.is_(None))
        count_query = select(func.count(TimeEntry.id)).where(TimeEntry.deleted_at.is_(None))

        if user_id:
            query = query.where(TimeEntry.user_id == user_id)
            count_query = count_query.where(TimeEntry.user_id == user_id)
        if client_id:
            query = query.where(TimeEntry.client_id == client_id)
            count_query = count_query.where(TimeEntry.client_id == client_id)
        if date_from:
            query = query.where(TimeEntry.date >= date_from)
            count_query = count_query.where(TimeEntry.date >= date_from)
        if date_to:
            query = query.where(TimeEntry.date <= date_to)
            count_query = count_query.where(TimeEntry.date <= date_to)
        if status_filter:
            query = query.where(TimeEntry.status == status_filter)
            count_query = count_query.where(TimeEntry.status == status_filter)

        total = (await db.execute(count_query)).scalar() or 0
        result = await db.execute(
            query.order_by(TimeEntry.date.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def get_time_entry(db: AsyncSession, entry_id: uuid.UUID) -> TimeEntry:
        result = await db.execute(
            select(TimeEntry).where(
                TimeEntry.id == entry_id, TimeEntry.deleted_at.is_(None)
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="Time entry not found")
        return entry

    @staticmethod
    async def update_time_entry(
        db: AsyncSession, entry_id: uuid.UUID, data: TimeEntryUpdate,
        current_user: CurrentUser,
    ) -> TimeEntry:
        entry = await TimeTrackingService.get_time_entry(db, entry_id)
        if entry.user_id != current_user.user_id:
            verify_role(current_user, "CPA_OWNER")
        if entry.status in (TimeEntryStatus.APPROVED, TimeEntryStatus.BILLED):
            raise HTTPException(status_code=400, detail="Cannot edit approved/billed entries")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entry, field, value)

        if entry.hourly_rate and entry.is_billable:
            entry.amount = (Decimal(entry.duration_minutes) / Decimal("60")) * entry.hourly_rate
        elif not entry.is_billable:
            entry.amount = None

        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def delete_time_entry(
        db: AsyncSession, entry_id: uuid.UUID, current_user: CurrentUser,
    ) -> None:
        entry = await TimeTrackingService.get_time_entry(db, entry_id)
        if entry.user_id != current_user.user_id:
            verify_role(current_user, "CPA_OWNER")
        if entry.status in (TimeEntryStatus.APPROVED, TimeEntryStatus.BILLED):
            raise HTTPException(status_code=400, detail="Cannot delete approved/billed entries")
        entry.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def submit_time_entries(
        db: AsyncSession, entry_ids: list[uuid.UUID], current_user: CurrentUser,
    ) -> list[TimeEntry]:
        entries = []
        for eid in entry_ids:
            entry = await TimeTrackingService.get_time_entry(db, eid)
            if entry.user_id != current_user.user_id:
                verify_role(current_user, "CPA_OWNER")
            if entry.status != TimeEntryStatus.DRAFT:
                raise HTTPException(status_code=400, detail=f"Entry {eid} is not in DRAFT status")
            entry.status = TimeEntryStatus.SUBMITTED
            entries.append(entry)
        await db.commit()
        return entries

    @staticmethod
    async def approve_time_entries(
        db: AsyncSession, entry_ids: list[uuid.UUID], current_user: CurrentUser,
    ) -> list[TimeEntry]:
        verify_role(current_user, "CPA_OWNER")
        entries = []
        for eid in entry_ids:
            entry = await TimeTrackingService.get_time_entry(db, eid)
            if entry.status != TimeEntryStatus.SUBMITTED:
                raise HTTPException(status_code=400, detail=f"Entry {eid} is not SUBMITTED")
            entry.status = TimeEntryStatus.APPROVED
            entries.append(entry)
        await db.commit()
        return entries

    # --- Timer Sessions ---
    @staticmethod
    async def start_timer(
        db: AsyncSession, data: TimerSessionCreate, current_user: CurrentUser,
    ) -> TimerSession:
        # Stop any running timers
        result = await db.execute(
            select(TimerSession).where(
                TimerSession.user_id == current_user.user_id,
                TimerSession.is_running.is_(True),
            )
        )
        for running in result.scalars().all():
            running.is_running = False
            running.stopped_at = datetime.now(timezone.utc)

        timer = TimerSession(
            user_id=current_user.user_id,
            client_id=data.client_id,
            description=data.description,
            service_type=data.service_type,
        )
        db.add(timer)
        await db.commit()
        await db.refresh(timer)
        return timer

    @staticmethod
    async def stop_timer(
        db: AsyncSession, timer_id: uuid.UUID, current_user: CurrentUser,
    ) -> TimerSession:
        result = await db.execute(
            select(TimerSession).where(TimerSession.id == timer_id)
        )
        timer = result.scalar_one_or_none()
        if not timer:
            raise HTTPException(status_code=404, detail="Timer not found")
        if timer.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not your timer")
        timer.is_running = False
        timer.stopped_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(timer)
        return timer

    @staticmethod
    async def get_active_timer(
        db: AsyncSession, current_user: CurrentUser,
    ) -> TimerSession | None:
        result = await db.execute(
            select(TimerSession).where(
                TimerSession.user_id == current_user.user_id,
                TimerSession.is_running.is_(True),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def convert_timer_to_entry(
        db: AsyncSession, timer_id: uuid.UUID, current_user: CurrentUser,
    ) -> TimeEntry:
        result = await db.execute(
            select(TimerSession).where(TimerSession.id == timer_id)
        )
        timer = result.scalar_one_or_none()
        if not timer:
            raise HTTPException(status_code=404, detail="Timer not found")
        if timer.is_running:
            timer.is_running = False
            timer.stopped_at = datetime.now(timezone.utc)

        if not timer.stopped_at or not timer.client_id:
            raise HTTPException(status_code=400, detail="Timer must be stopped and have a client")

        duration = int((timer.stopped_at - timer.started_at).total_seconds() / 60)
        if duration < 1:
            duration = 1

        create_data = TimeEntryCreate(
            client_id=timer.client_id,
            date=timer.started_at.date(),
            duration_minutes=duration,
            description=timer.description,
            service_type=timer.service_type,
        )
        return await TimeTrackingService.create_time_entry(db, create_data, current_user)

    # --- Staff Rates ---
    @staticmethod
    async def set_staff_rate(
        db: AsyncSession, data: StaffRateCreate, current_user: CurrentUser,
    ) -> StaffRate:
        verify_role(current_user, "CPA_OWNER")
        rate = StaffRate(
            user_id=data.user_id,
            rate_name=data.rate_name,
            hourly_rate=data.hourly_rate,
            effective_date=data.effective_date,
            end_date=data.end_date,
        )
        db.add(rate)
        await db.commit()
        await db.refresh(rate)
        return rate

    @staticmethod
    async def _get_user_rate(
        db: AsyncSession, user_id: uuid.UUID, as_of: date,
    ) -> Decimal | None:
        result = await db.execute(
            select(StaffRate).where(
                StaffRate.user_id == user_id,
                StaffRate.effective_date <= as_of,
                StaffRate.deleted_at.is_(None),
                (StaffRate.end_date.is_(None) | (StaffRate.end_date >= as_of)),
            ).order_by(StaffRate.effective_date.desc()).limit(1)
        )
        rate = result.scalar_one_or_none()
        return rate.hourly_rate if rate else None

    # --- Utilization Report ---
    @staticmethod
    async def utilization_report(
        db: AsyncSession, date_from: date, date_to: date,
    ) -> list[dict]:
        result = await db.execute(
            select(
                TimeEntry.user_id,
                func.sum(TimeEntry.duration_minutes).label("total_minutes"),
                func.sum(
                    func.case(
                        (TimeEntry.is_billable.is_(True), TimeEntry.duration_minutes),
                        else_=0,
                    )
                ).label("billable_minutes"),
                func.sum(
                    func.case(
                        (TimeEntry.is_billable.is_(True), TimeEntry.amount),
                        else_=Decimal("0"),
                    )
                ).label("total_amount"),
            ).where(
                TimeEntry.deleted_at.is_(None),
                TimeEntry.date >= date_from,
                TimeEntry.date <= date_to,
            ).group_by(TimeEntry.user_id)
        )

        rows = result.all()
        reports = []
        for row in rows:
            user = await db.get(User, row.user_id)
            total_hrs = Decimal(row.total_minutes or 0) / Decimal("60")
            billable_hrs = Decimal(row.billable_minutes or 0) / Decimal("60")
            util_pct = (billable_hrs / total_hrs * 100) if total_hrs > 0 else Decimal("0")
            reports.append({
                "user_id": row.user_id,
                "user_name": user.full_name if user else "Unknown",
                "total_hours": round(total_hrs, 2),
                "billable_hours": round(billable_hrs, 2),
                "non_billable_hours": round(total_hrs - billable_hrs, 2),
                "utilization_pct": round(util_pct, 1),
                "total_amount": row.total_amount or Decimal("0"),
                "period_start": date_from,
                "period_end": date_to,
            })
        return reports
