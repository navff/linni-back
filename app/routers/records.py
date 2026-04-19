import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..bot import send_rating_request
from ..database import get_db
from ..models import Car, ServiceRecord, User
from ..schemas.service_record import ServiceRecordCreate, ServiceRecordResponse, ServiceRecordUpdate

router = APIRouter(prefix="/api/cars/{car_id}/records", tags=["records"])


async def _get_car_for_user(db: AsyncSession, car_id: uuid.UUID, user_id: int) -> Car:
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    return car


@router.get("", response_model=list[ServiceRecordResponse])
async def list_records(
    car_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    query = (
        select(ServiceRecord)
        .where(ServiceRecord.car_id == car_id)
        .options(selectinload(ServiceRecord.attachments))
        .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
    )
    result = await db.execute(query)
    records = result.scalars().all()
    return [ServiceRecordResponse.from_orm_model(r) for r in records]


@router.post("", response_model=ServiceRecordResponse, status_code=201)
async def create_record(
    car_id: uuid.UUID,
    data: ServiceRecordCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await _get_car_for_user(db, car_id, user_id)

    consumption_per_100km = None

    if data.mileage is not None:
        # Validate mileage >= last record mileage (any type)
        last_record = await db.execute(
            select(ServiceRecord)
            .where(ServiceRecord.car_id == car_id, ServiceRecord.mileage.isnot(None))
            .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
            .limit(1)
        )
        prev = last_record.scalar_one_or_none()
        if prev and data.mileage < prev.mileage:
            raise HTTPException(
                status_code=422,
                detail=f"Пробег не может быть меньше предыдущей записи ({prev.mileage} км)",
            )

        # Calculate fuel consumption if this is a fuel record with mileage
        if data.record_type == "fuel":
            prev_fuel = await db.execute(
                select(ServiceRecord)
                .where(
                    ServiceRecord.car_id == car_id,
                    ServiceRecord.record_type == "fuel",
                    ServiceRecord.mileage.isnot(None),
                )
                .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
                .limit(1)
            )
            last_fuel = prev_fuel.scalar_one_or_none()
            if last_fuel and last_fuel.mileage and data.mileage > last_fuel.mileage:
                distance = data.mileage - last_fuel.mileage
                consumption_per_100km = round(data.fuel_liters * 100 / distance, 2)

    record = ServiceRecord(
        car_id=car_id,
        record_type=data.record_type,
        title=data.title,
        date=data.date,
        mileage=data.mileage,
        cost=data.cost,
        workshop=data.workshop,
        notes=data.notes,
        fuel_liters=data.fuel_liters,
        consumption_per_100km=consumption_per_100km,
    )
    db.add(record)

    # Update car mileage if new record has higher mileage
    if data.mileage is not None and data.mileage > car.mileage:
        car.mileage = data.mileage

    await db.flush()
    await db.refresh(record, ["attachments"])

    # Count total records for this user across all cars to trigger rating request
    record_count_result = await db.execute(
        select(func.count()).where(
            ServiceRecord.car_id.in_(select(Car.id).where(Car.user_id == user_id))
        )
    )
    record_count = record_count_result.scalar()

    user = await db.get(User, user_id)
    should_send_rating = record_count == 1 and user and not user.rating_requested

    if should_send_rating and user:
        user.rating_requested = True

    await db.commit()
    await db.refresh(record, ["attachments"])

    if should_send_rating:
        asyncio.create_task(send_rating_request(user_id))

    return ServiceRecordResponse.from_orm_model(record)


@router.put("/{record_id}", response_model=ServiceRecordResponse)
async def update_record(
    car_id: uuid.UUID,
    record_id: uuid.UUID,
    data: ServiceRecordUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    record = await db.get(ServiceRecord, record_id, options=[selectinload(ServiceRecord.attachments)])
    if record is None or record.car_id != car_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    record.record_type = data.record_type
    record.title = data.title
    record.date = data.date
    record.mileage = data.mileage
    record.cost = data.cost
    record.workshop = data.workshop
    record.notes = data.notes
    record.fuel_liters = data.fuel_liters
    # Recalculate consumption is not done on edit (complex; keep existing value unless cleared)
    if data.record_type != "fuel":
        record.fuel_liters = None
        record.consumption_per_100km = None

    await db.commit()
    await db.refresh(record, ["attachments"])
    return ServiceRecordResponse.from_orm_model(record)


@router.delete("/{record_id}", status_code=204)
async def delete_record(
    car_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    await _get_car_for_user(db, car_id, user_id)

    record = await db.get(ServiceRecord, record_id)
    if record is None or record.car_id != car_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    await db.delete(record)
    await db.commit()
