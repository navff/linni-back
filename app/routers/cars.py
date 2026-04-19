import logging
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from ..auth import get_current_user
from ..bot import send_rating_request
from ..database import get_db, async_session_maker
from ..models import Car, ServiceRecord, ShareToken, User
from ..schemas.car import CarCreate, CarResponse, CarUpdate, CarMileageUpdate, CarDescriptionUpdate
from ..schemas.service_record import ShareTokenResponse
from ..config import settings

router = APIRouter(prefix="/api/cars", tags=["cars"])

ENGINE_TYPE_LABELS: dict[str, str] = {
    "petrol": "бензин",
    "diesel": "дизель",
    "hybrid": "гибрид",
    "electric": "электро",
}

_DESCRIPTION_TIMEOUT = 60


async def _fetch_and_save_description(car_id: uuid.UUID, car_model: str, year: int) -> None:
    try:
        async with httpx.AsyncClient(timeout=_DESCRIPTION_TIMEOUT) as client:
            response = await client.post(
                settings.N8N_DESCRIPTION_URL,
                json={"car_model": car_model, "year": str(year)},
                headers={
                    "Authorization": f"Bearer {settings.N8N_SUGGESTIONS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
        raw = response.json()
        text = raw[0]["text"] if (isinstance(raw, list) and raw and isinstance(raw[0].get("text"), str)) else None
        if not text:
            return
    except Exception as exc:
        logger.warning("Description fetch failed for car %s: %s", car_id, exc)
        return

    try:
        async with async_session_maker() as db:
            car = await db.get(Car, car_id)
            if car is not None:
                car.description = text
                car.updated_at = datetime.utcnow()
                await db.commit()
    except Exception as exc:
        logger.warning("Description save failed for car %s: %s", car_id, exc)


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
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_or_create_user(db, current_user["user"])
    user_id = int(current_user["user"]["id"])
    car = Car(user_id=user_id, **data.model_dump())
    db.add(car)
    await db.commit()
    await db.refresh(car)

    engine_label = ENGINE_TYPE_LABELS.get(car.engine_type or "", "")
    car_model = f"{car.make} {car.model} ({engine_label})" if engine_label else f"{car.make} {car.model}"
    background_tasks.add_task(_fetch_and_save_description, car.id, car_model, car.year)

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


@router.post("/{car_id}/generate-description", status_code=202)
async def generate_description(
    car_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    engine_label = ENGINE_TYPE_LABELS.get(car.engine_type or "", "")
    car_model = f"{car.make} {car.model} ({engine_label})" if engine_label else f"{car.make} {car.model}"
    background_tasks.add_task(_fetch_and_save_description, car.id, car_model, car.year)
    return {"status": "generating"}


@router.patch("/{car_id}/description", response_model=CarResponse)
async def update_description(
    car_id: uuid.UUID,
    data: CarDescriptionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    car.description = data.description
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
