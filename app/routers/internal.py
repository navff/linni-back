from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import Car, MaintenancePlan

router = APIRouter(prefix="/api/internal", tags=["internal"])

_bearer = HTTPBearer()


def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
    if credentials.credentials != settings.INTERNAL_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")


class MaintenanceDueItem(BaseModel):
    user_id: int
    car_name: str
    plan_title: str
    target_date: date | None
    target_km: int | None


@router.get(
    "/maintenance-due",
    response_model=list[MaintenanceDueItem],
    dependencies=[Depends(_verify_token)],
)
async def maintenance_due(db: AsyncSession = Depends(get_db)):
    today = date.today()

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
