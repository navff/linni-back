import uuid
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Car, MaintenancePlan
from ..schemas.maintenance_plan import MaintenancePlanResponse

router = APIRouter(prefix="/api/cars/{car_id}/suggestions", tags=["suggestions"])

TIMEOUT_SECONDS = 75

ENGINE_TYPE_LABELS: dict[str, str] = {
    "petrol": "бензин",
    "diesel": "дизель",
    "hybrid": "гибрид",
    "electric": "электро",
}


class SuggestionsRequest(BaseModel):
    last_service_date: str


async def _get_car_for_user(db: AsyncSession, car_id: uuid.UUID, user_id: int) -> Car:
    car = await db.get(Car, car_id)
    if car is None or car.user_id != user_id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    return car


@router.post("", response_model=list[MaintenancePlanResponse])
async def create_suggestions(
    car_id: uuid.UUID,
    data: SuggestionsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = int(current_user["user"]["id"])
    car = await _get_car_for_user(db, car_id, user_id)

    # Build car model string for n8n prompt
    engine_label = ENGINE_TYPE_LABELS.get(car.engine_type or "", "")
    car_model = f"{car.make} {car.model} ({engine_label})" if engine_label else f"{car.make} {car.model}"

    # Fetch suggestions from n8n
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.N8N_SUGGESTIONS_URL,
                json={
                    "car_model": car_model,
                    "year": str(car.year),
                    "last_service_date": data.last_service_date,
                    "milage": str(car.mileage),
                },
                headers={
                    "Authorization": f"Bearer {settings.N8N_SUGGESTIONS_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Превышено время ожидания ответа от сервиса")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка внешнего сервиса: {e.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Ошибка соединения с сервисом рекомендаций")

    # Parse n8n response: [{ output: [...] }]
    raw = response.json()
    suggestions = raw[0]["output"] if (isinstance(raw, list) and raw and isinstance(raw[0].get("output"), list)) else []

    if not suggestions:
        return []

    # Create MaintenancePlan records in DB
    created = []
    for s in suggestions:
        target_date: date | None = None
        if s.get("date"):
            try:
                target_date = date.fromisoformat(s["date"])
            except ValueError:
                pass

        notes = "\n".join(s["services"]) if s.get("services") else None

        plan = MaintenancePlan(
            car_id=car_id,
            title=s.get("name", "ТО"),
            target_km=s.get("milage") or None,
            target_date=target_date,
            summary=s.get("summary") or None,
            notes=notes,
        )
        db.add(plan)
        created.append(plan)

    await db.commit()
    for plan in created:
        await db.refresh(plan)

    return [MaintenancePlanResponse.from_orm_model(p) for p in created]
