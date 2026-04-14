import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator, model_validator
from pydantic.alias_generators import to_camel


class MaintenancePlanCreate(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    title: str
    target_km: int | None = None
    target_date: date | None = None
    summary: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Наименование не может быть пустым")
        return v.strip()

    @model_validator(mode="after")
    def at_least_one_target(self) -> "MaintenancePlanCreate":
        if self.target_km is None and self.target_date is None:
            raise ValueError("Укажите хотя бы пробег или дату выполнения")
        return self


class MaintenancePlanUpdate(MaintenancePlanCreate):
    pass


class MaintenancePlanResponse(BaseModel):
    id: uuid.UUID
    carId: uuid.UUID
    title: str
    targetKm: int | None
    targetDate: date | None
    summary: str | None
    notes: str | None
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, plan) -> "MaintenancePlanResponse":
        return cls(
            id=plan.id,
            carId=plan.car_id,
            title=plan.title,
            targetKm=plan.target_km,
            targetDate=plan.target_date,
            summary=plan.summary,
            notes=plan.notes,
            createdAt=plan.created_at,
        )
