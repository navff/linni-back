import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Car, MaintenancePlan
from ..schemas.maintenance_plan import (
    MaintenancePlanCreate,
    MaintenancePlanDone,
    MaintenancePlanResponse,
    MaintenancePlanUpdate,
)

router = APIRouter(prefix="/api/cars/{car_id}/maintenance", tags=["maintenance"])


async def _get_car_for_user(db: AsyncSession, car_id: uuid.UUID, user_id: int) -> Car:
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    return car


@router.get("", response_model=list[MaintenancePlanResponse])
async def list_plans(
    car_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    result = await db.execute(
        select(MaintenancePlan)
        .where(MaintenancePlan.car_id == car_id)
        .order_by(MaintenancePlan.created_at)
    )
    plans = result.scalars().all()
    return [MaintenancePlanResponse.from_orm_model(p) for p in plans]


@router.post("", response_model=MaintenancePlanResponse, status_code=201)
async def create_plan(
    car_id: uuid.UUID,
    data: MaintenancePlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    plan = MaintenancePlan(
        car_id=car_id,
        title=data.title,
        interval_km=data.interval_km,
        interval_months=data.interval_months,
        last_mileage=data.last_mileage,
        last_date=data.last_date,
        notes=data.notes,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return MaintenancePlanResponse.from_orm_model(plan)


@router.put("/{plan_id}", response_model=MaintenancePlanResponse)
async def update_plan(
    car_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: MaintenancePlanUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    plan = await db.get(MaintenancePlan, plan_id)
    if plan is None or plan.car_id != car_id:
        raise HTTPException(status_code=404, detail="Регламент не найден")

    plan.title = data.title
    plan.interval_km = data.interval_km
    plan.interval_months = data.interval_months
    plan.last_mileage = data.last_mileage
    plan.last_date = data.last_date
    plan.notes = data.notes

    await db.commit()
    await db.refresh(plan)
    return MaintenancePlanResponse.from_orm_model(plan)


@router.patch("/{plan_id}/done", response_model=MaintenancePlanResponse)
async def mark_plan_done(
    car_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: MaintenancePlanDone,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await _get_car_for_user(db, car_id, user_id)

    plan = await db.get(MaintenancePlan, plan_id)
    if plan is None or plan.car_id != car_id:
        raise HTTPException(status_code=404, detail="Регламент не найден")

    if data.mileage is not None:
        plan.last_mileage = data.mileage
        if data.mileage > car.mileage:
            car.mileage = data.mileage
            car.updated_at = datetime.utcnow()

    if data.done_date is not None:
        plan.last_date = data.done_date

    await db.commit()
    await db.refresh(plan)
    return MaintenancePlanResponse.from_orm_model(plan)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    car_id: uuid.UUID,
    plan_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    plan = await db.get(MaintenancePlan, plan_id)
    if plan is None or plan.car_id != car_id:
        raise HTTPException(status_code=404, detail="Регламент не найден")

    await db.delete(plan)
    await db.commit()
