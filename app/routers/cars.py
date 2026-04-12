import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..bot import send_rating_request
from ..database import get_db
from ..models import Car, ServiceRecord, ShareToken, User
from ..schemas.car import CarCreate, CarResponse, CarUpdate, CarMileageUpdate
from ..schemas.service_record import ShareTokenResponse
from ..config import settings

router = APIRouter(prefix="/api/cars", tags=["cars"])


async def get_or_create_user(db: AsyncSession, user_data: dict) -> User:
    uid = int(user_data["id"])
    user = await db.get(User, uid)
    if user is None:
        user = User(
            id=uid,
            first_name=user_data.get("first_name"),
            username=user_data.get("username"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("", response_model=list[CarResponse])
async def list_cars(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_or_create_user(db, current_user["user"])
    user_id = int(current_user["user"]["id"])
    result = await db.execute(select(Car).where(Car.user_id == user_id).order_by(Car.created_at))
    cars = result.scalars().all()
    return [CarResponse.from_orm_model(c) for c in cars]


@router.post("", response_model=CarResponse, status_code=201)
async def create_car(
    data: CarCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_or_create_user(db, current_user["user"])
    user_id = int(current_user["user"]["id"])
    car = Car(user_id=user_id, **data.model_dump())
    db.add(car)
    await db.commit()
    await db.refresh(car)
    return CarResponse.from_orm_model(car)


@router.get("/{car_id}", response_model=CarResponse)
async def get_car(
    car_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    return CarResponse.from_orm_model(car)


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: uuid.UUID,
    data: CarUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    for field, value in data.model_dump(exclude_none=False).items():
        setattr(car, field, value)
    car.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(car)
    return CarResponse.from_orm_model(car)


@router.delete("/{car_id}", status_code=204)
async def delete_car(
    car_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    await db.delete(car)
    await db.commit()


@router.patch("/{car_id}/mileage", response_model=CarResponse)
async def update_mileage(
    car_id: uuid.UUID,
    data: CarMileageUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    if data.mileage <= car.mileage:
        raise HTTPException(status_code=422, detail=f"Новый пробег должен быть больше текущего ({car.mileage} км)")
    car.mileage = data.mileage
    car.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(car)
    return CarResponse.from_orm_model(car)


@router.post("/{car_id}/share", response_model=ShareTokenResponse)
async def create_share_token(
    car_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    token = ShareToken(car_id=car_id)
    db.add(token)
    await db.commit()
    await db.refresh(token)

    share_url = f"https://max.ru/{settings.BOT_NAME}?startapp=share_{token.token}"
    return ShareTokenResponse(token=str(token.token), shareUrl=share_url)
