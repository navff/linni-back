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

    # Validate mileage >= previous record
    last_record = await db.execute(
        select(ServiceRecord)
        .where(ServiceRecord.car_id == car_id)
        .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
        .limit(1)
    )
    prev = last_record.scalar_one_or_none()
    if prev and data.mileage < prev.mileage:
        raise HTTPException(
            status_code=422,
            detail=f"Пробег не может быть меньше предыдущей записи ({prev.mileage} км)",
        )

    record = ServiceRecord(car_id=car_id, **data.model_dump())
    db.add(record)

    # Update car mileage if new record has higher mileage
    if data.mileage > car.mileage:
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

    for field, value in data.model_dump(exclude_none=False).items():
        setattr(record, field, value)

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
