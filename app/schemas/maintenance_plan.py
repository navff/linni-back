import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator, model_validator
from pydantic.alias_generators import to_camel


class MaintenancePlanCreate(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    title: str
    interval_km: int | None = None
    interval_months: int | None = None
    last_mileage: int | None = None
    last_date: date | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Наименование не может быть пустым")
        return v.strip()

    @model_validator(mode="after")
    def at_least_one_interval(self) -> "MaintenancePlanCreate":
        if not self.interval_km and not self.interval_months:
            raise ValueError("Укажите хотя бы один интервал: по пробегу или по времени")
        return self


class MaintenancePlanUpdate(MaintenancePlanCreate):
    pass


class MaintenancePlanDone(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    mileage: int | None = None
    done_date: date | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> "MaintenancePlanDone":
        if self.mileage is None and self.done_date is None:
            raise ValueError("Укажите пробег или дату выполнения")
        return self


class MaintenancePlanResponse(BaseModel):
    id: uuid.UUID
    carId: uuid.UUID
    title: str
    intervalKm: int | None
    intervalMonths: int | None
    lastMileage: int | None
    lastDate: date | None
    notes: str | None
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, plan) -> "MaintenancePlanResponse":
        return cls(
            id=plan.id,
            carId=plan.car_id,
            title=plan.title,
            intervalKm=plan.interval_km,
            intervalMonths=plan.interval_months,
            lastMileage=plan.last_mileage,
            lastDate=plan.last_date,
            notes=plan.notes,
            createdAt=plan.created_at,
        )
