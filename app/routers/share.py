import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Car, ServiceRecord, ShareToken
from ..schemas.car import CarResponse
from ..schemas.service_record import ServiceRecordResponse

router = APIRouter(prefix="/api/share", tags=["share"])


class SharedCarResponse:
    pass


@router.get("/{token}")
async def get_shared_car(
    token: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    share = await db.get(ShareToken, token)
    if share is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена или устарела")

    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Ссылка истекла")

    car = await db.get(Car, share.car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    records_result = await db.execute(
        select(ServiceRecord)
        .where(ServiceRecord.car_id == car.id)
        .options(selectinload(ServiceRecord.attachments))
        .order_by(ServiceRecord.date.desc())
    )
    records = records_result.scalars().all()

    return {
        "car": CarResponse.from_orm_model(car),
        "records": [ServiceRecordResponse.from_orm_model(r) for r in records],
    }
