import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Car, MaintenancePlan
from ..schemas.maintenance_plan import (
    MaintenancePlanCreate,
    MaintenancePlanResponse,
    MaintenancePlanUpdate,
)

router = APIRouter(prefix="/api/cars/{car_id}/maintenance", tags=["maintenance"])


class ExecutePlanRequest(BaseModel):
    mileage: int
    date: date


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
        target_km=data.target_km,
        target_date=data.target_date,
        summary=data.summary,
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
        raise HTTPException(status_code=404, detail="Пункт плана не найден")

    plan.title = data.title
    plan.target_km = data.target_km
    plan.target_date = data.target_date
    plan.summary = data.summary
    plan.notes = data.notes

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
        raise HTTPException(status_code=404, detail="Пункт плана не найден")

    await db.delete(plan)
    await db.commit()


@router.post("/{plan_id}/execute", response_model=list[MaintenancePlanResponse])
async def execute_plan(
    car_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: ExecutePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a plan as executed with actual mileage and date.
    Shifts all remaining plans by the delta between planned and actual values,
    then deletes the executed plan.
    """
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    plan = await db.get(MaintenancePlan, plan_id)
    if plan is None or plan.car_id != car_id:
        raise HTTPException(status_code=404, detail="Пункт плана не найден")

    # Calculate deltas between planned and actual
    delta_km: int | None = None
    if plan.target_km is not None:
        delta_km = data.mileage - plan.target_km

    delta_days: int | None = None
    if plan.target_date is not None:
        delta_days = (data.date - plan.target_date).days

    # Fetch all other plans for this car
    result = await db.execute(
        select(MaintenancePlan)
        .where(MaintenancePlan.car_id == car_id, MaintenancePlan.id != plan_id)
        .order_by(MaintenancePlan.target_date, MaintenancePlan.target_km)
    )
    remaining = result.scalars().all()

    # Shift each remaining plan by the deltas
    for p in remaining:
        if delta_km is not None and p.target_km is not None:
            p.target_km += delta_km
        if delta_days is not None and p.target_date is not None:
            p.target_date = p.target_date + timedelta(days=delta_days)

    await db.delete(plan)
    await db.commit()

    for p in remaining:
        await db.refresh(p)

    return [MaintenancePlanResponse.from_orm_model(p) for p in remaining]
