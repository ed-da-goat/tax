"""
Service layer for fixed asset management (AN3).

Depreciation calculation (MACRS GDS, straight-line, Section 179, bonus).
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, verify_role
from app.models.fixed_asset import (
    FixedAsset, DepreciationEntry, DepreciationMethod, AssetStatus,
)
from app.schemas.fixed_asset import FixedAssetCreate, FixedAssetUpdate, FixedAssetDispose

# SOURCE: IRS Publication 946, Table A-1 through A-20 (MACRS GDS half-year convention)
# REVIEW DATE: 2026-03-04
MACRS_RATES = {
    "3-year": [Decimal("33.33"), Decimal("44.45"), Decimal("14.81"), Decimal("7.41")],
    "5-year": [Decimal("20.00"), Decimal("32.00"), Decimal("19.20"), Decimal("11.52"), Decimal("11.52"), Decimal("5.76")],
    "7-year": [Decimal("14.29"), Decimal("24.49"), Decimal("17.49"), Decimal("12.49"), Decimal("8.93"), Decimal("8.92"), Decimal("8.93"), Decimal("4.46")],
    "15-year": [Decimal("5.00"), Decimal("9.50"), Decimal("8.55"), Decimal("7.70"), Decimal("6.93"), Decimal("6.23"), Decimal("5.90"), Decimal("5.90"), Decimal("5.91"), Decimal("5.90"), Decimal("5.91"), Decimal("5.90"), Decimal("5.91"), Decimal("5.90"), Decimal("5.91"), Decimal("2.95")],
    "27.5-year": [Decimal("3.636")] * 28,
    "39-year": [Decimal("2.564")] * 40,
}


class FixedAssetService:

    @staticmethod
    async def create_asset(
        db: AsyncSession, client_id: uuid.UUID,
        data: FixedAssetCreate, current_user: CurrentUser,
    ) -> FixedAsset:
        book_value = data.acquisition_cost - data.section_179_amount
        asset = FixedAsset(
            client_id=client_id,
            asset_name=data.asset_name,
            asset_number=data.asset_number,
            description=data.description,
            category=data.category,
            acquisition_date=data.acquisition_date,
            acquisition_cost=data.acquisition_cost,
            depreciation_method=data.depreciation_method,
            useful_life_years=data.useful_life_years,
            salvage_value=data.salvage_value,
            macrs_class=data.macrs_class,
            bonus_depreciation_pct=data.bonus_depreciation_pct,
            section_179_amount=data.section_179_amount,
            accumulated_depreciation=data.section_179_amount,
            book_value=book_value,
            status=AssetStatus.ACTIVE,
            asset_account_id=data.asset_account_id,
            depreciation_expense_account_id=data.depreciation_expense_account_id,
            accumulated_depreciation_account_id=data.accumulated_depreciation_account_id,
            location=data.location,
            serial_number=data.serial_number,
        )
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        # Generate depreciation schedule
        await FixedAssetService._generate_schedule(db, asset)
        await db.refresh(asset)
        return asset

    @staticmethod
    async def _generate_schedule(db: AsyncSession, asset: FixedAsset) -> None:
        """Generate the full depreciation schedule for an asset."""
        if asset.depreciation_method == DepreciationMethod.NONE:
            return

        depreciable_basis = asset.acquisition_cost - asset.section_179_amount - asset.salvage_value

        if asset.depreciation_method == DepreciationMethod.MACRS_GDS and asset.macrs_class:
            rates = MACRS_RATES.get(asset.macrs_class, [])
            accumulated = asset.section_179_amount
            for i, rate in enumerate(rates):
                year = asset.acquisition_date.year + i
                dep_amount = (asset.acquisition_cost * rate / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                accumulated += dep_amount
                bv = asset.acquisition_cost - accumulated
                if bv < asset.salvage_value:
                    dep_amount -= (asset.salvage_value - bv)
                    bv = asset.salvage_value
                    accumulated = asset.acquisition_cost - bv

                entry = DepreciationEntry(
                    asset_id=asset.id,
                    period_start=date(year, 1, 1),
                    period_end=date(year, 12, 31),
                    fiscal_year=year,
                    depreciation_amount=max(dep_amount, Decimal("0")),
                    accumulated_total=accumulated,
                    book_value_end=max(bv, Decimal("0")),
                )
                db.add(entry)
                if bv <= asset.salvage_value:
                    break

        elif asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            if not asset.useful_life_years or asset.useful_life_years <= 0:
                return
            annual = (depreciable_basis / asset.useful_life_years).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            accumulated = asset.section_179_amount
            for i in range(asset.useful_life_years):
                year = asset.acquisition_date.year + i
                accumulated += annual
                bv = asset.acquisition_cost - accumulated
                entry = DepreciationEntry(
                    asset_id=asset.id,
                    period_start=date(year, 1, 1),
                    period_end=date(year, 12, 31),
                    fiscal_year=year,
                    depreciation_amount=annual,
                    accumulated_total=accumulated,
                    book_value_end=max(bv, Decimal("0")),
                )
                db.add(entry)

        await db.flush()

    @staticmethod
    async def list_assets(
        db: AsyncSession, client_id: uuid.UUID,
        status_filter: str | None = None,
        skip: int = 0, limit: int = 100,
    ) -> tuple[list[FixedAsset], int]:
        query = select(FixedAsset).where(
            FixedAsset.client_id == client_id,
            FixedAsset.deleted_at.is_(None),
        )
        count_q = select(func.count(FixedAsset.id)).where(
            FixedAsset.client_id == client_id,
            FixedAsset.deleted_at.is_(None),
        )
        if status_filter:
            query = query.where(FixedAsset.status == status_filter)
            count_q = count_q.where(FixedAsset.status == status_filter)

        total = (await db.execute(count_q)).scalar() or 0
        result = await db.execute(
            query.order_by(FixedAsset.acquisition_date.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().unique().all()), total

    @staticmethod
    async def get_asset(
        db: AsyncSession, client_id: uuid.UUID, asset_id: uuid.UUID,
    ) -> FixedAsset:
        result = await db.execute(
            select(FixedAsset).where(
                FixedAsset.id == asset_id,
                FixedAsset.client_id == client_id,
                FixedAsset.deleted_at.is_(None),
            )
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(status_code=404, detail="Fixed asset not found")
        return asset

    @staticmethod
    async def dispose_asset(
        db: AsyncSession, client_id: uuid.UUID, asset_id: uuid.UUID,
        data: FixedAssetDispose, current_user: CurrentUser,
    ) -> FixedAsset:
        verify_role(current_user, "CPA_OWNER")
        asset = await FixedAssetService.get_asset(db, client_id, asset_id)
        if asset.status != AssetStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Asset not active")

        asset.status = AssetStatus.DISPOSED
        asset.disposal_date = data.disposal_date
        asset.disposal_amount = data.disposal_amount
        asset.disposal_method = data.disposal_method
        asset.gain_loss = data.disposal_amount - asset.book_value
        await db.commit()
        await db.refresh(asset)
        return asset

    @staticmethod
    async def depreciation_summary(
        db: AsyncSession, client_id: uuid.UUID, fiscal_year: int,
    ) -> dict:
        result = await db.execute(
            select(
                func.count(FixedAsset.id).label("total_assets"),
                func.sum(FixedAsset.acquisition_cost).label("total_cost"),
                func.sum(FixedAsset.accumulated_depreciation).label("total_accum"),
                func.sum(FixedAsset.book_value).label("total_bv"),
            ).where(
                FixedAsset.client_id == client_id,
                FixedAsset.deleted_at.is_(None),
            )
        )
        row = result.one()

        dep_result = await db.execute(
            select(func.sum(DepreciationEntry.depreciation_amount)).where(
                DepreciationEntry.fiscal_year == fiscal_year,
                DepreciationEntry.asset_id.in_(
                    select(FixedAsset.id).where(FixedAsset.client_id == client_id)
                ),
            )
        )
        current_year_dep = dep_result.scalar() or Decimal("0")

        return {
            "client_id": client_id,
            "fiscal_year": fiscal_year,
            "total_assets": row.total_assets or 0,
            "total_cost": row.total_cost or Decimal("0"),
            "total_accumulated_depreciation": row.total_accum or Decimal("0"),
            "total_book_value": row.total_bv or Decimal("0"),
            "current_year_depreciation": current_year_dep,
        }
