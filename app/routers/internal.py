import uuid
from datetime import date as Date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import Car, MaintenancePlan, ServiceRecord
from ..schemas.service_record import ServiceRecordResponse

router = APIRouter(prefix="/api/internal", tags=["internal"])

_bearer = HTTPBearer()


def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if credentials.credentials != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


class MaintenanceDueItem(BaseModel):
    user_id: int
    car_name: str
    plan_title: str
    target_date: Date | None
    target_km: int | None


@router.get(
    "/maintenance-due",
    response_model=list[MaintenanceDueItem],
    dependencies=[Depends(_verify_token)],
)
async def maintenance_due(db: AsyncSession = Depends(get_db)):
    today = Date.today()

    result = await db.execute(
        select(MaintenancePlan, Car)
        .join(Car, MaintenancePlan.car_id == Car.id)
        .where(
            MaintenancePlan.target_date.is_not(None),
            MaintenancePlan.target_date <= today,
        )
        .order_by(MaintenancePlan.target_date)
    )
    rows = result.all()

    return [
        MaintenanceDueItem(
            user_id=car.user_id,
            car_name=car.nickname or f"{car.make} {car.model}",
            plan_title=plan.title,
            target_date=plan.target_date,
            target_km=plan.target_km,
        )
        for plan, car in rows
    ]


class FuelRecordCreate(BaseModel):
    car_id: uuid.UUID
    fuel_liters: float
    cost: float | None = None
    mileage: int | None = None
    date: Date | None = None
    notes: str | None = None


@router.post(
    "/fuel-records",
    response_model=ServiceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_verify_token)],
)
async def create_fuel_record(
    data: FuelRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    if data.fuel_liters <= 0:
        raise HTTPException(status_code=422, detail="fuel_liters должен быть больше 0")

    car = await db.get(Car, data.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    consumption_per_100km = None

    if data.mileage is not None:
        if data.mileage <= 0:
            raise HTTPException(status_code=422, detail="mileage должен быть больше 0")

        # Validate mileage >= last record mileage
        last_any = await db.execute(
            select(ServiceRecord)
            .where(ServiceRecord.car_id == data.car_id, ServiceRecord.mileage.isnot(None))
            .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
            .limit(1)
        )
        prev_any = last_any.scalar_one_or_none()
        if prev_any and data.mileage < prev_any.mileage:
            raise HTTPException(
                status_code=422,
                detail=f"Пробег не может быть меньше предыдущей записи ({prev_any.mileage} км)",
            )

        # Calculate consumption from last fuel record with mileage
        last_fuel = await db.execute(
            select(ServiceRecord)
            .where(
                ServiceRecord.car_id == data.car_id,
                ServiceRecord.record_type == "fuel",
                ServiceRecord.mileage.isnot(None),
            )
            .order_by(ServiceRecord.date.desc(), ServiceRecord.created_at.desc())
            .limit(1)
        )
        prev_fuel = last_fuel.scalar_one_or_none()
        if prev_fuel and prev_fuel.mileage and data.mileage > prev_fuel.mileage:
            distance = data.mileage - prev_fuel.mileage
            consumption_per_100km = round(data.fuel_liters * 100 / distance, 2)

    record = ServiceRecord(
        car_id=data.car_id,
        record_type="fuel",
        title="Заправка",
        date=data.date or Date.today(),
        mileage=data.mileage,
        cost=data.cost,
        notes=data.notes,
        fuel_liters=data.fuel_liters,
        consumption_per_100km=consumption_per_100km,
    )
    db.add(record)

    if data.mileage is not None and data.mileage > car.mileage:
        car.mileage = data.mileage

    await db.commit()
    await db.refresh(record, ["attachments"])
    return ServiceRecordResponse.from_orm_model(record)
