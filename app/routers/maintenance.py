import uuid

from fastapi import APIRouter, Depends, HTTPException
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
